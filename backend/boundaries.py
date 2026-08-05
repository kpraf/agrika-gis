"""
Public boundary endpoints — serve PostGIS geometries as GeoJSON for the map.

No auth required: the public yield map needs these too.
"""
import json

from flask import Blueprint, jsonify, request
from sqlalchemy import text

from extensions import db

boundaries_bp = Blueprint("boundaries", __name__, url_prefix="/api/boundaries")

# Coordinate precision (decimal places) for the served GeoJSON. 6 dp ~= 0.1 m,
# plenty for web maps and much smaller than the default 15 dp.
PRECISION = 6


@boundaries_bp.get("/municipalities")
def municipalities():
    rows = db.session.execute(
        text(
            "SELECT municipality_id, municipality_name, "
            "ST_AsGeoJSON(boundary_geometry, :p) AS geom "
            "FROM municipalities WHERE boundary_geometry IS NOT NULL "
            "ORDER BY municipality_name"
        ),
        {"p": PRECISION},
    ).all()
    features = [
        {
            "type": "Feature",
            "properties": {"municipality_id": r.municipality_id, "name": r.municipality_name},
            "geometry": json.loads(r.geom),
        }
        for r in rows
    ]
    return jsonify({"type": "FeatureCollection", "features": features})


@boundaries_bp.get("/barangays")
def barangays():
    """All barangays, or just one municipality's via ?municipality_id=N."""
    mid = request.args.get("municipality_id", type=int)
    sql = (
        "SELECT barangay_id, barangay_name, municipality_id, "
        "ST_AsGeoJSON(boundary_geometry, :p) AS geom "
        "FROM barangays WHERE boundary_geometry IS NOT NULL"
    )
    params = {"p": PRECISION}
    if mid:
        sql += " AND municipality_id = :mid"
        params["mid"] = mid
    rows = db.session.execute(text(sql), params).all()
    features = [
        {
            "type": "Feature",
            "properties": {
                "barangay_id": r.barangay_id,
                "name": r.barangay_name,
                "municipality_id": r.municipality_id,
            },
            "geometry": json.loads(r.geom),
        }
        for r in rows
    ]
    return jsonify({"type": "FeatureCollection", "features": features})
