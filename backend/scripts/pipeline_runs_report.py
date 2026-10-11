"""
pipeline_runs_report.py
=======================

Print the pipeline run log (pipeline_runs) - the record that the pipeline runs
on its own, and what each run did. One line per run, oldest first, then totals.

    # local DB (backend/.env)
    python backend/scripts/pipeline_runs_report.py

    # production (Supabase) - reads PROD_DATABASE_URL from backend/.env.prod
    python backend/scripts/pipeline_runs_report.py --prod

    # also write the table as CSV (for the manuscript)
    python backend/scripts/pipeline_runs_report.py --csv runs.csv
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

COLS = ["run_id", "started", "minutes", "triggered_by", "mode", "window", "status",
        "weather_new", "weather_refreshed", "satellite_new", "satellite_refreshed", "cells",
        "barangays", "brgy_new", "brgy_refreshed", "brgy_cells",
        "violations", "predictions_new", "brgy_predictions_new", "processing_units", "encrypted", "notes"]


def main():
    ap = argparse.ArgumentParser(description="Print the pipeline run log.")
    ap.add_argument("--prod", action="store_true", help="Read the production (Supabase) DB.")
    ap.add_argument("--csv", help="Also write the rows to this CSV file.")
    args = ap.parse_args()

    if args.prod:
        try:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(BACKEND, ".env.prod"))
        except ImportError:
            pass
        url = os.environ.get("PROD_DATABASE_URL", "").strip().strip('"').strip("'")
        if not url:
            sys.exit("ERROR: PROD_DATABASE_URL not set (backend/.env.prod).")
        os.environ["DATABASE_URL"] = url
        print(f"SOURCE: PRODUCTION @ {url.rsplit('@', 1)[-1].split('/', 1)[0]}")

    # Imported here, not at the top: Config reads DATABASE_URL at import time.
    from app import create_app
    from extensions import db

    app = create_app()
    with app.app_context():
        if db.session.execute(text("SELECT to_regclass('pipeline_runs')")).scalar() is None:
            print("No pipeline_runs table yet - the pipeline has not run against this database.")
            return 0
        rows = db.session.execute(text(
            "SELECT run_id, to_char(started_at AT TIME ZONE 'Asia/Manila', 'YYYY-MM-DD HH24:MI') AS started, "
            "round(extract(epoch FROM (finished_at - started_at)) / 60.0, 1) AS minutes, "
            "triggered_by, mode, "
            "CASE WHEN window_from IS NULL THEN '' WHEN window_from = window_to THEN window_from "
            "     ELSE window_from || '..' || window_to END AS window, status, "
            "weather_rows_new AS weather_new, weather_rows_refreshed AS weather_refreshed, "
            "satellite_rows_new AS satellite_new, satellite_rows_refreshed AS satellite_refreshed, "
            "CASE WHEN cells_expected IS NULL THEN '' ELSE weather_cells || '+' || satellite_cells || "
            "     ' of ' || cells_expected || '+' || cells_expected END AS cells, "
            "barangays, barangay_rows_new AS brgy_new, barangay_rows_refreshed AS brgy_refreshed, "
            "CASE WHEN barangay_cells_expected IS NULL THEN '' ELSE barangay_cells || ' of ' || "
            "     barangay_cells_expected END AS brgy_cells, "
            "integrity_violations AS violations, predictions_new, "
            "barangay_predictions_new AS brgy_predictions_new, processing_units, "
            "db_encrypted AS encrypted, COALESCE(notes, '') AS notes "
            "FROM pipeline_runs ORDER BY run_id")).mappings().all()

    if not rows:
        print("pipeline_runs is empty.")
        return 0
    table = [[("" if r[c] is None else str(r[c])) for c in COLS] for r in rows]
    widths = [max(len(c), *(len(t[i]) for t in table)) for i, c in enumerate(COLS)]
    print("  ".join(c.ljust(w) for c, w in zip(COLS, widths)))
    print("  ".join("-" * w for w in widths))
    for t in table:
        print("  ".join(v.ljust(w) for v, w in zip(t, widths)))

    done = [r for r in rows if r["status"] != "running"]
    ok = sum(1 for r in done if r["status"] == "ok")
    by = {}
    for r in rows:
        by[r["triggered_by"]] = by.get(r["triggered_by"], 0) + 1
    pu = sum(float(r["processing_units"] or 0) for r in rows)
    print(f"\n{len(rows)} runs ({', '.join(f'{v} {k}' for k, v in sorted(by.items()))}); "
          f"{ok} of {len(done)} finished runs succeeded; "
          f"{sum(int(r['violations'] or 0) for r in rows)} integrity violations; "
          f"{pu:.0f} Copernicus processing units in total. Times are Philippine time.")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(COLS)
            w.writerows(table)
        print(f"wrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
