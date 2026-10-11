"""
load_feature_tables.py
======================

Load the monthly weather and satellite feature CSVs into the centralized spatial
database (weather_monthly, satellite_monthly). Idempotent: re-running upserts on
(municipality_id, year, month) rather than duplicating.

Inputs  (backend/db/)
    weather_laguna_monthly.csv     -> weather_monthly
    satellite_laguna_monthly.csv   -> satellite_monthly

Municipality names are matched to the DB by diacritics-folded name (the CSVs and
the municipalities table share the PSA/GeoJSON names, so this is exact-after-fold).
Blank cells (e.g. cloud-masked satellite months) load as NULL.

Run add_feature_tables.py first if the tables do not exist yet.

Usage
    python backend/scripts/load_feature_tables.py
    python backend/scripts/load_feature_tables.py --only weather
    # load a different file (the scheduled pipeline loads just its fetch window)
    python backend/scripts/load_feature_tables.py --weather-csv db/_run/weather_window.csv \
        --satellite-csv db/_run/satellite_window.csv
"""
import argparse
import csv
import os
import sys
import unicodedata

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "db"))
WEATHER_CSV = os.path.join(DB_DIR, "weather_laguna_monthly.csv")
SATELLITE_CSV = os.path.join(DB_DIR, "satellite_laguna_monthly.csv")

WEATHER_COLS = ["rainfall_mm", "temp_mean_c", "humidity_mean_pct", "days"]
SATELLITE_COLS = ["ndvi_mean", "ndvi_std", "evi_mean", "evi_std", "ndwi_mean",
                  "ndwi_std", "s2_valid_px", "vv_mean", "vv_std", "vh_mean",
                  "vh_std", "s1_valid_px"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.strip().lower().split())


def num(v):
    """CSV cell -> float/int/None (blank -> None)."""
    if v is None or str(v).strip() == "":
        return None
    f = float(v)
    return f


def load_table(table, csv_path, value_cols, muni_map):
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    cols = ["municipality_id", "year", "month"] + value_cols
    placeholders = ", ".join(f":{c}" for c in cols)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in value_cols)
    sql = text(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT (municipality_id, year, month) DO UPDATE SET {updates}"
    )

    skipped = 0
    unmatched = set()
    batch = []
    for r in rows:
        mid = muni_map.get(norm(r["municipality"]))
        if mid is None:
            unmatched.add(r["municipality"])
            skipped += 1
            continue
        params = {"municipality_id": mid, "year": int(r["year"]), "month": int(r["month"])}
        for c in value_cols:
            params[c] = num(r.get(c))
        batch.append(params)

    # One batched statement instead of a round trip per row: the same upsert, but
    # quick against a database on another continent.
    before = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    if batch:
        db.session.execute(sql, batch)
    db.session.commit()
    total = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    print(f"{table}: upserted {len(batch)} ({total - before} new, {len(batch) - (total - before)} "
          f"refreshed), skipped {skipped}. table now has {total} rows.")
    if unmatched:
        print(f"  unmatched municipality names: {sorted(unmatched)}")


def main():
    ap = argparse.ArgumentParser(description="Load weather/satellite CSVs into the DB.")
    ap.add_argument("--only", choices=["weather", "satellite"], help="Load just one table.")
    ap.add_argument("--weather-csv", default=WEATHER_CSV, help="Weather CSV to load.")
    ap.add_argument("--satellite-csv", default=SATELLITE_CSV, help="Satellite CSV to load.")
    args = ap.parse_args()

    app = create_app()
    with app.app_context():
        muni_map = {
            norm(r.municipality_name): r.municipality_id
            for r in db.session.execute(text("SELECT municipality_id, municipality_name FROM municipalities"))
        }
        if args.only in (None, "weather"):
            load_table("weather_monthly", args.weather_csv, WEATHER_COLS, muni_map)
        if args.only in (None, "satellite"):
            load_table("satellite_monthly", args.satellite_csv, SATELLITE_COLS, muni_map)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
