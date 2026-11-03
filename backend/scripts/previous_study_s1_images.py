"""
previous_study_s1_images.py
===========================

Sentinel-1 counterpart of previous_study_images.py, for the faithful form of this
study's Objective 1: the previous AgriKA study's image method (Ebron et al., 2025)
with a Sentinel-1 image added to every growth phase.

For each city (or barangay), season and growth phase one Sentinel-1 IW GRD
acquisition is rendered as a 224 x 224 false-colour picture over the same area
the NDVI image covers:

    red   = VV backscatter, -25 to 0 dB
    green = VH backscatter, -30 to -5 dB
    blue  = VV - VH (cross-polarisation ratio), 0 to 15 dB

Gamma0 terrain-flattened, orthorectified, as the system's monthly Sentinel-1
values (fetch_satellite_cdse.py). Pixels outside the area are black. The picture
then goes through the same ResNet50 as the NDVI picture.

Date: radar sees through cloud, so no cloud test is needed. The acquisition
closest to the date of the phase's NDVI image is taken (the mid-date of the
phase when there is no NDVI image), so both pictures of a phase show the same
moment as nearly as possible.

Outputs (backend/db/previous_study/, or --prefix for barangays)
    images_s1/<Area>_<year>S<semester>_P<phase>_<date>.png
    image_index_s1.csv

Usage
    python backend/scripts/previous_study_s1_images.py --cities Victoria --years 2023
    python backend/scripts/previous_study_s1_images.py --years 2018-2026 --resume --max-pu 800
"""
import argparse
import csv
import datetime as dt
import os

import numpy as np

import fetch_satellite_cdse as cdse
import previous_study_images as psi

COLUMNS = ["city", "year", "semester", "phase", "date", "ndvi_date", "file", "pu"]

EVALSCRIPT = """
//VERSION=3
function setup() {
    return { input: ["VV", "VH", "dataMask"], output: { bands: 4 } };
}
function db(x) { return 10 * Math.log(x) / Math.LN10; }
function clip(v) { return Math.max(0, Math.min(1, v)); }
function evaluatePixel(s) {
    if (s.dataMask === 0 || !(s.VV > 0) || !(s.VH > 0)) return [0, 0, 0, 0];
    let vv = db(s.VV), vh = db(s.VH);
    return [clip((vv + 25) / 25), clip((vh + 30) / 25), clip((vv - vh) / 15), 1];
}
"""


def acquisitions(catalog, collection, geom, start, end):
    from sentinelhub import CRS, Geometry
    search = catalog.search(collection, geometry=Geometry(geom, CRS.WGS84), time=(start.isoformat(), end.isoformat()),
                            fields={"include": ["properties.datetime"], "exclude": []})
    return sorted({item["properties"]["datetime"][:10] for item in search})


def fetch(cfg, collection, geom, day):
    from sentinelhub import CRS, Geometry, MimeType, SentinelHubDownloadClient, SentinelHubRequest
    request = SentinelHubRequest(
        evalscript=EVALSCRIPT,
        input_data=[SentinelHubRequest.input_data(
            data_collection=collection, time_interval=(day, day),
            other_args={"dataFilter": {"acquisitionMode": "IW", "polarization": "DV"},
                        "processing": {"backCoeff": "GAMMA0_TERRAIN", "orthorectify": True}})],
        responses=[SentinelHubRequest.output_response("default", MimeType.PNG)],
        geometry=Geometry(geom, CRS.WGS84), size=(224, 224), config=cfg)
    response = SentinelHubDownloadClient(config=cfg).download([request.download_list[0]], decode_data=False)[0]
    try:
        spent = float({k.lower(): v for k, v in response.headers.items()}.get("x-processingunits-spent", 0))
    except (TypeError, ValueError):
        spent = 0.0
    return np.asarray(response.decode()), spent


def load_areas(geojson, name_field):
    """{name: shapely geometry}; the previous study's rice fields by default."""
    if not geojson:
        return psi.load_fields()
    import json
    from shapely.geometry import shape
    with open(geojson, encoding="utf-8") as fh:
        return {f["properties"][name_field]: shape(f["geometry"]) for f in json.load(fh)["features"]}


def main():
    ap = argparse.ArgumentParser(description="Download one Sentinel-1 picture per area, season and growth phase.")
    ap.add_argument("--cities", default="", help="Comma list of areas (default: all).")
    ap.add_argument("--years", default="2018-2026")
    ap.add_argument("--semesters", default="1,2")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--max-pu", type=float, default=0)
    ap.add_argument("--geojson", default="", help="Areas to use instead of the previous study's rice fields.")
    ap.add_argument("--name-field", default="name")
    ap.add_argument("--ndvi-index", default=psi.INDEX, help="NDVI index whose dates the radar dates follow.")
    ap.add_argument("--out-dir", default=psi.OUT_DIR)
    ap.add_argument("--part", default="", help="N/M: take every M-th area starting at N and write its own index "
                                               "(image_index_s1.pN.csv), so several downloads can run side by side.")
    ap.add_argument("--merge", action="store_true", help="Merge the part indexes into image_index_s1.csv and exit.")
    args = ap.parse_args()
    if args.merge:
        return merge(args.out_dir)

    from PIL import Image
    from sentinelhub import DataCollection, SentinelHubCatalog

    img_dir = os.path.join(args.out_dir, "images_s1")
    main_index = os.path.join(args.out_dir, "image_index_s1.csv")
    index = main_index
    os.makedirs(img_dir, exist_ok=True)
    cfg = cdse.make_config()
    s1 = DataCollection.SENTINEL1_IW.define_from("s1iw_cdse", service_url=cdse.CDSE_BASE)
    catalog = SentinelHubCatalog(config=cfg)
    areas = load_areas(args.geojson, args.name_field)
    names = [c.strip() for c in args.cities.split(",") if c.strip()] or sorted(areas)
    if args.part:
        n_part, m_parts = (int(v) for v in args.part.split("/"))
        names = [a for i, a in enumerate(names) if i % m_parts == n_part]
        index = os.path.join(args.out_dir, f"image_index_s1.p{n_part}.csv")

    ndvi_dates = {}
    if os.path.exists(args.ndvi_index):
        with open(args.ndvi_index, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["date"]:
                    ndvi_dates[(r["city"], int(r["year"]), int(r["semester"]), int(r["phase"]))] = r["date"]

    rows, done = [], set()
    if args.resume:
        for path in {main_index, index}:
            if os.path.exists(path):
                with open(path, newline="", encoding="utf-8") as fh:
                    found = list(csv.DictReader(fh))
                done |= {(r["city"], int(r["year"]), int(r["semester"]), int(r["phase"])) for r in found}
                if path == index:
                    rows = found

    total_pu, n = 0.0, 0
    for name in names:
        geom = areas[name]
        for year in psi.parse_years(args.years):
            for semester in [int(s) for s in args.semesters.split(",")]:
                for phase, start, end in psi.phase_windows(year, semester):
                    k = (name, year, semester, phase)
                    if k in done or end >= dt.date.today():          # done already, or the phase has not ended yet
                        continue
                    if args.max_pu and total_pu >= args.max_pu:
                        print(f"stopping: {total_pu:.1f} processing units spent, cap is {args.max_pu:.0f}")
                        return write(index, rows, total_pu, n)
                    target = dt.date.fromisoformat(ndvi_dates[k]) if k in ndvi_dates else start + (end - start) / 2
                    row = {"city": name, "year": year, "semester": semester, "phase": phase, "date": "",
                           "ndvi_date": ndvi_dates.get(k, ""), "file": "", "pu": 0.0}
                    days = acquisitions(catalog, s1, geom, start, end)
                    days.sort(key=lambda d: abs((dt.date.fromisoformat(d) - target).days))
                    for day in days[:3]:
                        rgba, spent = fetch(cfg, s1, geom, day)
                        total_pu += spent
                        n += 1
                        row["pu"] = round(row["pu"] + spent, 4)
                        if not (rgba[..., 3] > 0).any():
                            continue
                        safe = name.replace(" ", "").replace("/", "-").replace("|", "_")
                        fname = f"{safe}_{year}S{semester}_P{phase}_{day}.png"
                        Image.fromarray(rgba, "RGBA").save(os.path.join(img_dir, fname))
                        row.update(date=day, file=fname)
                        break
                    rows.append(row)
                    print(f"{name:<14} {year} S{semester} P{phase}: {row['date'] or 'no image'} "
                          f"({len(days)} acquisitions, {row['pu']} PU, total {total_pu:.1f})", flush=True)
                    if len(rows) % 10 == 0:
                        write(index, rows, total_pu, n, quiet=True)
    return write(index, rows, total_pu, n)


def merge(out_dir):
    import glob
    merged = {}
    for path in [os.path.join(out_dir, "image_index_s1.csv")] + sorted(glob.glob(os.path.join(out_dir, "image_index_s1.p*.csv"))):
        if os.path.exists(path):
            with open(path, newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    k = (r["city"], int(r["year"]), int(r["semester"]), int(r["phase"]))
                    if k not in merged or (r["file"] and not merged[k]["file"]):
                        merged[k] = r
    rows = [merged[k] for k in sorted(merged)]
    write(os.path.join(out_dir, "image_index_s1.csv"), rows, sum(float(r["pu"] or 0) for r in rows), len(rows))
    print(f"merged {len(rows)} rows; with a picture: {sum(1 for r in rows if r['file'])}")
    return 0


def write(index, rows, total_pu, n, quiet=False):
    with open(index, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    if not quiet:
        print(f"\nprocessing units spent: {total_pu:.2f} over {n} requests | index -> {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
