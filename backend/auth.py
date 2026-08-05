"""Authentication endpoints: login, current-user, logout."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from werkzeug.security import check_password_hash

from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    user = db.session.query(User).filter_by(username=username).first()
    if user is None or not check_password_hash(user.password_hash, password):
        # Same message either way — don't reveal which part was wrong.
        return jsonify({"error": "Invalid username or password."}), 401

    # Identity is the user id (as a string); role/municipality travel as claims.
    token = create_access_token(
        identity=str(user.user_id),
        additional_claims={
            "role": user.role.role_name if user.role else None,
            "municipality": user.municipality.municipality_name if user.municipality else None,
        },
    )
    return jsonify({"token": token, "user": user.to_public_dict()})


@auth_bp.get("/me")
@jwt_required()
def me():
    """Return the current user — used by the frontend to restore a session on refresh."""
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if user is None:
        return jsonify({"error": "User no longer exists."}), 401
    return jsonify({"user": user.to_public_dict()})


@auth_bp.post("/logout")
@jwt_required()
def logout():
    # Stateless JWT: the client just drops the token. Endpoint exists for symmetry.
    return jsonify({"ok": True})
