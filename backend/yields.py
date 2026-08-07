"""
Public yield endpoints — serve observed municipality yields for the map.

Backed by municipality_yield_records (real PRiSM/Ricelytics data, mt/ha),
joined to seasons (season_type + year) and municipalities. No auth required:
the public yield map consumes these.
"""
from flask import Blueprint, jsonify, request
from sqlalchemy import text

from extensions import db

yields_bp = Blueprint("yields", __name__, url_prefix="/api/yield")


@yields_bp.get("/meta")
def meta():
    """Distinct years and seasons that actually have data (drives the filters)."""
    years = [
        r.year
        for r in db.session.execute(
            text(
                "SELECT DISTINCT s.year FROM municipality_yield_records r "
                "JOIN seasons s ON s.season_id = r.season_id ORDER BY s.year"
            )
        )
    ]
    seasons = [
        r.season_type
        for r in db.session.execute(
            text(
                "SELECT DISTINCT s.season_type FROM municipality_yield_records r "
                "JOIN seasons s ON s.season_id = r.season_id ORDER BY s.season_type"
            )
        )
    ]
    return jsonify({"years": years, "seasons": seasons})


@yields_bp.get("/municipalities")
def municipalities():
    """Observed yield per municipality for a given year + season.

    Query params:
        year   (int)  required — e.g. 2024
        season (str)  required — 'Dry' or 'Wet'

    Returns records keyed for easy map lookup, plus summary stats for the
    heatmap colour scale and the "average yield" panel.
    """
    year = request.args.get("year", type=int)
    season = request.args.get("season", type=str)
    if not year or not season:
        return jsonify({"error": "year and season are required"}), 400

    rows = db.session.execute(
        text(
            "SELECT m.municipality_id, m.municipality_name, "
            "r.observed_yield, r.is_proxy, r.source "
            "FROM municipality_yield_records r "
            "JOIN municipalities m ON m.municipality_id = r.municipality_id "
            "JOIN seasons s ON s.season_id = r.season_id "
            "WHERE s.year = :y AND s.season_type = :sea "
            "ORDER BY m.municipality_name"
        ),
        {"y": year, "sea": season},
    ).all()

    records = [
        {
            "municipality_id": r.municipality_id,
            "name": r.municipality_name,
            "yield": round(r.observed_yield, 3),
            "is_proxy": r.is_proxy,
            "source": r.source,
        }
        for r in rows
    ]

    values = [rec["yield"] for rec in records]
    stats = {
        "count": len(values),
        "min": round(min(values), 3) if values else None,
        "max": round(max(values), 3) if values else None,
        "avg": round(sum(values) / len(values), 3) if values else None,
    }

    return jsonify({"year": year, "season": season, "stats": stats, "records": records})
