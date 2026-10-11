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


_LOCAL_DB_HOSTS = {"localhost", "127.0.0.1", "::1", ""}


def _engine_options(url: str) -> dict:
    """Require an encrypted connection to any database that is not on this machine.

    psycopg's default (sslmode=prefer) falls back to plain text if the server
    will not do TLS; "require" refuses to connect instead. A local database is
    left alone (a default local Postgres has no TLS), and so is a URL that
    already states its own sslmode.
    """
    try:
        from sqlalchemy.engine import make_url

        parsed = make_url(url)
    except Exception:  # noqa: BLE001 - already reported by _normalize_db_url
        return {}
    if (parsed.host or "") in _LOCAL_DB_HOSTS or "sslmode" in parsed.query:
        return {}
    return {"connect_args": {"sslmode": "require"}}


def _jwt_secret() -> str:
    """The token-signing secret. There is deliberately no default.

    A built-in fallback would be public (this repository is), and anyone who
    knows the secret can sign themselves a token for any account - so without
    one the app refuses to start.
    """
    secret = os.environ.get("JWT_SECRET_KEY", "").strip()
    # The two placeholders this repository has ever shipped count as "not set".
    if not secret or secret in ("dev-only-change-me", "change-this-to-a-long-random-string"):
        raise RuntimeError(
            "JWT_SECRET_KEY is not set. Put a long random value in backend/.env "
            "(setup_db.ps1 writes one; Render generates one) - the app will not "
            "start without it."
        )
    return secret


class Config:
    # SQLAlchemy connection string, e.g. postgresql+psycopg://postgres:pw@localhost:5432/agrika_gis
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(
        os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/agrika_gis",
        )
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options(SQLALCHEMY_DATABASE_URI)

    # JWT
    JWT_SECRET_KEY = _jwt_secret()
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # Which frontend origins may call the API (comma-separated in .env)
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

    # Contact form: stored in the DB always; an email notification is also sent
    # via Resend (https://resend.com) when RESEND_API_KEY is set. Without the key
    # the message is still saved, just no email goes out.
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
    CONTACT_FROM_EMAIL = os.environ.get("CONTACT_FROM_EMAIL", "onboarding@resend.dev").strip()
    CONTACT_TO_EMAIL = os.environ.get("CONTACT_TO_EMAIL", "agrikagis.official@gmail.com").strip()
