"""
remove_2026.py
==============

Delete the stray 2026 rows that a manual CSV-import test left in
municipality_yield_records (one municipality only), which made the map default to
an empty 2026 view. Also removes the now-orphaned 2026 seasons rows.

Idempotent — safe to re-run (it just deletes 2026 if present).

    # local DB (backend/.env)
    .\\venv\\Scripts\\python.exe scripts\\remove_2026.py

    # production (Supabase) — reads PROD_DATABASE_URL from backend/.env.prod
    .\\venv\\Scripts\\python.exe scripts\\remove_2026.py --prod
    .\\venv\\Scripts\\python.exe scripts\\remove_2026.py --prod --yes   # skip the prompt
"""
import argparse
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DELETE_YIELDS = text(
    "DELETE FROM municipality_yield_records "
    "WHERE season_id IN (SELECT season_id FROM seasons WHERE year = 2026)"
)
# Only drop the 2026 seasons rows if nothing else still references them.
DELETE_SEASONS = text(
    "DELETE FROM seasons WHERE year = 2026 "
    "AND season_id NOT IN (SELECT season_id FROM municipality_yield_records) "
    "AND season_id NOT IN (SELECT season_id FROM municipality_predictions) "
    "AND season_id NOT IN (SELECT season_id FROM barangay_yield) "
    "AND season_id NOT IN (SELECT season_id FROM barangay_predictions)"
)


def prod_url():
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(BACKEND, ".env.prod"))
    except ImportError:
        pass
    url = os.environ.get("PROD_DATABASE_URL", "").strip().strip('"').strip("'")
    if not url:
        sys.exit("ERROR: PROD_DATABASE_URL is not set (backend/.env.prod). Nothing was done.")
    return url


def main():
    ap = argparse.ArgumentParser(description="Remove the stray 2026 rows.")
    ap.add_argument("--prod", action="store_true", help="Act on the production (Supabase) DB.")
    ap.add_argument("--yes", action="store_true", help="Skip the confirmation prompt (--prod).")
    args = ap.parse_args()

    if args.prod:
        url = prod_url()
        os.environ["DATABASE_URL"] = url  # create_app() reads this
        host = urllib.parse.urlparse(url.replace("postgresql+psycopg://", "postgresql://")).hostname
        print(f"TARGET: PRODUCTION @ {host}")
        if not args.yes and input("Delete 2026 rows from PRODUCTION? type 'yes': ").strip().lower() != "yes":
            sys.exit("Aborted. Nothing was deleted.")

    app = create_app()
    with app.app_context():
        n1 = db.session.execute(DELETE_YIELDS).rowcount
        n2 = db.session.execute(DELETE_SEASONS).rowcount
        db.session.commit()
        remaining = db.session.execute(text("SELECT COUNT(*) FROM seasons WHERE year = 2026")).scalar()
    print(f"deleted {n1} municipality_yield_records, {n2} orphaned 2026 seasons "
          f"({remaining} 2026 seasons remaining).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
