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

Quota: every request costs Copernicus "processing units" (the free tier allows
30,000 a month). The script adds up what the API says each request cost, prints
the total, writes it next to the CSV (<out>.meta.json), and stops early if the
run passes --max-pu, so one run can never use up the month.

Usage
    python backend/scripts/fetch_satellite_cdse.py                 # all municipalities
    python backend/scripts/fetch_satellite_cdse.py --limit 2       # smoke-test 2 areas
    python backend/scripts/fetch_satellite_cdse.py --level barangay --start 2018 --end 2025
    # a window of months only (what the scheduled pipeline does), into its own file
    python backend/scripts/fetch_satellite_cdse.py --from-month 2026-08 --to-month 2026-10 \
        --out db/_run/satellite_window.csv
"""
import argparse
import csv
import json
import math
import os
import sys
import time
from datetime import datetime, timezone

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


def load_geometries(level, path=None):
    """[(name, shapely_geometry)] from the level's GeoJSON (or an override path)."""
    from shapely.geometry import shape
    with open(path or GEOJSON[level], encoding="utf-8") as fh:
        data = json.load(fh)
    out = []
    for feat in data["features"]:
        out.append((feat["properties"].get("name"), shape(feat["geometry"])))
    out.sort(key=lambda p: p[0])
    return out


def month_key(iso_from):
    """'2024-03-01T00:00:00Z' -> (2024, 3)."""
    return int(iso_from[0:4]), int(iso_from[5:7])


def parse_month(s):
    """'2026-08' -> (2026, 8)."""
    try:
        year, month = (int(p) for p in s.split("-"))
        if not 1 <= month <= 12:
            raise ValueError
    except ValueError:
        sys.exit(f"ERROR: month must look like 2026-08 (got {s!r}).")
    return year, month


def time_window(args):
    """(from, to) for the request: whole calendar months, `to` exclusive.

    `to` is the first instant of the month AFTER the last one wanted, never later
    than now. Ending on 31 December 23:59:59 instead leaves the last month one
    second short of a full interval, and the API then drops it - which is how
    December of the final year went missing from the first full fetch.
    """
    if args.from_month:
        fy, fm = parse_month(args.from_month)
        ty, tm = parse_month(args.to_month or args.from_month)
    else:
        fy, fm, ty, tm = args.start, 1, args.end, 12
    t_from = datetime(fy, fm, 1)
    t_to = datetime(ty + 1, 1, 1) if tm == 12 else datetime(ty, tm + 1, 1)
    now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    if t_from >= now:
        sys.exit(f"ERROR: {fy}-{fm:02d} has not started yet. Nothing to fetch.")
    return t_from, min(t_to, now)


def run_statistical(cfg, collection, evalscript, other_args, geom, t_from, t_to, resolution):
    """One geometry: ({(year, month): {band_id: {mean,std,min,max,n}}}, processing units spent)."""
    from sentinelhub import SentinelHubStatistical, SentinelHubDownloadClient, Geometry, CRS

    # Reproject to the local UTM zone so `resolution` is in METRES, not degrees.
    # (A geometry left in WGS84 makes resolution=20 mean 20 degrees/pixel ~ 12 km,
    # which the Statistical API rejects.)
    geo = Geometry(geom, CRS.WGS84)
    utm = CRS.get_utm_from_wgs84(geom.centroid.x, geom.centroid.y)
    geo = geo.transform(utm)

    aggregation = SentinelHubStatistical.aggregation(
        evalscript=evalscript,
        time_interval=(t_from, t_to),
        aggregation_interval="P1M",
        resolution=(resolution, resolution),
        # The month still in progress is a short last interval: keep it (as a
        # month-to-date figure) instead of the API's default of skipping it.
        other_args={"aggregationInterval": {"lastIntervalBehavior": "SHORTEN"}},
    )
    request = SentinelHubStatistical(
        aggregation=aggregation,
        input_data=[SentinelHubStatistical.input_data(collection, other_args=other_args)],
        geometry=geo,
        config=cfg,
    )
    # Same request as request.get_data(), but keeping the response headers: the
    # API reports there what the request cost against the monthly quota.
    response = SentinelHubDownloadClient(config=cfg).download(
        [request.download_list[0]], decode_data=False)[0]
    result = response.decode()
    try:
        spent = float({k.lower(): v for k, v in response.headers.items()}
                      .get("x-processingunits-spent", 0))
    except (TypeError, ValueError):
        spent = 0.0

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
    return monthly, spent


def main():
    ap = argparse.ArgumentParser(description="Fetch monthly S2 NDVI + S1 VV/VH features from CDSE.")
    ap.add_argument("--level", choices=["municipality", "barangay"], default="municipality")
    ap.add_argument("--start", type=int, default=2018)
    ap.add_argument("--end", type=int, default=2025)
    ap.add_argument("--from-month", default=None, metavar="YYYY-MM",
                    help="Fetch only from this month (instead of whole years). Needs --out.")
    ap.add_argument("--to-month", default=None, metavar="YYYY-MM",
                    help="Last month of the window, inclusive (default: same as --from-month).")
    ap.add_argument("--max-pu", type=float, default=0,
                    help="Stop once this run has spent this many processing units (0 = no cap).")
    ap.add_argument("--resolution", type=int, default=20, help="Sampling resolution in metres.")
    ap.add_argument("--maxcc", type=float, default=0.6, help="Max S2 scene cloud cover (0-1).")
    ap.add_argument("--limit", type=int, default=0, help="Only process the first N areas (smoke test).")
    ap.add_argument("--sleep", type=float, default=1.0, help="Seconds between areas.")
    ap.add_argument("--resume", action="store_true",
                    help="Keep rows already in the output CSV and only fetch missing areas "
                         "(lets a second CDSE account finish what the first ran out of PU on).")
    ap.add_argument("--geojson", default=None,
                    help="Override the GeoJSON path (e.g. a subset of barangays to conserve PU).")
    ap.add_argument("--out", default=None, help="Override the output CSV path.")
    args = ap.parse_args()
    if args.from_month and not args.out:
        sys.exit("ERROR: --from-month fetches a few months only; give it its own --out file "
                 "so it cannot overwrite the full CSV (run_pipeline.py merges the two).")
    t_from, t_to = time_window(args)

    from sentinelhub import DataCollection

    cfg = make_config()
    s2 = DataCollection.SENTINEL2_L2A.define_from("s2l2a_cdse", service_url=CDSE_BASE)
    s1 = DataCollection.SENTINEL1_IW.define_from("s1iw_cdse", service_url=CDSE_BASE)
    s2_args = {"dataFilter": {"maxCloudCoverage": int(args.maxcc * 100)}}
    s1_args = {
        "dataFilter": {},
        "processing": {"backCoeff": "GAMMA0_TERRAIN", "orthorectify": True},
    }

    areas = load_geometries(args.level, args.geojson)
    if args.limit:
        areas = areas[: args.limit]
    name_col = args.level
    out_path = args.out or OUT[args.level]

    # Resume: carry over rows already fetched, skip those areas.
    rows = []
    if args.resume and os.path.exists(out_path):
        with open(out_path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        done = {r[name_col] for r in rows}
        areas = [a for a in areas if a[0] not in done]
        print(f"resume: {len(done)} areas already present, {len(areas)} to fetch")

    print(f"{len(areas)} {args.level} | {t_from:%Y-%m-%d} -> {t_to:%Y-%m-%d %H:%M} UTC | "
          f"S2 NDVI/EVI/NDWI + S1 VV/VH | {args.resolution} m")
    failed = 0
    pu_spent = 0.0
    n_requests = 0
    for i, (name, geom) in enumerate(areas, 1):
        if args.max_pu and pu_spent >= args.max_pu:
            print(f"  stopping: {pu_spent:.0f} processing units spent, cap is {args.max_pu:.0f}. "
                  f"{len(areas) - i + 1} areas not fetched.", file=sys.stderr)
            failed += len(areas) - i + 1
            break
        try:
            s2m, pu2 = run_statistical(cfg, s2, EVAL_S2_NDVI, s2_args, geom, t_from, t_to, args.resolution)
            pu_spent += pu2
            n_requests += 1
            s1m, pu1 = run_statistical(cfg, s1, EVAL_S1_VVVH, s1_args, geom, t_from, t_to, args.resolution)
            pu_spent += pu1
            n_requests += 1
        except Exception as e:  # noqa: BLE001
            print(f"  [{i}/{len(areas)}] {name}: ERROR {e}", file=sys.stderr)
            failed += 1
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
        print(f"  [{i}/{len(areas)}] {name}: S2 {len(s2m)} mo, S1 {len(s1m)} mo "
              f"({pu2 + pu1:.1f} PU)")
        time.sleep(args.sleep)

    print(f"\nprocessing units spent: {pu_spent:.1f} over {n_requests} requests")
    with open((args.out or OUT[args.level]) + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump({"processing_units": round(pu_spent, 1), "requests": n_requests,
                   "areas": len(areas), "areas_failed": failed,
                   "from": t_from.isoformat(), "to": t_to.isoformat()}, fh, indent=2)

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
    print(f"wrote {len(rows)} rows -> {out_path}")
    if failed:
        # Partial result is on disk (and loadable); the exit code still says so,
        # so an unattended run is recorded as failed rather than silently short.
        print(f"{failed} of {len(areas)} areas failed.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
