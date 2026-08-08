"""App configuration, loaded from backend/.env (written by setup_db.ps1)."""
import os
import sys
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def _redacted(url: str) -> str:
    """A log-safe view of a DB URL — never reveals the password."""
    if "://" not in url:
        return f"<no scheme; len={len(url)}; starts={url[:10]!r}>"
    head, tail = url.split("://", 1)
    if "@" in tail:
        creds, host = tail.split("@", 1)
        user = creds.split(":", 1)[0]
        return f"{head}://{user}:***@{host}"
    return f"{head}://{tail}"


def _normalize_db_url(url: str) -> str:
    """Force the psycopg (v3) driver and clean common paste mistakes.

    Managed providers (Render, Supabase, Heroku) hand out URLs like
    'postgres://...' or 'postgresql://...'. SQLAlchemy + psycopg3 needs the
    explicit 'postgresql+psycopg://' scheme. We also strip whitespace and any
    surrounding quotes, which are the usual reasons a dashboard-pasted value
    fails to parse.
    """
    url = url.strip().strip('"').strip("'").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]

    # Fail loudly but safely if the result still isn't a valid URL.
    try:
        from sqlalchemy.engine import make_url

        make_url(url)
    except Exception as exc:  # noqa: BLE001
        print(
            f"[config] DATABASE_URL could not be parsed ({exc}). "
            f"Redacted value: {_redacted(url)}",
            file=sys.stderr,
        )
    return url


class Config:
    # SQLAlchemy connection string, e.g. postgresql+psycopg://postgres:pw@localhost:5432/agrika_gis
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(
        os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/agrika_gis",
        )
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-only-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # Which frontend origins may call the API (comma-separated in .env)
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
