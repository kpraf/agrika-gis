"""One-off: add the weather_monthly and satellite_monthly tables.

Objective 3 (centralized spatial database): the acquired + preprocessed weather
and satellite features are stored in PostGIS alongside boundaries, yield, and
predictions - instead of living only in CSVs.

Safe to run against a live DB - only CREATEs (IF NOT EXISTS), never drops. For a
fresh setup, db/schema.sql already includes these tables.

Grain: one row per (municipality, year, month). Loaded by load_feature_tables.py.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

DDL = [
    """
    CREATE TABLE IF NOT EXISTS weather_monthly (
        weather_id        SERIAL PRIMARY KEY,
        municipality_id   INTEGER NOT NULL REFERENCES municipalities(municipality_id),
        year              INTEGER NOT NULL,
        month             INTEGER NOT NULL,
        rainfall_mm       DOUBLE PRECISION,
        temp_mean_c       DOUBLE PRECISION,
        humidity_mean_pct DOUBLE PRECISION,
        days              INTEGER,
        UNIQUE (municipality_id, year, month)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS satellite_monthly (
        satellite_id    SERIAL PRIMARY KEY,
        municipality_id INTEGER NOT NULL REFERENCES municipalities(municipality_id),
        year            INTEGER NOT NULL,
        month           INTEGER NOT NULL,
        ndvi_mean       DOUBLE PRECISION,
        ndvi_std        DOUBLE PRECISION,
        evi_mean        DOUBLE PRECISION,
        evi_std         DOUBLE PRECISION,
        ndwi_mean       DOUBLE PRECISION,
        ndwi_std        DOUBLE PRECISION,
        s2_valid_px     INTEGER,
        vv_mean         DOUBLE PRECISION,
        vv_std          DOUBLE PRECISION,
        vh_mean         DOUBLE PRECISION,
        vh_std          DOUBLE PRECISION,
        s1_valid_px     INTEGER,
        UNIQUE (municipality_id, year, month)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_weather_monthly_muni   ON weather_monthly(municipality_id)",
    "CREATE INDEX IF NOT EXISTS idx_satellite_monthly_muni ON satellite_monthly(municipality_id)",
]


def main():
    app = create_app()
    with app.app_context():
        for stmt in DDL:
            db.session.execute(text(stmt))
        db.session.commit()
        for tbl in ("weather_monthly", "satellite_monthly"):
            n = db.session.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            print(f"{tbl} ready ({n} rows currently).")


if __name__ == "__main__":
    main()
