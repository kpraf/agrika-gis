"""
load_all_data.py
================

One command to load ALL AgriKA-GIS data into your LOCAL database.

Run this after the database + boundaries exist (i.e. after
`backend/db/setup_db.ps1` and `scripts/import_boundaries.py`). It runs every
loader in the right order:

  * municipality yields, CNN-LSTM predictions and monthly features
  * barangay yields for the four study cities (Santa Rosa, Cabuyao, Biñan, Calamba)
  * barangay Environment features (weather + satellite) for those cities
  * barangay CNN-LSTM predictions

Everything is an idempotent UPSERT, so it is safe to re-run — after a `git pull`
that brings new/updated CSVs, just run this again to refresh your local data.

    cd backend
    .\\venv\\Scripts\\python.exe scripts\\load_all_data.py

It writes to whatever DATABASE_URL your backend/.env points at (your local DB).
To push to production instead, use scripts/push_to_supabase.py.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, ".."))

# Municipality prediction tag — matches what production (push_to_supabase.py) uses.
MUNI_MODEL_VERSION = "cnn-lstm-s2s1"

# Each step: (script, argv). Order matters (create tables before loading them).
STEPS = [
    # --- municipality level ---
    ("load_municipality_yield.py", ["--csv", "db/ricelytics_laguna_yield.csv"]),
    ("add_municipality_predictions.py", []),
    ("load_municipality_predictions.py",
     ["--csv", "db/cnn_lstm_predictions_for_app.csv", "--model-version", MUNI_MODEL_VERSION]),
    ("add_feature_tables.py", []),
    ("load_feature_tables.py", []),
    # --- barangay yields (four study cities) ---
    ("add_barangay_yield_table.py", []),
    ("load_barangay_yield.py",
     ["--csv", "db/barangay_yield_city-of-santa-rosa.csv",
      "--source", "Santa Rosa CAO (Planting & Harvesting report)"]),
    ("load_barangay_yield.py",
     ["--csv", "db/barangay_yield_city-of-cabuyao.csv",
      "--source", "Cabuyao CAO (Harvesting Accomplishment Report)"]),
    ("load_barangay_yield.py",
     ["--csv", "db/barangay_yield_city-of-binan.csv",
      "--source", "Biñan CAO (Harvesting Accomplishment Report)"]),
    ("load_barangay_yield.py",
     ["--csv", "db/barangay_yield_city-of-calamba.csv",
      "--source", "Calamba CAO (Harvesting Accomplishment Report)"]),
    # --- barangay Environment features ---
    ("add_barangay_feature_tables.py", []),
    ("load_barangay_feature_tables.py",
     ["--weather", "db/weather_barangay_sr_cabuyao_monthly.csv",
      "--satellite", "db/satellite_barangay_sr_cabuyao_monthly.csv",
      "--municipalities", "City of Santa Rosa,City of Cabuyao"]),
    ("load_barangay_feature_tables.py",
     ["--weather", "db/weather_barangay_binan_monthly.csv",
      "--satellite", "db/satellite_barangay_binan_monthly.csv",
      "--municipalities", "City of Biñan"]),
    ("load_barangay_feature_tables.py",
     ["--weather", "db/weather_barangay_calamba_monthly.csv",
      "--satellite", "db/satellite_barangay_calamba_monthly.csv",
      "--municipalities", "City of Calamba"]),
    # --- barangay predictions ---
    ("load_barangay_predictions.py", ["--csv", "db/barangay_cnn_lstm_predictions.csv"]),
    ("load_barangay_predictions.py", ["--csv", "db/barangay_cnn_lstm_predictions_calamba.csv"]),
]


def main():
    # Preflight: every script exists.
    missing = [s for s, _ in STEPS if not os.path.exists(os.path.join(HERE, s))]
    if missing:
        sys.exit(f"ERROR: missing loader scripts: {', '.join(missing)}")

    for i, (script, argv) in enumerate(STEPS, 1):
        print(f"\n[{i}/{len(STEPS)}] $ {script} {' '.join(argv)}", flush=True)
        r = subprocess.run([sys.executable, os.path.join(HERE, script), *argv], cwd=BACKEND)
        if r.returncode != 0:
            sys.exit(f"ERROR: {script} failed (exit {r.returncode}). Stopping.")

    print("\nAll data loaded into your local database. "
          "Start the API with:  .\\venv\\Scripts\\python.exe app.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
