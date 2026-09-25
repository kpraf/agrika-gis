r"""
check_db.py - "Is the backend really talking to my local PostgreSQL?"

Save this file as  backend/scripts/check_db.py  and run it from the backend/ folder:

    .\venv\Scripts\python.exe scripts\check_db.py

It uses the SAME connection settings as the Flask app (backend/.env), so if this
works, the app can connect too. It prints where it connected (never the password),
whether PostGIS is enabled, and how many rows each table has.
"""
import os
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BACKEND)

from dotenv import dotenv_values  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

# Tables the app reads, in the order data is loaded.
TABLES = [
    "roles", "municipalities", "barangays", "seasons", "users",
    "municipality_yield_records", "municipality_predictions",
    "barangay_yield", "weather_monthly", "satellite_monthly",
]


def main() -> int:
    ok = True

    # A DATABASE_URL set in the PowerShell session wins over backend/.env.
    # If the two differ, the app is NOT using the .env file - warn about it.
    file_url = dotenv_values(os.path.join(BACKEND, ".env")).get("DATABASE_URL")
    live_url = os.environ.get("DATABASE_URL")
    if file_url and live_url and file_url.strip() != live_url.strip():
        print("WARNING: a DATABASE_URL set in this PowerShell session is overriding backend\\.env.")
        print("         Clear it with:  Remove-Item Env:DATABASE_URL\n")

    app = create_app()
    with app.app_context():
        url = db.engine.url
        print(f"Target   : host={url.host}  port={url.port}  database={url.database}  user={url.username}")
        if url.host not in ("localhost", "127.0.0.1", "::1", None):
            print("WARNING  : host is not this computer - this is NOT your local PostgreSQL.")
            ok = False

        try:
            row = db.session.execute(text("SELECT current_database(), current_user, version()")).one()
        except Exception as exc:  # noqa: BLE001
            print(f"\nCONNECTION FAILED: {type(exc).__name__}")
            print(str(exc).strip().splitlines()[0][:200])
            print("Check: is the PostgreSQL service running, and are the settings in backend\\.env right?")
            return 1
        print(f"Connected: database={row[0]}  user={row[1]}")
        print(f"Server   : {row[2].split(',')[0]}")

        try:
            ver = db.session.execute(text("SELECT postgis_version()")).scalar()
            print(f"PostGIS  : {ver}")
        except Exception:  # noqa: BLE001
            db.session.rollback()
            print("PostGIS  : NOT ENABLED in this database (run schema_geometry.sql)")
            ok = False

        print("\nTable row counts:")
        for t in TABLES:
            try:
                n = db.session.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                print(f"  {t:<28}{n:>7}")
            except Exception:  # noqa: BLE001
                db.session.rollback()
                print(f"  {t:<28}MISSING")
                ok = False

        try:
            m = db.session.execute(text("SELECT COUNT(*) FROM municipalities WHERE boundary_geometry IS NOT NULL")).scalar()
            b = db.session.execute(text("SELECT COUNT(*) FROM barangays WHERE boundary_geometry IS NOT NULL")).scalar()
            print(f"\nBoundaries with geometry: {m} municipalities, {b} barangays")
        except Exception:  # noqa: BLE001
            db.session.rollback()
            print("\nBoundaries with geometry: geometry columns missing (run schema_geometry.sql)")
            ok = False

    print("\nRESULT:", "OK" if ok else "PROBLEMS FOUND (see above)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
