"""App configuration, loaded from backend/.env (written by setup_db.ps1)."""
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    # SQLAlchemy connection string, e.g. postgresql+psycopg://postgres:pw@localhost:5432/agrika_gis
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/agrika_gis",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-only-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # Which frontend origins may call the API (comma-separated in .env)
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
