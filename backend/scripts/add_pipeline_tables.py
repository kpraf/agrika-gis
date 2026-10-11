"""One-off: add the audit tables (yield_import_log, pipeline_runs).

Safe to run against a live DB - only CREATEs (IF NOT EXISTS), never drops. For a
fresh setup, db/schema.sql already includes these tables. The pipeline and the
import endpoint also create them on first use, so running this by hand is
optional; it exists so the tables can be put in place ahead of time.

    # local DB (backend/.env)
    .\\venv\\Scripts\\python.exe scripts\\add_pipeline_tables.py

    # production (Supabase) - reads PROD_DATABASE_URL from backend/.env.prod
    .\\venv\\Scripts\\python.exe scripts\\add_pipeline_tables.py --prod
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main():
    ap = argparse.ArgumentParser(description="Create the audit tables.")
    ap.add_argument("--prod", action="store_true", help="Act on the production (Supabase) DB.")
    args = ap.parse_args()

    if args.prod:
        try:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(BACKEND, ".env.prod"))
        except ImportError:
            pass
        url = os.environ.get("PROD_DATABASE_URL", "").strip().strip('"').strip("'")
        if not url:
            sys.exit("ERROR: PROD_DATABASE_URL not set (backend/.env.prod). Nothing was done.")
        os.environ["DATABASE_URL"] = url
        print(f"TARGET: PRODUCTION @ {url.rsplit('@', 1)[-1].split('/', 1)[0]}")

    # Imported here, not at the top: Config reads DATABASE_URL at import time,
    # so the --prod override above has to happen first.
    from app import create_app
    from extensions import db
    import audit

    app = create_app()
    with app.app_context():
        audit.ensure_import_log()
        audit.ensure_pipeline_runs()
        for tbl in ("yield_import_log", "pipeline_runs"):
            n = db.session.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            print(f"{tbl} ready ({n} rows currently).")


if __name__ == "__main__":
    main()
