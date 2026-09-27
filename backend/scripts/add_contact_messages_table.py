"""One-off: add the contact_messages table to an existing database.

Safe to run against a live DB (CREATE IF NOT EXISTS, never drops). For a fresh
setup, db/schema.sql already includes this table.

    # local DB (backend/.env)
    .\\venv\\Scripts\\python.exe scripts\\add_contact_messages_table.py

    # production (Supabase) — reads PROD_DATABASE_URL from backend/.env.prod
    .\\venv\\Scripts\\python.exe scripts\\add_contact_messages_table.py --prod
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DDL = """
CREATE TABLE IF NOT EXISTS contact_messages (
    message_id   SERIAL PRIMARY KEY,
    full_name    VARCHAR(150) NOT NULL,
    organization VARCHAR(150),
    phone        VARCHAR(50)  NOT NULL,
    subject      VARCHAR(150) NOT NULL,
    message      TEXT         NOT NULL,
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
)
"""


def main():
    ap = argparse.ArgumentParser(description="Create the contact_messages table.")
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

    app = create_app()
    with app.app_context():
        db.session.execute(text(DDL))
        db.session.commit()
        n = db.session.execute(text("SELECT COUNT(*) FROM contact_messages")).scalar()
        print(f"contact_messages ready ({n} rows currently).")


if __name__ == "__main__":
    main()
