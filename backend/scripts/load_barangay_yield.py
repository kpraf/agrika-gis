"""
load_barangay_yield.py
======================

Load a barangay-yield CSV (from extract_barangay_yield.py) into the barangay_yield
table. Idempotent: upserts on (barangay_id, season_id). Only rows that actually
have a yield are loaded; blank "no data" rows are skipped.

Expected CSV columns (header row):
    municipality, barangay, year, season, area_ha, production_mt, yield_mt_ha

Barangays are matched to the DB by (municipality name + barangay name), folded for
case/diacritics/'Sta.'. Seasons are matched by (season_type, year) and created if
missing. Run add_barangay_yield_table.py first if the table doesn't exist.

Usage
    python backend/scripts/load_barangay_yield.py --csv db/barangay_yield_city-of-santa-rosa.csv
    python backend/scripts/load_barangay_yield.py --csv <file> --source "Santa Rosa CAO"
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


def fold(s):
    s = re.sub(r"\s+", " ", str(s).strip().lower()).replace(".", "").replace("sta ", "santa ")
    return s


def num(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser(description="Load a barangay-yield CSV into barangay_yield.")
    ap.add_argument("--csv", required=True, help="CSV from extract_barangay_yield.py")
    ap.add_argument("--source", default="City Agriculture Office (Planting & Harvesting report)")
    args = ap.parse_args()

    with open(args.csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    app = create_app()
    with app.app_context():
        # (folded municipality, folded barangay) -> barangay_id
        brgy_map = {
            (fold(r.municipality_name), fold(r.barangay_name)): r.barangay_id
            for r in db.session.execute(text(
                "SELECT b.barangay_id, b.barangay_name, m.municipality_name "
                "FROM barangays b JOIN municipalities m ON m.municipality_id = b.municipality_id"
            ))
        }
        season_cache = {}

        def season_id(stype, year):
            key = (stype, year)
            if key in season_cache:
                return season_cache[key]
            sid = db.session.execute(
                text("SELECT season_id FROM seasons WHERE season_type = :t AND year = :y"),
                {"t": stype, "y": year},
            ).scalar()
            if sid is None:
                sid = db.session.execute(
                    text("INSERT INTO seasons (season_type, year) VALUES (:t, :y) RETURNING season_id"),
                    {"t": stype, "y": year},
                ).scalar()
            season_cache[key] = sid
            return sid

        upsert = text(
            "INSERT INTO barangay_yield "
            "(barangay_id, season_id, yield_mt_ha, area_ha, production_mt, source) "
            "VALUES (:b, :s, :y, :a, :p, :src) "
            "ON CONFLICT (barangay_id, season_id) DO UPDATE SET "
            "yield_mt_ha = EXCLUDED.yield_mt_ha, area_ha = EXCLUDED.area_ha, "
            "production_mt = EXCLUDED.production_mt, source = EXCLUDED.source"
        )

        loaded = skipped_nodata = skipped_nomatch = 0
        unmatched = set()
        for r in rows:
            y = num(r.get("yield_mt_ha"))
            if y is None:
                skipped_nodata += 1  # "no data" row
                continue
            bid = brgy_map.get((fold(r["municipality"]), fold(r["barangay"])))
            if bid is None:
                unmatched.add(f'{r["municipality"]}/{r["barangay"]}')
                skipped_nomatch += 1
                continue
            sid = season_id(str(r["season"]).strip().capitalize(), int(float(r["year"])))
            db.session.execute(upsert, {
                "b": bid, "s": sid, "y": y,
                "a": num(r.get("area_ha")), "p": num(r.get("production_mt")), "src": args.source,
            })
            loaded += 1

        db.session.commit()
        total = db.session.execute(text("SELECT COUNT(*) FROM barangay_yield")).scalar()
        print(f"loaded {loaded}, skipped {skipped_nodata} (no-data), "
              f"{skipped_nomatch} (no barangay match). table now has {total} rows.")
        if unmatched:
            print(f"  unmatched: {sorted(unmatched)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
