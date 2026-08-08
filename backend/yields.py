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


@yields_bp.get("/records")
def records():
    """Flat list of every observed municipality yield — for the Reports page.

    One row per municipality-year-season: { municipality, year, season, yield,
    is_proxy }. Small enough (a few hundred rows) to return in one call.
    """
    rows = db.session.execute(
        text(
            "SELECT m.municipality_name, s.year, s.season_type, "
            "r.observed_yield, r.is_proxy "
            "FROM municipality_yield_records r "
            "JOIN municipalities m ON m.municipality_id = r.municipality_id "
            "JOIN seasons s ON s.season_id = r.season_id "
            "ORDER BY s.year, s.season_type, m.municipality_name"
        )
    ).all()
    return jsonify({
        "records": [
            {
                "municipality": r.municipality_name,
                "year": r.year,
                "season": r.season_type,
                "yield": round(r.observed_yield, 3),
                "is_proxy": r.is_proxy,
            }
            for r in rows
        ]
    })


@yields_bp.get("/predictions/meta")
def predictions_meta():
    """Years / seasons / model versions that have CNN-LSTM predictions.

    has_predictions lets the UI enable the Predicted overlay only once real
    model output has been loaded.
    """
    years = [
        r.year
        for r in db.session.execute(
            text(
                "SELECT DISTINCT s.year FROM municipality_predictions p "
                "JOIN seasons s ON s.season_id = p.season_id ORDER BY s.year"
            )
        )
    ]
    seasons = [
        r.season_type
        for r in db.session.execute(
            text(
                "SELECT DISTINCT s.season_type FROM municipality_predictions p "
                "JOIN seasons s ON s.season_id = p.season_id ORDER BY s.season_type"
            )
        )
    ]
    models = [
        r.model_version
        for r in db.session.execute(
            text("SELECT DISTINCT model_version FROM municipality_predictions ORDER BY model_version")
        )
    ]
    return jsonify({
        "has_predictions": len(years) > 0,
        "years": years,
        "seasons": seasons,
        "model_versions": models,
    })


@yields_bp.get("/compare")
def compare():
    """Observed vs predicted (and residual) per municipality for a year+season.

    Query params:
        year          (int) required
        season        (str) required — 'Dry' or 'Wet'
        model_version (str) optional — defaults to the most recent run present

    Each record: { municipality_id, name, observed, predicted, residual,
    is_proxy }. residual = observed - predicted (null unless both exist).
    stats summarises observed/predicted averages and the mean absolute error
    over municipalities that have both.
    """
    year = request.args.get("year", type=int)
    season = request.args.get("season", type=str)
    model_version = request.args.get("model_version", type=str)
    if not year or not season:
        return jsonify({"error": "year and season are required"}), 400

    observed = {
        r.municipality_id: {"name": r.municipality_name, "observed": round(r.observed_yield, 3), "is_proxy": r.is_proxy}
        for r in db.session.execute(
            text(
                "SELECT m.municipality_id, m.municipality_name, r.observed_yield, r.is_proxy "
                "FROM municipality_yield_records r "
                "JOIN municipalities m ON m.municipality_id = r.municipality_id "
                "JOIN seasons s ON s.season_id = r.season_id "
                "WHERE s.year = :y AND s.season_type = :sea"
            ),
            {"y": year, "sea": season},
        )
    }

    # Latest model run per municipality unless a specific version is requested.
    pred_sql = (
        "SELECT DISTINCT ON (p.municipality_id) p.municipality_id, m.municipality_name, "
        "p.predicted_yield "
        "FROM municipality_predictions p "
        "JOIN municipalities m ON m.municipality_id = p.municipality_id "
        "JOIN seasons s ON s.season_id = p.season_id "
        "WHERE s.year = :y AND s.season_type = :sea"
    )
    params = {"y": year, "sea": season}
    if model_version:
        pred_sql += " AND p.model_version = :mv"
        params["mv"] = model_version
    pred_sql += " ORDER BY p.municipality_id, p.generated_at DESC"
    predicted = {
        r.municipality_id: {"name": r.municipality_name, "predicted": round(r.predicted_yield, 3)}
        for r in db.session.execute(text(pred_sql), params)
    }

    records = []
    for mid in sorted(set(observed) | set(predicted), key=lambda i: (observed.get(i) or predicted.get(i))["name"]):
        obs = observed.get(mid, {})
        prd = predicted.get(mid, {})
        o = obs.get("observed")
        p = prd.get("predicted")
        residual = round(o - p, 3) if (o is not None and p is not None) else None
        records.append({
            "municipality_id": mid,
            "name": obs.get("name") or prd.get("name"),
            "observed": o,
            "predicted": p,
            "residual": residual,
            "is_proxy": obs.get("is_proxy", False),
        })

    obs_vals = [r["observed"] for r in records if r["observed"] is not None]
    pred_vals = [r["predicted"] for r in records if r["predicted"] is not None]
    abs_res = [abs(r["residual"]) for r in records if r["residual"] is not None]
    stats = {
        "observed_avg": round(sum(obs_vals) / len(obs_vals), 3) if obs_vals else None,
        "predicted_avg": round(sum(pred_vals) / len(pred_vals), 3) if pred_vals else None,
        "mae": round(sum(abs_res) / len(abs_res), 3) if abs_res else None,
        "count_observed": len(obs_vals),
        "count_predicted": len(pred_vals),
    }
    return jsonify({"year": year, "season": season, "stats": stats, "records": records})


@yields_bp.get("/trend")
def trend():
    """Year-over-year yield for a season.

    Query params:
        season          (str) required — 'Dry' or 'Wet'
        municipality_id (int) optional — one municipality's series; omit for the
                              province average across municipalities.

    Returns one point per year: { year, avg, min, max, count }.
    """
    season = request.args.get("season", type=str)
    mid = request.args.get("municipality_id", type=int)
    if not season:
        return jsonify({"error": "season is required"}), 400

    sql = (
        "SELECT s.year, "
        "AVG(r.observed_yield) AS avg, MIN(r.observed_yield) AS min, "
        "MAX(r.observed_yield) AS max, COUNT(*) AS count "
        "FROM municipality_yield_records r "
        "JOIN seasons s ON s.season_id = r.season_id "
        "WHERE s.season_type = :sea"
    )
    params = {"sea": season}
    if mid:
        sql += " AND r.municipality_id = :mid"
        params["mid"] = mid
    sql += " GROUP BY s.year ORDER BY s.year"

    series = [
        {
            "year": row.year,
            "avg": round(row.avg, 3),
            "min": round(row.min, 3),
            "max": round(row.max, 3),
            "count": row.count,
        }
        for row in db.session.execute(text(sql), params)
    ]
    return jsonify({"season": season, "municipality_id": mid, "series": series})
