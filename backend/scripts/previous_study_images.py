"""
previous_study_images.py
========================

Rebuilds the image dataset of the previous AgriKA study (Ebron et al., 2025) so
that its method can be re-run on current data.

What is reproduced from their code and thesis
    * the rice-field outlines of each city   (their static/fields_coordinates.geojson)
    * the NDVI image request                 (their colour script, 224 x 224 pixels)
    * the three growth phases per season     (their Tables 11 and 12)
          Dry  (S1)  Sep 16 - Nov 15 | Nov 16 - Jan 15 | Jan 16 - Mar 15
          Wet  (S2)  Mar 16 - May 15 | May 16 - Jul 15 | Jul 16 - Sep 15
    * the green ratio                        (their Appendix S)

What cannot be reproduced exactly
    * They chose each image by eye and did not publish the dates. Here the
      clearest acquisition of each phase is chosen automatically: candidates are
      tried from the least cloudy scene upward, and the first whose field area is
      less than 30% cloud is kept (30% is the threshold of their real-time code).

One request per candidate returns the NDVI picture and the cloud flag together,
to spare the Copernicus quota; the saved picture is identical to what their
script produces.

Outputs (backend/db/previous_study/)
    images/<City>_<year>S<semester>_P<phase>_<date>.png
    image_index.csv     one row per city, season and phase

Usage
    python backend/scripts/previous_study_images.py --cities Victoria,Calamba --years 2023
    python backend/scripts/previous_study_images.py --years 2018-2025 --resume --max-pu 600
"""
import argparse
import csv
import datetime as dt
import json
import os

import numpy as np

import fetch_satellite_cdse as cdse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.abspath(os.path.join(HERE, "..", "db", "previous_study"))
FIELDS = os.path.join(OUT_DIR, "fields_coordinates.geojson")
IMG_DIR = os.path.join(OUT_DIR, "images")
INDEX = os.path.join(OUT_DIR, "image_index.csv")
COLUMNS = ["city", "year", "semester", "phase", "date", "scene_cloud_pct", "field_cloud_frac",
           "green_ratio", "file", "candidates_tried", "pu"]

MAX_FIELD_CLOUD = 0.30
MAX_CANDIDATES = 4

# Their NDVI colour script (Appendix P), with the scene-classification cloud flag
# carried in the alpha channel: 1 = clear, 0.5 = cloud (SCL 7, 8, 9, as in their
# true-colour script), 0 = no data.
EVALSCRIPT = """
//VERSION=3
function setup() {
    return { input: ["B04", "B08", "SCL", "dataMask"], output: { bands: 4 } };
}
function evaluatePixel(sample) {
    let val = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
    let imgVals = null;
    if (val < -1.1) imgVals = [0, 0, 0];
    else if (val < -0.2) imgVals = [0.75, 0.75, 0.75];
    else if (val < -0.1) imgVals = [0.86, 0.86, 0.86];
    else if (val < 0) imgVals = [1, 1, 0.88];
    else if (val < 0.025) imgVals = [1, 1, 0.5];
    else if (val < 0.05) imgVals = [0.93, 0.1, 0.71];
    else if (val < 0.075) imgVals = [0.87, 0.85, 0.61];
    else if (val < 0.1) imgVals = [0.8, 0.78, 0.51];
    else if (val < 0.125) imgVals = [0.74, 0.72, 0.42];
    else if (val < 0.15) imgVals = [0.69, 0.76, 0.38];
    else if (val < 0.175) imgVals = [0.64, 0.8, 0.35];
    else if (val < 0.2) imgVals = [0.57, 0.75, 0.32];
    else if (val < 0.25) imgVals = [0.5, 0.7, 0.28];
    else if (val < 0.3) imgVals = [0.44, 0.64, 0.25];
    else if (val < 0.35) imgVals = [0.38, 0.59, 0.21];
    else if (val < 0.4) imgVals = [0.31, 0.54, 0.18];
    else if (val < 0.45) imgVals = [0.25, 0.49, 0.14];
    else if (val < 0.5) imgVals = [0.19, 0.43, 0.11];
    else if (val < 0.55) imgVals = [0.13, 0.38, 0.07];
    else if (val < 0.6) imgVals = [0.06, 0.33, 0.04];
    else imgVals = [0, 0.27, 0];
    let cloud = (sample.SCL === 7 || sample.SCL === 8 || sample.SCL === 9);
    imgVals.push(sample.dataMask === 0 ? 0 : (cloud ? 0.5 : 1));
    return imgVals;
}
"""


def phase_windows(year, semester):
    """[(phase, start_date, end_date)] of one season, from their Tables 11 and 12."""
    d = dt.date
    if semester == 1:
        return [(1, d(year - 1, 9, 16), d(year - 1, 11, 15)), (2, d(year - 1, 11, 16), d(year, 1, 15)),
                (3, d(year, 1, 16), d(year, 3, 15))]
    return [(1, d(year, 3, 16), d(year, 5, 15)), (2, d(year, 5, 16), d(year, 7, 15)), (3, d(year, 7, 16), d(year, 9, 15))]


def load_fields():
    """{city: shapely MultiPolygon} of the rice fields each image is clipped to."""
    from shapely.geometry import MultiPolygon, shape
    out = {}
    with open(FIELDS, encoding="utf-8") as fh:
        for feat in json.load(fh)["features"]:
            out.setdefault(feat["properties"]["city"], []).append(shape(feat["geometry"]))
    return {city: MultiPolygon(polys) for city, polys in out.items()}


def green_ratio(rgb):
    """Their Appendix S, on an RGB array: light-green pixels over non-black pixels."""
    def in_range(lo, hi):
        return np.all((rgb >= np.array(lo)) & (rgb <= np.array(hi)), axis=-1)

    valid = np.any(rgb != 0, axis=-1)
    green = in_range([49, 111, 29], [159, 198, 89])
    exclusion = (in_range([0, 60, 0], [5, 75, 5]) | in_range([248, 153, 151], [237, 13, 182])
                 | in_range([251, 207, 159], [254, 255, 255]))
    return float((green & ~exclusion).sum() / valid.sum()) if valid.sum() else 0.0


def candidates(catalog, collection, geom, start, end):
    """Acquisition dates in the window, least cloudy scene first."""
    from sentinelhub import CRS, Geometry
    search = catalog.search(collection, geometry=Geometry(geom, CRS.WGS84), time=(start.isoformat(), end.isoformat()),
                            fields={"include": ["properties.datetime", "properties.eo:cloud_cover"], "exclude": []})
    best = {}
    for item in search:
        day = item["properties"]["datetime"][:10]
        cc = item["properties"].get("eo:cloud_cover", 100.0)
        best[day] = min(cc, best.get(day, 101.0))
    return sorted(best.items(), key=lambda kv: kv[1])


def fetch(cfg, collection, geom, day):
    """(RGBA array, processing units spent) for one acquisition date."""
    from sentinelhub import CRS, Geometry, MimeType, SentinelHubDownloadClient, SentinelHubRequest
    request = SentinelHubRequest(
        evalscript=EVALSCRIPT,
        input_data=[SentinelHubRequest.input_data(data_collection=collection, time_interval=(day, day),
                                                  other_args={"dataFilter": {"mosaickingOrder": "leastCC"}})],
        responses=[SentinelHubRequest.output_response("default", MimeType.PNG)],
        geometry=Geometry(geom, CRS.WGS84), size=(224, 224), config=cfg)
    response = SentinelHubDownloadClient(config=cfg).download([request.download_list[0]], decode_data=False)[0]
    try:
        spent = float({k.lower(): v for k, v in response.headers.items()}.get("x-processingunits-spent", 0))
    except (TypeError, ValueError):
        spent = 0.0
    return np.asarray(response.decode()), spent


def parse_years(text):
    if "-" in text:
        a, b = text.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(y) for y in text.split(",")]


def main():
    ap = argparse.ArgumentParser(description="Download the previous study's NDVI phase images.")
    ap.add_argument("--cities", default="", help="Comma list of cities as named in their field file (default: all).")
    ap.add_argument("--years", default="2018-2025", help="Yield years, e.g. 2023 or 2018-2025.")
    ap.add_argument("--semesters", default="1,2", help="1 = dry, 2 = wet.")
    ap.add_argument("--resume", action="store_true", help="Skip city-season-phases already in the index.")
    ap.add_argument("--max-pu", type=float, default=0, help="Stop after spending this many processing units (0 = no cap).")
    ap.add_argument("--part", default="", help="Write to image_index.<part>.csv, so several runs can work side by side; "
                                               "merge afterwards with --merge.")
    ap.add_argument("--merge", action="store_true", help="Merge every image_index.<part>.csv into image_index.csv and exit.")
    ap.add_argument("--geojson", default="", help="Areas to use instead of their rice fields (e.g. barangay outlines).")
    ap.add_argument("--name-field", default="name")
    ap.add_argument("--out-dir", default="", help="Folder for the index and pictures (default: db/previous_study).")
    args = ap.parse_args()
    global OUT_DIR, IMG_DIR, INDEX
    if args.out_dir:
        OUT_DIR = args.out_dir
        IMG_DIR, INDEX = os.path.join(OUT_DIR, "images"), os.path.join(OUT_DIR, "image_index.csv")

    if args.merge:
        import glob
        merged = {}
        for path in [INDEX] + sorted(glob.glob(os.path.join(OUT_DIR, "image_index.*.csv"))):
            if os.path.exists(path):
                with open(path, newline="", encoding="utf-8") as fh:
                    for r in csv.DictReader(fh):
                        key = (r["city"], int(r["year"]), int(r["semester"]), int(r["phase"]))
                        if key not in merged or (r["file"] and not merged[key]["file"]):
                            merged[key] = r
        with open(INDEX, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(merged[k] for k in sorted(merged))
        print(f"merged {len(merged)} rows -> {INDEX}; with an image: {sum(1 for r in merged.values() if r['file'])}")
        return 0

    from PIL import Image
    from sentinelhub import DataCollection, SentinelHubCatalog

    cfg = cdse.make_config()
    s2 = DataCollection.SENTINEL2_L2A.define_from("s2l2a_cdse", service_url=cdse.CDSE_BASE)
    catalog = SentinelHubCatalog(config=cfg)
    if args.geojson:
        from shapely.geometry import shape
        with open(args.geojson, encoding="utf-8") as fh:
            fields = {f["properties"][args.name_field]: shape(f["geometry"]) for f in json.load(fh)["features"]}
    else:
        fields = load_fields()
    cities = [c.strip() for c in args.cities.split(",") if c.strip()] or sorted(fields)
    os.makedirs(IMG_DIR, exist_ok=True)

    out_index = os.path.join(OUT_DIR, f"image_index.{args.part}.csv") if args.part else INDEX
    rows, done = [], set()
    if args.resume:
        for path in {INDEX, out_index}:
            if os.path.exists(path):
                with open(path, newline="", encoding="utf-8") as fh:
                    found = list(csv.DictReader(fh))
                done |= {(r["city"], int(r["year"]), int(r["semester"]), int(r["phase"])) for r in found}
                if path == out_index:
                    rows = found

    total_pu, n_requests = 0.0, 0
    for city in cities:
        geom = fields[city]
        for year in parse_years(args.years):
            for semester in [int(s) for s in args.semesters.split(",")]:
                for phase, start, end in phase_windows(year, semester):
                    if (city, year, semester, phase) in done or end >= dt.date.today():
                        continue                        # done already, or the phase has not ended yet
                    if args.max_pu and total_pu >= args.max_pu:
                        print(f"stopping: {total_pu:.1f} processing units spent, cap is {args.max_pu:.0f}")
                        break
                    row = {"city": city, "year": year, "semester": semester, "phase": phase, "date": "", "scene_cloud_pct": "",
                           "field_cloud_frac": "", "green_ratio": "", "file": "", "candidates_tried": 0, "pu": 0.0}
                    for day, scene_cc in candidates(catalog, s2, geom, start, end)[:MAX_CANDIDATES]:
                        rgba, spent = fetch(cfg, s2, geom, day)
                        total_pu += spent
                        n_requests += 1
                        row["candidates_tried"] += 1
                        row["pu"] = round(row["pu"] + spent, 4)
                        alpha = rgba[..., 3]
                        inside = alpha > 0
                        if not inside.any():
                            continue
                        cloud = float(((alpha > 64) & (alpha < 192)).sum() / inside.sum())
                        if cloud >= MAX_FIELD_CLOUD:
                            continue
                        picture = rgba.copy()
                        picture[..., 3] = np.where(inside, 255, 0)      # as their script returns it
                        name = f"{city.replace(' ', '').replace('|', '_')}_{year}S{semester}_P{phase}_{day}.png"
                        Image.fromarray(picture, "RGBA").save(os.path.join(IMG_DIR, name))
                        row.update(date=day, scene_cloud_pct=round(scene_cc, 1), field_cloud_frac=round(cloud, 3),
                                   green_ratio=round(green_ratio(picture[..., :3]), 6), file=name)
                        break
                    rows.append(row)
                    print(f"{city:<12} {year} S{semester} P{phase}: "
                          + (f"{row['date']} cloud {row['field_cloud_frac']} green {row['green_ratio']}" if row["file"]
                             else "no usable image") + f" ({row['candidates_tried']} tried, {row['pu']} PU)", flush=True)
                    with open(out_index, "w", newline="", encoding="utf-8") as fh:
                        w = csv.DictWriter(fh, fieldnames=COLUMNS)
                        w.writeheader()
                        w.writerows(rows)
    print(f"\nprocessing units spent: {total_pu:.2f} over {n_requests} requests | index -> {out_index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
