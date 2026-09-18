"""
push_to_supabase.py
===================

One command to load the final model's predictions (and optionally the monthly
feature tables) into the PRODUCTION database that the Render app reads.

Why this exists: everything else this project does writes to your LOCAL database.
The Render app talks to a separate Supabase Postgres, so predictions must be
pushed there explicitly for the deployed app to show them.

Setup (once):
    cp backend/.env.prod.example backend/.env.prod
    # edit backend/.env.prod and paste your Supabase URL into PROD_DATABASE_URL

Run:
    python backend/scripts/push_to_supabase.py                 # predictions only
    python backend/scripts/push_to_supabase.py --with-features # + weather/satellite tables
    python backend/scripts/push_to_supabase.py --yes           # skip the confirm prompt

Safety: this writes to PRODUCTION but only UPSERTS (no deletes). It prints the
target host and asks you to confirm unless --yes is given. The URL is read from
the gitignored .env.prod - never pass it on the command line.
"""
import argparse
import os
import subprocess
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, ".."))
PRED_CSV = os.path.join(BACKEND, "db", "cnn_lstm_predictions_for_app.csv")
MODEL_VERSION = "cnn-lstm-s2s1"

# Real per-barangay yield CSVs (one per municipality collected so far).
BARANGAY_CSVS = [
    ("db/barangay_yield_city-of-santa-rosa.csv", "Santa Rosa CAO (Planting & Harvesting report)"),
    ("db/barangay_yield_city-of-cabuyao.csv", "Cabuyao CAO (Harvesting Accomplishment Report)"),
    ("db/barangay_yield_city-of-binan.csv", "Biñan CAO (Harvesting Accomplishment Report)"),
]


def load_prod_url():
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(BACKEND, ".env.prod"))
    except ImportError:
        pass
    url = os.environ.get("PROD_DATABASE_URL", "").strip().strip('"').strip("'")
    if not url:
        sys.exit("ERROR: PROD_DATABASE_URL is not set. Copy backend/.env.prod.example "
                 "to backend/.env.prod and paste your Supabase URL. Nothing was done.")
    return url


def host_of(url):
    u = url.replace("postgresql+psycopg://", "postgresql://")
    return urllib.parse.urlparse(u).hostname or "?"


def run(script, argv, env):
    print(f"\n$ {script} {' '.join(argv)}", flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *argv], cwd=BACKEND, env=env)
    if r.returncode != 0:
        sys.exit(f"ERROR: {script} failed (exit {r.returncode}). Stopping.")


def main():
    ap = argparse.ArgumentParser(description="Push predictions/features to the production (Supabase) DB.")
    ap.add_argument("--with-features", action="store_true",
                    help="Also create + load weather_monthly / satellite_monthly.")
    ap.add_argument("--with-barangays", action="store_true",
                    help="Also create barangay_yield + load the real per-barangay CSVs.")
    ap.add_argument("--skip-predictions", action="store_true",
                    help="Don't touch municipality_predictions (e.g. a barangay-only push).")
    ap.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")
    args = ap.parse_args()

    do_predictions = not args.skip_predictions
    if do_predictions and not os.path.exists(PRED_CSV):
        sys.exit(f"ERROR: {PRED_CSV} not found. Run export_cnn_lstm_predictions.py first.")
    if args.with_barangays:
        for rel, _ in BARANGAY_CSVS:
            if not os.path.exists(os.path.join(BACKEND, rel)):
                sys.exit(f"ERROR: {rel} not found. Nothing was done.")
    if not do_predictions and not args.with_features and not args.with_barangays:
        sys.exit("Nothing to do: --skip-predictions with no --with-features/--with-barangays.")

    prod = load_prod_url()
    print("=" * 60)
    print(f"TARGET: PRODUCTION database @ {host_of(prod)}")
    if do_predictions:
        print(f"  - UPSERT predictions into municipality_predictions (model_version={MODEL_VERSION})")
    if args.with_features:
        print("  - CREATE (if needed) + load weather_monthly / satellite_monthly")
    if args.with_barangays:
        print("  - CREATE (if needed) barangay_yield + UPSERT " +
              ", ".join(os.path.basename(c) for c, _ in BARANGAY_CSVS))
    print("  (no rows are deleted)")
    print("=" * 60)
    if not args.yes:
        if input("Proceed against PRODUCTION? type 'yes' to continue: ").strip().lower() != "yes":
            sys.exit("Aborted. Nothing was written.")

    # DATABASE_URL in the child env points the app at production; config.py's
    # load_dotenv() won't override an already-set env var.
    env = dict(os.environ, DATABASE_URL=prod)

    if args.with_features:
        run("add_feature_tables.py", [], env)
        run("load_feature_tables.py", [], env)
    if args.with_barangays:
        run("add_barangay_yield_table.py", [], env)
        for rel, src in BARANGAY_CSVS:
            run("load_barangay_yield.py", ["--csv", rel, "--source", src], env)
    if do_predictions:
        # Ensure the predictions table exists, then load.
        run("add_municipality_predictions.py", [], env)
        run("load_municipality_predictions.py", ["--csv", PRED_CSV, "--model-version", MODEL_VERSION], env)

    print("\nDone. The Render app should now reflect the pushed data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
