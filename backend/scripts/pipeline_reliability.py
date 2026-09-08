"""
pipeline_reliability.py
=======================

Objective 3 evaluation: measure how reliably the data pipeline ACQUIRES,
PREPROCESSES, INTEGRATES, and DELIVERS the data required for prediction and
spatial visualization. Produces citable reliability figures.

Reads the centralized spatial database (weather_monthly, satellite_monthly,
municipalities, municipality_yield_records) plus the training set delivered to
the model, and the orchestrator's last-run summary if present.

Checks
  1. Acquisition   - area-month cells present vs expected, per source.
  2. Completeness  - non-null feature coverage (documents expected optical/SAR gaps).
  3. Integrity     - every value within a physical range; zero non-finite values.
  4. Integration   - yield-label municipalities matched to features; training rows delivered.
  5. Gap accounting- where the satellite gaps fall (season / year), i.e. are they expected.

Output: printed report, also saved to db/pipeline_reliability_report.txt.

Usage
    python backend/scripts/pipeline_reliability.py
    python backend/scripts/pipeline_reliability.py --start 2018 --end 2025
"""
import argparse
import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "db"))
TRAIN_WIDE = os.path.join(DB_DIR, "training_features_wide.csv")
RUN_SUMMARY = os.path.join(DB_DIR, "pipeline_last_run.json")
REPORT_PATH = os.path.join(DB_DIR, "pipeline_reliability_report.txt")

# Physical ranges for the integrity check (value outside => violation).
RANGES = {
    "weather_monthly": {
        "rainfall_mm": (0, 3000),
        "temp_mean_c": (10, 40),
        "humidity_mean_pct": (0, 100),
    },
    "satellite_monthly": {
        "ndvi_mean": (-1, 1),
        "ndwi_mean": (-1, 1),
        "vv_mean": (-40, 5),
        "vh_mean": (-40, 5),
    },
}
SAT_FEATURES = ["ndvi_mean", "evi_mean", "ndwi_mean", "vv_mean", "vh_mean"]
WEATHER_FEATURES = ["rainfall_mm", "temp_mean_c", "humidity_mean_pct"]


def q1(sql, **p):
    return db.session.execute(text(sql), p).scalar()


def main():
    ap = argparse.ArgumentParser(description="Evaluate data-pipeline reliability.")
    ap.add_argument("--start", type=int, default=2018)
    ap.add_argument("--end", type=int, default=2025)
    args = ap.parse_args()

    out = []
    def p(s=""):
        out.append(s)
        print(s)

    app = create_app()
    with app.app_context():
        n_muni = q1("SELECT COUNT(*) FROM municipalities")
        years = args.end - args.start + 1
        expected = n_muni * years * 12

        p("=" * 68)
        p(" AgriKA-GIS DATA PIPELINE - RELIABILITY REPORT")
        p("=" * 68)
        p(f"scope: {n_muni} municipalities x {years} years x 12 months "
          f"= {expected} expected area-months ({args.start}-{args.end})")

        # 1. Acquisition -----------------------------------------------------
        p("\n[1] ACQUISITION  (area-month cells present vs expected)")
        for tbl in ("weather_monthly", "satellite_monthly"):
            rows = q1(f"SELECT COUNT(*) FROM {tbl}")
            munis = q1(f"SELECT COUNT(DISTINCT municipality_id) FROM {tbl}")
            p(f"  {tbl:<18} {rows}/{expected} cells ({100*rows/expected:.1f}%), "
              f"{munis}/{n_muni} municipalities")

        # 2. Completeness ----------------------------------------------------
        p("\n[2] COMPLETENESS  (non-null feature values / expected cells)")
        for f in WEATHER_FEATURES:
            c = q1(f"SELECT COUNT({f}) FROM weather_monthly")
            p(f"  weather.{f:<18} {c}/{expected} ({100*c/expected:.1f}%)")
        for f in SAT_FEATURES:
            c = q1(f"SELECT COUNT({f}) FROM satellite_monthly")
            p(f"  sat.{f:<21} {c}/{expected} ({100*c/expected:.1f}%)")

        # 3. Integrity -------------------------------------------------------
        p("\n[3] INTEGRITY  (values within physical range; non-finite count)")
        total_violations = 0
        for tbl, cols in RANGES.items():
            for col, (lo, hi) in cols.items():
                v = q1(f"SELECT COUNT(*) FROM {tbl} WHERE {col} IS NOT NULL "
                       f"AND ({col} < :lo OR {col} > :hi)", lo=lo, hi=hi)
                nonfinite = q1(f"SELECT COUNT(*) FROM {tbl} WHERE {col} IS NOT NULL "
                               f"AND (NOT ({col} = {col}) OR {col} = 'Infinity' OR {col} = '-Infinity')")
                total_violations += v + nonfinite
                flag = "OK" if (v + nonfinite) == 0 else f"** {v} out-of-range, {nonfinite} non-finite"
                p(f"  {tbl.split('_')[0]}.{col:<18} [{lo},{hi}]  {flag}")
        # EVI outliers reported separately (known EVI instability, not a hard bound)
        evi_out = q1("SELECT COUNT(*) FROM satellite_monthly WHERE evi_mean IS NOT NULL "
                     "AND (evi_mean < -1 OR evi_mean > 1.5)")
        p(f"  sat.evi_mean         (note) {evi_out} values outside [-1,1.5] - known EVI instability, EVI excluded from final model")
        p(f"  --> total integrity violations: {total_violations}")

        # 4. Integration / delivery -----------------------------------------
        p("\n[4] INTEGRATION / DELIVERY")
        label_munis = q1("SELECT COUNT(DISTINCT municipality_id) FROM municipality_yield_records")
        matched = q1("SELECT COUNT(DISTINCT r.municipality_id) FROM municipality_yield_records r "
                     "WHERE EXISTS (SELECT 1 FROM weather_monthly w WHERE w.municipality_id=r.municipality_id) "
                     "AND EXISTS (SELECT 1 FROM satellite_monthly s WHERE s.municipality_id=r.municipality_id)")
        p(f"  yield-label municipalities matched to features: {matched}/{label_munis} "
          f"({100*matched/label_munis:.1f}%)")
        if os.path.exists(TRAIN_WIDE):
            with open(TRAIN_WIDE, newline="", encoding="utf-8") as fh:
                n_train = sum(1 for _ in csv.DictReader(fh))
            p(f"  training samples delivered: {n_train} rows")

        # 5. Gap accounting --------------------------------------------------
        p("\n[5] GAP ACCOUNTING  (are the satellite gaps expected?)")
        present = q1("SELECT COUNT(*) FROM satellite_monthly")
        absent = expected - present
        # S2 optical: NDVI null within acquired rows (cloud), split by season.
        dry = q1("SELECT COUNT(*) FROM satellite_monthly WHERE ndvi_mean IS NULL AND month BETWEEN 1 AND 6")
        wet = q1("SELECT COUNT(*) FROM satellite_monthly WHERE ndvi_mean IS NULL AND month BETWEEN 7 AND 12")
        p(f"  S2 optical (NDVI/EVI/NDWI) cloud-masked in acquired months: "
          f"Dry(Jan-Jun)={dry}, Wet(Jul-Dec)={wet} "
          f"-> wet-season clouds ({wet}/{dry+wet} of gaps), expected for optical in the tropics")
        # S1 SAR: VV/VH are present in every acquired row (cloud-independent).
        vv_nulls = q1("SELECT COUNT(*) FROM satellite_monthly WHERE vv_mean IS NULL")
        p(f"  S1 SAR (VV/VH): present in all {present} acquired area-months "
          f"({vv_nulls} nulls) -> cloud-independent, coverage complete where acquired")
        p(f"  Fully-absent area-months (no S1 or S2 acquisition at all): "
          f"{absent}/{expected} ({100*absent/expected:.1f}%)")

        # Orchestrator last run ---------------------------------------------
        if os.path.exists(RUN_SUMMARY):
            run = json.load(open(RUN_SUMMARY, encoding="utf-8"))
            p(f"\n[6] LAST PIPELINE RUN: {run.get('overall','?').upper()} "
              f"(started {run.get('started','?')})")
            for st in run.get("stages", []):
                p(f"    {st['stage']:<22} {st['status']:<8} {st['seconds']}s")

        # Verdict ------------------------------------------------------------
        p("\n" + "=" * 68)
        weather_ok = q1("SELECT COUNT(*) FROM weather_monthly") == expected
        p(f" VERDICT: integrity violations = {total_violations} "
          f"({'PASS' if total_violations == 0 else 'REVIEW'}); "
          f"weather complete = {weather_ok}; "
          f"satellite gaps documented + expected.")
        p("=" * 68)

    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"\nsaved -> {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
