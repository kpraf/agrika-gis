"""
fetch_satellite_cdse.py
=======================

Pull MONTHLY Sentinel-2 (NDVI) and Sentinel-1 (VV/VH backscatter) FEATURES for
every Laguna area from the Copernicus Data Space Ecosystem (CDSE) via the
Sentinel Hub *Statistical* API.

This is the model-feature counterpart of the appendix image script. Instead of
rendering PNGs, it asks CDSE to compute per-polygon statistics (mean / stDev /
min / max) for each calendar month, so the output is numbers the CNN-LSTM can
consume - one monthly time series per area, exactly parallel to
weather_laguna_monthly.csv.

Platform note: same CDSE endpoints and the same `.define_from(service_url=...)`
pattern as the working appendix script - only the request type changes
(SentinelHubStatistical instead of SentinelHubRequest returning PNG).

Requirements (NOT in backend/requirements.txt - this is an offline data-prep tool)
    pip install sentinelhub shapely numpy

Credentials - set as environment variables, NEVER hard-code or commit:
    CDSE_CLIENT_ID       your CDSE OAuth client id
    CDSE_CLIENT_SECRET   your CDSE OAuth client secret
    (create them at https://shapps.dataspace.copernicus.eu/dashboard/ -> User settings)

Output  (backend/db/)
    satellite_laguna_monthly.csv           (--level municipality, default)
    satellite_laguna_barangay_monthly.csv  (--level barangay)

    Columns: <area>, year, month,
             ndvi_mean, ndvi_std, ndvi_min, ndvi_max, s2_valid_px,
             vv_mean, vv_std, vh_mean, vh_std, s1_valid_px

    vv/vh are backscatter in decibels. Empty stats mean the whole month was
    cloud-masked (S2) or had no acquisition (S1) - expected in the wet season;
    handle those gaps when you assemble the training tensor.

Usage
    python backend/scripts/fetch_satellite_cdse.py                 # all municipalities
    python backend/scripts/fetch_satellite_cdse.py --limit 2       # smoke-test 2 areas
    python backend/scripts/fetch_satellite_cdse.py --level barangay --start 2018 --end 2025
"""
import argparse
import csv
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.abspath(os.path.join(HERE, "..", "db"))
GEOJSON = {
    "municipality": os.path.join(DB_DIR, "geojson", "Laguna_Municipalities.geojson"),
    "barangay": os.path.join(DB_DIR, "geojson", "Laguna_Barangays.geojson"),
}
OUT = {
    "municipality": os.path.join(DB_DIR, "satellite_laguna_monthly.csv"),
    "barangay": os.path.join(DB_DIR, "satellite_laguna_barangay_monthly.csv"),
}

CDSE_BASE = "https://sh.dataspace.copernicus.eu"
CDSE_TOKEN = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

# --- evalscripts (Statistical API flavour: emit index bands + dataMask) -------
# Sentinel-2 vegetation/water indices (NDVI, EVI, NDWI), with an SCL-based
# cloud/shadow mask folded into dataMask so clouded pixels are excluded from the
# monthly statistics. Reflectances are 0-1 (L2A surface reflectance).
EVAL_S2_NDVI = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B02", "B03", "B04", "B08", "SCL", "dataMask"] }],
    output: [
      { id: "ndvi", bands: 1, sampleType: "FLOAT32" },
      { id: "evi",  bands: 1, sampleType: "FLOAT32" },
      { id: "ndwi", bands: 1, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}
function evaluatePixel(s) {
  let d_ndvi = s.B08 + s.B04;
  let ndvi = d_ndvi > 0 ? (s.B08 - s.B04) / d_ndvi : 0;
  // EVI = 2.5 (NIR-RED) / (NIR + 6 RED - 7.5 BLUE + 1)
  let d_evi = s.B08 + 6.0 * s.B04 - 7.5 * s.B02 + 1.0;
  let evi = d_evi !== 0 ? 2.5 * (s.B08 - s.B04) / d_evi : 0;
  // NDWI (McFeeters) = (GREEN - NIR) / (GREEN + NIR)
  let d_ndwi = s.B03 + s.B08;
  let ndwi = d_ndwi > 0 ? (s.B03 - s.B08) / d_ndwi : 0;
  // SCL: 3 shadow, 8 cloud med, 9 cloud high, 10 cirrus, 11 snow -> drop
  let bad = [3, 8, 9, 10, 11].indexOf(s.SCL) > -1;
  let valid = (s.dataMask === 1 && !bad && d_ndvi > 0) ? 1 : 0;
  return { ndvi: [ndvi], evi: [evi], ndwi: [ndwi], dataMask: [valid] };
}
"""

# Sentinel-1 IW GRD, VV & VH gamma0 backscatter converted to decibels.
EVAL_S1_VVVH = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["VV", "VH", "dataMask"] }],
    output: [
      { id: "vv", bands: 1, sampleType: "FLOAT32" },
      { id: "vh", bands: 1, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}
function toDb(x) { return 10 * Math.log(x) / Math.LN10; }
function evaluatePixel(s) {
  // Only keep pixels with real, positive backscatter; exclude the rest via
  // dataMask so nodata/border pixels can't turn the average into Infinity.
  let ok = (s.dataMask === 1) && isFinite(s.VV) && isFinite(s.VH) && s.VV > 0 && s.VH > 0;
  return {
    vv: [ok ? toDb(s.VV) : 0],
    vh: [ok ? toDb(s.VH) : 0],
    dataMask: [ok ? 1 : 0]
  };
}
"""


def make_config():
    from sentinelhub import SHConfig
    # Load credentials from backend/.env (gitignored) if present, so they never
    # have to be set in the shell or hard-coded here.
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(HERE, "..", ".env"))
    except ImportError:
        pass
    cid = os.environ.get("CDSE_CLIENT_ID")
    secret = os.environ.get("CDSE_CLIENT_SECRET")
    if not cid or not secret:
        sys.exit("ERROR: set CDSE_CLIENT_ID and CDSE_CLIENT_SECRET env vars first "
                 "(create them in the CDSE dashboard). Nothing was hard-coded on purpose.")
    cfg = SHConfig()
    cfg.sh_client_id = cid
    cfg.sh_client_secret = secret
    cfg.sh_base_url = CDSE_BASE
    cfg.sh_token_url = CDSE_TOKEN
    return cfg


def load_geometries(level):
    """[(name, shapely_geometry)] from the level's GeoJSON."""
    from shapely.geometry import shape
    with open(GEOJSON[level], encoding="utf-8") as fh:
        data = json.load(fh)
    out = []
    for feat in data["features"]:
        out.append((feat["properties"].get("name"), shape(feat["geometry"])))
    out.sort(key=lambda p: p[0])
    return out


def month_key(iso_from):
    """'2024-03-01T00:00:00Z' -> (2024, 3)."""
    return int(iso_from[0:4]), int(iso_from[5:7])


def run_statistical(cfg, collection, evalscript, other_args, geom, start, end, resolution):
    """Return {(year, month): {band_id: {mean,std,min,max,n}}} for one geometry."""
    from sentinelhub import SentinelHubStatistical, Geometry, CRS

    # Reproject to the local UTM zone so `resolution` is in METRES, not degrees.
    # (A geometry left in WGS84 makes resolution=20 mean 20 degrees/pixel ~ 12 km,
    # which the Statistical API rejects.)
    geo = Geometry(geom, CRS.WGS84)
    utm = CRS.get_utm_from_wgs84(geom.centroid.x, geom.centroid.y)
    geo = geo.transform(utm)

    aggregation = SentinelHubStatistical.aggregation(
        evalscript=evalscript,
        time_interval=(f"{start}-01-01", f"{end}-12-31"),
        aggregation_interval="P1M",
        resolution=(resolution, resolution),
    )
    request = SentinelHubStatistical(
        aggregation=aggregation,
        input_data=[SentinelHubStatistical.input_data(collection, other_args=other_args)],
        geometry=geo,
        config=cfg,
    )
    result = request.get_data()[0]

    monthly = {}
    for entry in result.get("data", []):
        if entry.get("outputs") is None:
            continue
        key = month_key(entry["interval"]["from"])
        bands = {}
        for out_id, out_val in entry["outputs"].items():
            band = next(iter(out_val["bands"].values()))  # single-band outputs
            st = band.get("stats", {})
            n = st.get("sampleCount", 0) - st.get("noDataCount", 0)

            def fin(v):  # non-finite (NaN/Infinity) or empty-band -> None
                return v if isinstance(v, (int, float)) and math.isfinite(v) else None

            bands[out_id] = {
                "mean": fin(st.get("mean")),
                "std": fin(st.get("stDev")),
                "min": fin(st.get("min")),
                "max": fin(st.get("max")),
                "n": max(n, 0),
            }
        monthly[key] = bands
    return monthly


def main():
    ap = argparse.ArgumentParser(description="Fetch monthly S2 NDVI + S1 VV/VH features from CDSE.")
    ap.add_argument("--level", choices=["municipality", "barangay"], default="municipality")
    ap.add_argument("--start", type=int, default=2018)
    ap.add_argument("--end", type=int, default=2025)
    ap.add_argument("--resolution", type=int, default=20, help="Sampling resolution in metres.")
    ap.add_argument("--maxcc", type=float, default=0.6, help="Max S2 scene cloud cover (0-1).")
    ap.add_argument("--limit", type=int, default=0, help="Only process the first N areas (smoke test).")
    ap.add_argument("--sleep", type=float, default=1.0, help="Seconds between areas.")
    args = ap.parse_args()

    from sentinelhub import DataCollection

    cfg = make_config()
    s2 = DataCollection.SENTINEL2_L2A.define_from("s2l2a_cdse", service_url=CDSE_BASE)
    s1 = DataCollection.SENTINEL1_IW.define_from("s1iw_cdse", service_url=CDSE_BASE)
    s2_args = {"dataFilter": {"maxCloudCoverage": int(args.maxcc * 100)}}
    s1_args = {
        "dataFilter": {},
        "processing": {"backCoeff": "GAMMA0_TERRAIN", "orthorectify": True},
    }

    areas = load_geometries(args.level)
    if args.limit:
        areas = areas[: args.limit]
    name_col = args.level
    out_path = OUT[args.level]

    print(f"{len(areas)} {args.level} | {args.start}-{args.end} | S2 NDVI/EVI/NDWI + S1 VV/VH | {args.resolution} m")
    rows = []
    for i, (name, geom) in enumerate(areas, 1):
        try:
            s2m = run_statistical(cfg, s2, EVAL_S2_NDVI, s2_args, geom, args.start, args.end, args.resolution)
            s1m = run_statistical(cfg, s1, EVAL_S1_VVVH, s1_args, geom, args.start, args.end, args.resolution)
        except Exception as e:  # noqa: BLE001
            print(f"  [{i}/{len(areas)}] {name}: ERROR {e}", file=sys.stderr)
            continue

        for (year, month) in sorted(set(s2m) | set(s1m)):
            s2v = s2m.get((year, month), {})
            nd = s2v.get("ndvi", {})
            ev = s2v.get("evi", {})
            nw = s2v.get("ndwi", {})
            vv = s1m.get((year, month), {}).get("vv", {})
            vh = s1m.get((year, month), {}).get("vh", {})
            rows.append({
                name_col: name,
                "year": year,
                "month": month,
                "ndvi_mean": nd.get("mean"),
                "ndvi_std": nd.get("std"),
                "evi_mean": ev.get("mean"),
                "evi_std": ev.get("std"),
                "ndwi_mean": nw.get("mean"),
                "ndwi_std": nw.get("std"),
                "s2_valid_px": nd.get("n"),
                "vv_mean": vv.get("mean"),
                "vv_std": vv.get("std"),
                "vh_mean": vh.get("mean"),
                "vh_std": vh.get("std"),
                "s1_valid_px": vv.get("n"),
            })
        print(f"  [{i}/{len(areas)}] {name}: S2 {len(s2m)} mo, S1 {len(s1m)} mo")
        time.sleep(args.sleep)

    if not rows:
        print("No data fetched. Nothing written.", file=sys.stderr)
        return 1

    fieldnames = [name_col, "year", "month",
                  "ndvi_mean", "ndvi_std", "evi_mean", "evi_std",
                  "ndwi_mean", "ndwi_std", "s2_valid_px",
                  "vv_mean", "vv_std", "vh_mean", "vh_std", "s1_valid_px"]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
