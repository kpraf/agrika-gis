"""Admin-only user management endpoints (Module 6)."""
from functools import wraps

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import User, Role, Municipality

users_bp = Blueprint("users", __name__, url_prefix="/api")


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if get_jwt().get("role") != "administrator":
            return jsonify({"error": "Administrator access required."}), 403
        return fn(*args, **kwargs)

    return wrapper


def _role_id(role_name):
    role = db.session.query(Role).filter_by(role_name=role_name).first()
    return role.role_id if role else None


# ---- Dropdown metadata (roles + municipalities) ----
@users_bp.get("/meta")
@admin_required
def meta():
    roles = [r.role_name for r in db.session.query(Role).order_by(Role.role_id)]
    munis = [
        {"id": m.municipality_id, "name": m.municipality_name}
        for m in db.session.query(Municipality).order_by(Municipality.municipality_name)
    ]
    return jsonify({"roles": roles, "municipalities": munis})


# ---- List ----
@users_bp.get("/users")
@admin_required
def list_users():
    users = db.session.query(User).order_by(User.user_id).all()
    return jsonify([u.to_public_dict() for u in users])


# ---- Create ----
@users_bp.post("/users")
@admin_required
def create_user():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    role_name = data.get("role")

    if not username or not password or not role_name:
        return jsonify({"error": "Username, password, and role are required."}), 400
    rid = _role_id(role_name)
    if rid is None:
        return jsonify({"error": f"Unknown role '{role_name}'."}), 400

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        full_name=(data.get("full_name") or "").strip() or None,
        status=data.get("status") or "Active",
        role_id=rid,
        municipality_id=data.get("municipality_id") if role_name != "administrator" else None,
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "That username is already taken."}), 409
    return jsonify(user.to_public_dict()), 201


# ---- Update ----
@users_bp.put("/users/<int:user_id>")
@admin_required
def update_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "User not found."}), 404

    data = request.get_json(silent=True) or {}
    if "full_name" in data:
        user.full_name = (data.get("full_name") or "").strip() or None
    if "status" in data and data["status"]:
        user.status = data["status"]
    if data.get("role"):
        rid = _role_id(data["role"])
        if rid is None:
            return jsonify({"error": f"Unknown role '{data['role']}'."}), 400
        user.role_id = rid
    # Administrators are province-wide (no municipality); others take the given one.
    if "municipality_id" in data or data.get("role"):
        role_name = data.get("role") or (user.role.role_name if user.role else None)
        user.municipality_id = None if role_name == "administrator" else data.get("municipality_id", user.municipality_id)
    if data.get("password"):
        user.password_hash = generate_password_hash(data["password"])

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "That username is already taken."}), 409
    return jsonify(user.to_public_dict())


# ---- Delete ----
@users_bp.delete("/users/<int:user_id>")
@admin_required
def delete_user(user_id):
    if str(user_id) == str(get_jwt_identity()):
        return jsonify({"error": "You can't delete your own account."}), 400
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "User not found."}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"ok": True})
