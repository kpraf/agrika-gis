"""One-off: add the barangay_yield table to an existing database.

Safe to run against a live DB - only CREATEs (IF NOT EXISTS), never drops. For a
fresh setup, db/schema.sql already includes this table.

Real barangay-level observed yield (mt/ha), one row per (barangay, season).
Loaded by load_barangay_yield.py from the extractor's CSV.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

DDL = [
    """
    CREATE TABLE IF NOT EXISTS barangay_yield (
        brgy_yield_id  SERIAL PRIMARY KEY,
        barangay_id    INTEGER NOT NULL REFERENCES barangays(barangay_id),
        season_id      INTEGER NOT NULL REFERENCES seasons(season_id),
        yield_mt_ha    DOUBLE PRECISION,
        area_ha        DOUBLE PRECISION,
        production_mt  DOUBLE PRECISION,
        source         VARCHAR(120),
        UNIQUE (barangay_id, season_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_barangay_yield_brgy   ON barangay_yield(barangay_id)",
    "CREATE INDEX IF NOT EXISTS idx_barangay_yield_season ON barangay_yield(season_id)",
]


def main():
    app = create_app()
    with app.app_context():
        for stmt in DDL:
            db.session.execute(text(stmt))
        db.session.commit()
        n = db.session.execute(text("SELECT COUNT(*) FROM barangay_yield")).scalar()
        print(f"barangay_yield ready ({n} rows currently).")


if __name__ == "__main__":
    main()
