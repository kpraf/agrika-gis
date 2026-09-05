"""
fetch_weather_openmeteo.py
==========================

Pull historical monthly rainfall + temperature for every Laguna municipality
from the Open-Meteo Historical Weather (Archive) API, which is backed by the
ERA5 / ERA5-Land reanalysis (~9 km grid).

No API key and no third-party packages are required - this uses only the Python
standard library. Each municipality is sampled at its polygon centroid (computed
here from db/geojson/Laguna_Municipalities.geojson via the shoelace formula), so
the database does not need to be running to produce the CSV.

Output
------
Writes db/weather_laguna_monthly.csv with one row per municipality-year-month:

    municipality, year, month, rainfall_mm, temp_mean_c, days

where
    rainfall_mm  - total precipitation for the month (mm), summed from daily
    temp_mean_c  - mean daily 2 m air temperature for the month (degrees C)
    days         - number of days that had data (sanity / gap check)

Feed that CSV into the LSTM branch of the model as a monthly time series, or
load it into a weather table with a companion loader script.

Usage
-----
    python backend/scripts/fetch_weather_openmeteo.py
    python backend/scripts/fetch_weather_openmeteo.py --start 2018 --end 2025
    python backend/scripts/fetch_weather_openmeteo.py --level barangay   # 682 points

Notes
-----
- The archive lags real time by ~5 days; whole past years are always complete.
- Open-Meteo asks that heavy users be gentle; we sleep briefly between calls and
  retry transient failures. 30 municipalities is well within the free tier.
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.abspath(os.path.join(HERE, "..", "db"))
GEOJSON = {
    "municipality": os.path.join(DB_DIR, "geojson", "Laguna_Municipalities.geojson"),
    "barangay": os.path.join(DB_DIR, "geojson", "Laguna_Barangays.geojson"),
}
OUT = {
    "municipality": os.path.join(DB_DIR, "weather_laguna_monthly.csv"),
    "barangay": os.path.join(DB_DIR, "weather_laguna_barangay_monthly.csv"),
}
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


# --- geometry: area-weighted centroid of a (Multi)Polygon, no shapely ---------
def _ring_area_centroid(ring):
    """Signed area and centroid of one linear ring via the shoelace formula."""
    a = cx = cy = 0.0
    n = len(ring)
    for i in range(n - 1):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[i + 1][0], ring[i + 1][1]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a *= 0.5
    if a == 0:
        # Degenerate ring: fall back to the mean of its vertices.
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return 0.0, sum(xs) / len(xs), sum(ys) / len(ys)
    return a, cx / (6 * a), cy / (6 * a)


def centroid(geometry):
    """Area-weighted centroid (lon, lat) of a Polygon or MultiPolygon geometry."""
    gtype = geometry["type"]
    if gtype == "Polygon":
        polygons = [geometry["coordinates"]]
    elif gtype == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise ValueError(f"unsupported geometry type: {gtype}")

    tot_a = tot_x = tot_y = 0.0
    for poly in polygons:
        exterior = poly[0]  # ring[0] is the outer boundary
        a, cx, cy = _ring_area_centroid(exterior)
        w = abs(a)
        tot_a += w
        tot_x += cx * w
        tot_y += cy * w
    if tot_a == 0:
        raise ValueError("zero total area")
    return round(tot_x / tot_a, 5), round(tot_y / tot_a, 5)  # lon, lat


def load_points(level):
    """[(name, lon, lat)] for each feature in the level's GeoJSON."""
    with open(GEOJSON[level], encoding="utf-8") as fh:
        data = json.load(fh)
    points = []
    for feat in data["features"]:
        name = feat["properties"].get("name")
        lon, lat = centroid(feat["geometry"])
        points.append((name, lon, lat))
    points.sort(key=lambda p: p[0])
    return points


# --- Open-Meteo archive fetch -------------------------------------------------
def fetch_daily(lat, lon, start_date, end_date, retries=3):
    """Daily precipitation_sum + temperature_2m_mean for one point."""
    params = urllib.parse.urlencode({
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum,temperature_2m_mean",
        "timezone": "Asia/Manila",
    })
    url = f"{ARCHIVE_URL}?{params}"
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "agrika-gis/weather"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))["daily"]
        except urllib.error.HTTPError as e:
            last_err = e
            # Rate-limited: back off hard (Open-Meteo's free limit is per-minute).
            wait = 20 * (attempt + 1) if e.code == 429 else 3 * (attempt + 1)
            time.sleep(wait)
        except Exception as e:  # noqa: BLE001 - network is best-effort here
            last_err = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"failed after {retries} tries: {last_err}")


def to_monthly(daily):
    """Collapse daily arrays into {(year, month): (rain_mm, temp_mean, days)}."""
    times = daily["time"]
    rain = daily["precipitation_sum"]
    temp = daily["temperature_2m_mean"]
    rain_by = defaultdict(float)
    temp_sum = defaultdict(float)
    temp_n = defaultdict(int)
    for t, r, tp in zip(times, rain, temp):
        year, month = int(t[0:4]), int(t[5:7])
        key = (year, month)
        if r is not None:
            rain_by[key] += r
        if tp is not None:
            temp_sum[key] += tp
            temp_n[key] += 1
    out = {}
    for key in sorted(set(rain_by) | set(temp_n)):
        n = temp_n.get(key, 0)
        out[key] = (
            round(rain_by.get(key, 0.0), 2),
            round(temp_sum[key] / n, 2) if n else None,
            n,
        )
    return out


def main():
    ap = argparse.ArgumentParser(description="Fetch Laguna monthly weather from Open-Meteo (ERA5).")
    ap.add_argument("--start", type=int, default=2018, help="First year (default 2018).")
    ap.add_argument("--end", type=int, default=2025, help="Last year, inclusive (default 2025).")
    ap.add_argument("--level", choices=["municipality", "barangay"], default="municipality")
    ap.add_argument("--sleep", type=float, default=1.0, help="Seconds between API calls.")
    ap.add_argument("--resume", action="store_true",
                    help="Keep rows already in the output CSV and only fetch missing names.")
    args = ap.parse_args()

    start_date = f"{args.start}-01-01"
    end_date = f"{args.end}-12-31"
    points = load_points(args.level)
    out_path = OUT[args.level]
    name_col = "municipality" if args.level == "municipality" else "barangay"

    # Resume: carry over existing rows, skip names we already have.
    rows = []
    done = set()
    if args.resume and os.path.exists(out_path):
        with open(out_path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        done = {r[name_col] for r in rows}
        points = [p for p in points if p[0] not in done]
        print(f"resume: {len(done)} names already present, {len(points)} to fetch")

    print(f"{len(points)} {args.level} centroids | {start_date} -> {end_date} | Open-Meteo ERA5")
    for i, (name, lon, lat) in enumerate(points, 1):
        try:
            monthly = to_monthly(fetch_daily(lat, lon, start_date, end_date))
        except Exception as e:  # noqa: BLE001
            print(f"  [{i}/{len(points)}] {name}: ERROR {e}", file=sys.stderr)
            continue
        for (year, month), (rain_mm, temp_c, days) in monthly.items():
            rows.append({
                name_col: name,
                "year": year,
                "month": month,
                "rainfall_mm": rain_mm,
                "temp_mean_c": temp_c,
                "days": days,
            })
        print(f"  [{i}/{len(points)}] {name} ({lat},{lon}): {len(monthly)} months")
        time.sleep(args.sleep)

    if not rows:
        print("No data fetched (network blocked?). Nothing written.", file=sys.stderr)
        return 1

    rows.sort(key=lambda r: (r[name_col], int(r["year"]), int(r["month"])))
    fieldnames = [name_col, "year", "month", "rainfall_mm", "temp_mean_c", "days"]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
