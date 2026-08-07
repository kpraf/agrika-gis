"""One-off: add the municipality_yield_records table to an existing database.

Safe to run against a live DB - it only CREATEs (IF NOT EXISTS) and never drops
anything. For a fresh setup, db/schema.sql already includes this table, so you
don't need this script there.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

DDL = [
    """
    CREATE TABLE IF NOT EXISTS municipality_yield_records (
        muni_yield_id   SERIAL PRIMARY KEY,
        observed_yield  DOUBLE PRECISION NOT NULL,
        municipality_id INTEGER NOT NULL REFERENCES municipalities(municipality_id),
        season_id       INTEGER NOT NULL REFERENCES seasons(season_id),
        source          VARCHAR(50),
        is_proxy        BOOLEAN NOT NULL DEFAULT FALSE,
        UNIQUE (municipality_id, season_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_muni_yield_muni   ON municipality_yield_records(municipality_id)",
    "CREATE INDEX IF NOT EXISTS idx_muni_yield_season ON municipality_yield_records(season_id)",
]


def main():
    app = create_app()
    with app.app_context():
        for stmt in DDL:
            db.session.execute(text(stmt))
        db.session.commit()
        n = db.session.execute(text("SELECT COUNT(*) FROM municipality_yield_records")).scalar()
        print(f"municipality_yield_records ready ({n} rows currently).")


if __name__ == "__main__":
    main()
