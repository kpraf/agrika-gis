"""One-off: add barangay-level weather_monthly_barangay / satellite_monthly_barangay.

Barangay counterpart of add_feature_tables.py, for the Environment layers on the
map's barangay drill-in (research-locale cities only). Grain: one row per
(barangay, year, month). Safe to re-run (CREATE IF NOT EXISTS).

Loaded by load_barangay_feature_tables.py from the per-city barangay feature CSVs.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

DDL = [
    """
    CREATE TABLE IF NOT EXISTS weather_monthly_barangay (
        weather_id        SERIAL PRIMARY KEY,
        barangay_id       INTEGER NOT NULL REFERENCES barangays(barangay_id),
        year              INTEGER NOT NULL,
        month             INTEGER NOT NULL,
        rainfall_mm       DOUBLE PRECISION,
        temp_mean_c       DOUBLE PRECISION,
        humidity_mean_pct DOUBLE PRECISION,
        days              INTEGER,
        UNIQUE (barangay_id, year, month)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS satellite_monthly_barangay (
        satellite_id  SERIAL PRIMARY KEY,
        barangay_id   INTEGER NOT NULL REFERENCES barangays(barangay_id),
        year          INTEGER NOT NULL,
        month         INTEGER NOT NULL,
        ndvi_mean     DOUBLE PRECISION,
        ndvi_std      DOUBLE PRECISION,
        evi_mean      DOUBLE PRECISION,
        evi_std       DOUBLE PRECISION,
        ndwi_mean     DOUBLE PRECISION,
        ndwi_std      DOUBLE PRECISION,
        s2_valid_px   INTEGER,
        vv_mean       DOUBLE PRECISION,
        vv_std        DOUBLE PRECISION,
        vh_mean       DOUBLE PRECISION,
        vh_std        DOUBLE PRECISION,
        s1_valid_px   INTEGER,
        UNIQUE (barangay_id, year, month)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_weather_monthly_brgy   ON weather_monthly_barangay(barangay_id)",
    "CREATE INDEX IF NOT EXISTS idx_satellite_monthly_brgy ON satellite_monthly_barangay(barangay_id)",
]


def main():
    app = create_app()
    with app.app_context():
        for stmt in DDL:
            db.session.execute(text(stmt))
        db.session.commit()
        for tbl in ("weather_monthly_barangay", "satellite_monthly_barangay"):
            n = db.session.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            print(f"{tbl} ready ({n} rows currently).")


if __name__ == "__main__":
    main()
