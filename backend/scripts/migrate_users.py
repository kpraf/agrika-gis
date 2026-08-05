"""One-off: add full_name + status columns to an existing users table and backfill."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

NAMES = {"admin": "System Administrator", "agriculturist": "City Agriculturist", "technician": "Rice Technician"}


def main():
    app = create_app()
    with app.app_context():
        db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(150)"))
        db.session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'Active'"))
        db.session.commit()
        for username, full_name in NAMES.items():
            db.session.execute(
                text("UPDATE users SET full_name = :fn WHERE username = :u AND full_name IS NULL"),
                {"fn": full_name, "u": username},
            )
        db.session.commit()
        rows = db.session.execute(text("SELECT username, full_name, status FROM users ORDER BY user_id")).all()
        for r in rows:
            print(f"  {r.username:14} | {r.full_name} | {r.status}")
        print("migration done.")


if __name__ == "__main__":
    main()
