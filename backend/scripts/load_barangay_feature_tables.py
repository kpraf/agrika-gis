"""
load_barangay_feature_tables.py
===============================

Load per-barangay weather/satellite feature CSVs into weather_monthly_barangay /
satellite_monthly_barangay. Idempotent (upsert on barangay_id, year, month).

The feature CSVs are keyed by barangay NAME only, and barangay names repeat across
Laguna, so pass --municipalities to scope the name->barangay_id lookup to the
city/cities the CSV actually covers (avoids matching a same-named barangay
elsewhere). Run add_barangay_feature_tables.py first.

Usage
    # Santa Rosa + Cabuyao (from the earlier model fetch)
    python backend/scripts/load_barangay_feature_tables.py \
        --weather db/weather_barangay_sr_cabuyao_monthly.csv \
        --satellite db/satellite_barangay_sr_cabuyao_monthly.csv \
        --municipalities "City of Santa Rosa,City of Cabuyao"
    # Biñan
    python backend/scripts/load_barangay_feature_tables.py \
        --weather db/weather_barangay_binan_monthly.csv \
        --satellite db/satellite_barangay_binan_monthly.csv \
        --municipalities "City of Biñan"
"""
import argparse
import csv
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

WEATHER_COLS = ["rainfall_mm", "temp_mean_c", "humidity_mean_pct", "days"]
SATELLITE_COLS = ["ndvi_mean", "ndvi_std", "evi_mean", "evi_std", "ndwi_mean",
                  "ndwi_std", "s2_valid_px", "vv_mean", "vv_std", "vh_mean",
                  "vh_std", "s1_valid_px"]


def fold(s):
    return re.sub(r"\s+", " ", str(s).strip().lower()).replace(".", "").replace("sta ", "santa ")


def num(v):
    if v is None or str(v).strip() == "":
        return None
    return float(v)


def load_table(table, csv_path, value_cols, brgy_map):
    if not csv_path or not os.path.exists(csv_path):
        print(f"  (skip {table}: {csv_path} not found)")
        return
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    name_key = "barangay" if "barangay" in rows[0] else list(rows[0])[0]
    cols = ["barangay_id", "year", "month"] + value_cols
    placeholders = ", ".join(f":{c}" for c in cols)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in value_cols)
    sql = text(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) "
               f"ON CONFLICT (barangay_id, year, month) DO UPDATE SET {updates}")
    loaded = skipped = 0
    unmatched = set()
    for r in rows:
        bid = brgy_map.get(fold(r[name_key]))
        if bid is None:
            unmatched.add(r[name_key]); skipped += 1; continue
        params = {"barangay_id": bid, "year": int(r["year"]), "month": int(r["month"])}
        for c in value_cols:
            params[c] = num(r.get(c))
        db.session.execute(sql, params)
        loaded += 1
    db.session.commit()
    total = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    print(f"{table}: upserted {loaded}, skipped {skipped}. table now has {total} rows.")
    if unmatched:
        print(f"  unmatched: {sorted(unmatched)}")


def main():
    ap = argparse.ArgumentParser(description="Load barangay weather/satellite CSVs into the DB.")
    ap.add_argument("--weather")
    ap.add_argument("--satellite")
    ap.add_argument("--municipalities", required=True,
                    help="Comma-separated municipality names the CSV covers (scopes the name lookup).")
    args = ap.parse_args()
    munis = [m.strip() for m in args.municipalities.split(",") if m.strip()]

    app = create_app()
    with app.app_context():
        rows = db.session.execute(text(
            "SELECT b.barangay_id, b.barangay_name, m.municipality_name "
            "FROM barangays b JOIN municipalities m ON m.municipality_id = b.municipality_id"
        ))
        brgy_map = {fold(r.barangay_name): r.barangay_id for r in rows
                    if r.municipality_name in munis}
        if not brgy_map:
            sys.exit(f"No barangays found for municipalities {munis}. Check the names.")
        load_table("weather_monthly_barangay", args.weather, WEATHER_COLS, brgy_map)
        load_table("satellite_monthly_barangay", args.satellite, SATELLITE_COLS, brgy_map)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
