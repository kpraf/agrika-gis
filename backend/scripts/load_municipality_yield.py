"""
load_municipality_yield.py
==========================

Load the compiled Ricelytics CSV (from compile_ricelytics.py) into the database:
upserts the needed rows in `seasons`, then upserts one row per
municipality-season into `municipality_yield_records`.

Idempotent - re-running updates existing rows rather than duplicating them
(relies on the UNIQUE(municipality_id, season_id) constraint).

Usage
-----
    python backend/scripts/load_municipality_yield.py \
        --csv backend/db/ricelytics_laguna_yield.csv

Expects the long-format CSV columns:
    municipality, season_type, year, yield_mt_ha, source_file, suspected_proxy
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402


def truthy(v) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def main():
    ap = argparse.ArgumentParser(description="Load compiled municipality yield CSV into the DB.")
    ap.add_argument("--csv", required=True, help="Path to the long-format CSV from compile_ricelytics.py")
    ap.add_argument("--source", default="Ricelytics", help="Value stored in the source column (default: Ricelytics)")
    args = ap.parse_args()

    with open(args.csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print("CSV has no rows.", file=sys.stderr)
        return 1

    app = create_app()
    with app.app_context():
        # municipality name -> id (normalise to be safe against spacing/case)
        muni = {
            r.municipality_name.strip().lower(): r.municipality_id
            for r in db.session.execute(
                text("SELECT municipality_id, municipality_name FROM municipalities")
            )
        }

        season_cache: dict[tuple[str, int], int] = {}

        def season_id(season_type: str, year: int) -> int:
            key = (season_type, year)
            if key in season_cache:
                return season_cache[key]
            sid = db.session.execute(
                text("SELECT season_id FROM seasons WHERE season_type = :t AND year = :y"),
                {"t": season_type, "y": year},
            ).scalar()
            if sid is None:
                sid = db.session.execute(
                    text("INSERT INTO seasons (season_type, year) VALUES (:t, :y) RETURNING season_id"),
                    {"t": season_type, "y": year},
                ).scalar()
            season_cache[key] = sid
            return sid

        inserted = updated = skipped = 0
        for r in rows:
            mid = muni.get(r["municipality"].strip().lower())
            if mid is None:
                print(f"  skip: no municipality match for {r['municipality']!r}")
                skipped += 1
                continue
            sid = season_id(r["season_type"].strip(), int(float(r["year"])))
            yld = float(r["yield_mt_ha"])
            is_proxy = truthy(r.get("suspected_proxy", "false"))

            existing = db.session.execute(
                text(
                    "SELECT muni_yield_id FROM municipality_yield_records "
                    "WHERE municipality_id = :m AND season_id = :s"
                ),
                {"m": mid, "s": sid},
            ).scalar()
            if existing:
                db.session.execute(
                    text(
                        "UPDATE municipality_yield_records "
                        "SET observed_yield = :y, source = :src, is_proxy = :p "
                        "WHERE muni_yield_id = :id"
                    ),
                    {"y": yld, "src": args.source, "p": is_proxy, "id": existing},
                )
                updated += 1
            else:
                db.session.execute(
                    text(
                        "INSERT INTO municipality_yield_records "
                        "(observed_yield, municipality_id, season_id, source, is_proxy) "
                        "VALUES (:y, :m, :s, :src, :p)"
                    ),
                    {"y": yld, "m": mid, "s": sid, "src": args.source, "p": is_proxy},
                )
                inserted += 1

        db.session.commit()
        total = db.session.execute(text("SELECT COUNT(*) FROM municipality_yield_records")).scalar()
        print(f"done. inserted {inserted}, updated {updated}, skipped {skipped}. table now has {total} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
