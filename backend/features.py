"""
Remote-sensing / meteorological feature endpoints for the map's Environment view.

Serves per-municipality seasonal averages of the monthly features stored in
weather_monthly and satellite_monthly (Objective 3's centralized spatial DB), so
the Web-GIS can visualise the model's INPUTS (NDVI, rainfall, etc.) - the data
that drives the yield predictions - instead of empty land-use placeholders.

No auth: the public yield map consumes these alongside the yield endpoints.
"""
from flask import Blueprint, jsonify, request
from sqlalchemy import text

from extensions import db

features_bp = Blueprint("features", __name__, url_prefix="/api/features")

# metric -> (table, column, label, unit). Table/column come from this whitelist
# only, so interpolating them into SQL is safe.
METRICS = {
    "ndvi":        ("satellite_monthly", "ndvi_mean",         "NDVI",        ""),
    "evi":         ("satellite_monthly", "evi_mean",          "EVI",         ""),
    "ndwi":        ("satellite_monthly", "ndwi_mean",         "NDWI",        ""),
    "rainfall":    ("weather_monthly",   "rainfall_mm",       "Rainfall",    "mm/mo"),
    "temperature": ("weather_monthly",   "temp_mean_c",       "Temperature", "°C"),
    "humidity":    ("weather_monthly",   "humidity_mean_pct", "Humidity",    "%"),
}
# PSA-semester month windows, matching the training-set alignment.
SEASON_MONTHS = {"Dry": [1, 2, 3, 4, 5, 6], "Wet": [7, 8, 9, 10, 11, 12]}


@features_bp.get("/meta")
def meta():
    """List the selectable metrics (for the Environment layer picker)."""
    return jsonify({
        "metrics": [
            {"key": k, "label": lbl, "unit": unit}
            for k, (_, _, lbl, unit) in METRICS.items()
        ]
    })


@features_bp.get("/municipalities")
def municipalities():
    """Per-municipality seasonal average of one feature for a year + season.

    Query params: metric (see METRICS), year (int), season ('Dry'|'Wet').
    Averages the metric over that season's months. Returns records keyed for the
    map plus min/max/avg for the colour scale.
    """
    metric = request.args.get("metric", type=str)
    year = request.args.get("year", type=int)
    season = request.args.get("season", type=str)
    if metric not in METRICS or not year or season not in SEASON_MONTHS:
        return jsonify({"error": "valid metric, year and season are required"}), 400

    table, col, label, unit = METRICS[metric]
    months = SEASON_MONTHS[season]
    rows = db.session.execute(
        text(
            f"SELECT m.municipality_id, m.municipality_name AS name, "
            f"AVG(t.{col}) AS value "
            f"FROM {table} t "
            f"JOIN municipalities m ON m.municipality_id = t.municipality_id "
            f"WHERE t.year = :y AND t.month = ANY(:months) AND t.{col} IS NOT NULL "
            f"GROUP BY m.municipality_id, m.municipality_name "
            f"ORDER BY m.municipality_name"
        ),
        {"y": year, "months": months},
    ).all()

    records = [
        {"municipality_id": r.municipality_id, "name": r.name, "value": round(float(r.value), 3)}
        for r in rows
    ]
    vals = [r["value"] for r in records]
    stats = {
        "count": len(vals),
        "min": round(min(vals), 3) if vals else None,
        "max": round(max(vals), 3) if vals else None,
        "avg": round(sum(vals) / len(vals), 3) if vals else None,
    }
    return jsonify({
        "metric": metric, "label": label, "unit": unit,
        "year": year, "season": season, "stats": stats, "records": records,
    })
