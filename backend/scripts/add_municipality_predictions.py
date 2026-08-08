"""One-off: add the municipality_predictions table to an existing database.

Safe to run against a live DB - it only CREATEs (IF NOT EXISTS) and never drops
anything. For a fresh setup, db/schema.sql already includes this table.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

DDL = [
    """
    CREATE TABLE IF NOT EXISTS municipality_predictions (
        muni_pred_id    SERIAL PRIMARY KEY,
        predicted_yield DOUBLE PRECISION NOT NULL,
        municipality_id INTEGER NOT NULL REFERENCES municipalities(municipality_id),
        season_id       INTEGER NOT NULL REFERENCES seasons(season_id),
        model_version   VARCHAR(50) NOT NULL DEFAULT 'cnn-lstm',
        generated_at    TIMESTAMP NOT NULL DEFAULT now(),
        UNIQUE (municipality_id, season_id, model_version)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_muni_pred_muni   ON municipality_predictions(municipality_id)",
    "CREATE INDEX IF NOT EXISTS idx_muni_pred_season ON municipality_predictions(season_id)",
]


def main():
    app = create_app()
    with app.app_context():
        for stmt in DDL:
            db.session.execute(text(stmt))
        db.session.commit()
        n = db.session.execute(text("SELECT COUNT(*) FROM municipality_predictions")).scalar()
        print(f"municipality_predictions ready ({n} rows currently).")


if __name__ == "__main__":
    main()
