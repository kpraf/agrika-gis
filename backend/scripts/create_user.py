"""
Create (or update) a portal user account.

Run from the backend/ folder with the virtualenv active:
    python scripts/create_user.py

It prompts for username, password, role, and (for non-admins) municipality,
hashes the password with the same library the login endpoint verifies against,
and upserts the user into the database.
"""
import sys
import os
from getpass import getpass

# Make backend/ importable when run as scripts/create_user.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from werkzeug.security import generate_password_hash  # noqa: E402

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402
from models import User, Role, Municipality  # noqa: E402

ROLES = ["administrator", "agriculturist", "rice_technician"]


def prompt_choice(label, options):
    print(f"\n{label}:")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input("Choose a number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("  Invalid choice, try again.")


def main():
    app = create_app()
    with app.app_context():
        print("=== Create / update a portal user ===")
        username = input("Username: ").strip()
        if not username:
            print("Username can't be empty.")
            return

        password = getpass("Password: ")
        if len(password) < 6:
            print("Password should be at least 6 characters.")
            return
        confirm = getpass("Confirm password: ")
        if password != confirm:
            print("Passwords don't match.")
            return

        role_name = prompt_choice("Role", ROLES)

        role = db.session.query(Role).filter_by(role_name=role_name).first()
        if role is None:
            print(f"Role '{role_name}' not found — did the seed data load? Run setup_db.ps1 first.")
            return

        municipality = None
        if role_name != "administrator":
            municipalities = db.session.query(Municipality).order_by(Municipality.municipality_name).all()
            if not municipalities:
                print("No municipalities found — run setup_db.ps1 to load seed data first.")
                return
            names = [m.municipality_name for m in municipalities]
            chosen = prompt_choice("Municipality (this user's assigned city)", names)
            municipality = next(m for m in municipalities if m.municipality_name == chosen)

        user = db.session.query(User).filter_by(username=username).first()
        if user is None:
            user = User(username=username)
            db.session.add(user)
            action = "Created"
        else:
            action = "Updated"

        user.password_hash = generate_password_hash(password)
        user.role_id = role.role_id
        user.municipality_id = municipality.municipality_id if municipality else None

        db.session.commit()

        muni = municipality.municipality_name if municipality else "— (province-wide)"
        print(f"\n{action} user '{username}'  |  role: {role_name}  |  municipality: {muni}")


if __name__ == "__main__":
    main()
