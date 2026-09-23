"""
Public yield endpoints — serve observed municipality yields for the map.

Backed by municipality_yield_records (real PRiSM/Ricelytics data, mt/ha),
joined to seasons (season_type + year) and municipalities. No auth required:
the public yield map consumes these.
"""
import csv
import io

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import text

from extensions import db

yields_bp = Blueprint("yields", __name__, url_prefix="/api/yield")

# Roles allowed to import observed-yield data. (The Reports module is already
# gated to these roles on the frontend; the backend enforces it too.)
IMPORT_ROLES = {"administrator", "agriculturist", "rice_technician"}

# Validation bounds for an imported row.
_VALID_SEASONS = {"wet": "Wet", "dry": "Dry"}
_MIN_YEAR, _MAX_YEAR = 2000, 2100
_MIN_YIELD, _MAX_YIELD = 0.0, 20.0  # mt/ha — palay averages sit well inside this


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
    # Barangay ground truth starts later (collected 2020+), so barangay-scoped
    # year pickers use this narrower list instead of the municipality years.
    barangay_years = [
        r.year
        for r in db.session.execute(
            text(
                "SELECT DISTINCT s.year FROM barangay_yield y "
                "JOIN seasons s ON s.season_id = y.season_id "
                "WHERE y.yield_mt_ha IS NOT NULL ORDER BY s.year"
            )
        )
    ]
    return jsonify({"years": years, "seasons": seasons, "barangay_years": barangay_years})


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


@yields_bp.get("/barangays")
def barangays_yield():
    """Real per-barangay observed yield for a municipality + year + season.

    Backed by barangay_yield (collected manually from the City Agriculture
    Offices' Planting & Harvesting reports). Only barangays that reported a
    harvest for this municipality/year/season are returned; everything else is
    absent and the UI greys it. No synthetic/placeholder data is produced.

    Query params: municipality_id (int), year (int), season (str) — all required.
    """
    mid = request.args.get("municipality_id", type=int)
    year = request.args.get("year", type=int)
    season = request.args.get("season", type=str)
    if not mid or not year or not season:
        return jsonify({"error": "municipality_id, year and season are required"}), 400

    rows = db.session.execute(
        text(
            "SELECT b.barangay_id, b.barangay_name, y.yield_mt_ha, y.area_ha, y.production_mt "
            "FROM barangay_yield y "
            "JOIN barangays b ON b.barangay_id = y.barangay_id "
            "JOIN seasons s ON s.season_id = y.season_id "
            "WHERE b.municipality_id = :m AND s.year = :y AND s.season_type = :sea "
            "AND y.yield_mt_ha IS NOT NULL "
            "ORDER BY b.barangay_name"
        ),
        {"m": mid, "y": year, "sea": season},
    ).all()

    records = [
        {
            "barangay_id": r.barangay_id,
            "name": r.barangay_name,
            "yield": round(r.yield_mt_ha, 3),
            "area_ha": r.area_ha,
            "production_mt": r.production_mt,
        }
        for r in rows
    ]
    values = [r["yield"] for r in records]
    stats = {
        "count": len(values),
        "min": round(min(values), 3) if values else None,
        "max": round(max(values), 3) if values else None,
        "avg": round(sum(values) / len(values), 3) if values else None,
    }
    return jsonify({
        "municipality_id": mid,
        "year": year,
        "season": season,
        "stats": stats,
        "records": records,
    })


@yields_bp.get("/barangays/municipalities")
def barangays_municipalities():
    """Municipalities that actually have per-barangay yield data collected.

    Drives the Analytics "compare barangays" municipality picker — barangays are
    only ever compared within their own municipality.
    """
    rows = db.session.execute(
        text(
            "SELECT DISTINCT m.municipality_id, m.municipality_name "
            "FROM barangay_yield y "
            "JOIN barangays b ON b.barangay_id = y.barangay_id "
            "JOIN municipalities m ON m.municipality_id = b.municipality_id "
            "WHERE y.yield_mt_ha IS NOT NULL "
            "ORDER BY m.municipality_name"
        )
    ).all()
    return jsonify({
        "municipalities": [
            {"municipality_id": r.municipality_id, "name": r.municipality_name} for r in rows
        ]
    })


@yields_bp.get("/barangays/series")
def barangays_series():
    """Year-over-year observed yield for every barangay of one municipality, in a
    season — for the Analytics barangay comparison (scoped to one municipality).

    Query params: municipality_id (int), season (str) — both required.

    Returns { municipality_id, season, years: [...], barangays: [
        { barangay_id, name, series: { <year>: yield_mt_ha } } ] }.
    """
    mid = request.args.get("municipality_id", type=int)
    season = request.args.get("season", type=str)
    if not mid or not season:
        return jsonify({"error": "municipality_id and season are required"}), 400

    rows = db.session.execute(
        text(
            "SELECT b.barangay_id, b.barangay_name, s.year, y.yield_mt_ha "
            "FROM barangay_yield y "
            "JOIN barangays b ON b.barangay_id = y.barangay_id "
            "JOIN seasons s ON s.season_id = y.season_id "
            "WHERE b.municipality_id = :m AND s.season_type = :sea "
            "AND y.yield_mt_ha IS NOT NULL "
            "ORDER BY b.barangay_name, s.year"
        ),
        {"m": mid, "sea": season},
    ).all()

    years = sorted({r.year for r in rows})
    bmap = {}
    for r in rows:
        e = bmap.setdefault(
            r.barangay_id,
            {"barangay_id": r.barangay_id, "name": r.barangay_name, "series": {}},
        )
        e["series"][r.year] = round(r.yield_mt_ha, 3)
    return jsonify({
        "municipality_id": mid,
        "season": season,
        "years": years,
        "barangays": list(bmap.values()),
    })


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


@yields_bp.get("/barangays/records")
def barangay_records():
    """Flat list of every observed barangay yield for one municipality — the
    barangay-level counterpart to /records, for the Reports page.

    Query param: municipality_id (int, required).
    One row per barangay-year-season: { barangay, municipality, year, season, yield }.
    """
    mid = request.args.get("municipality_id", type=int)
    if not mid:
        return jsonify({"error": "municipality_id is required"}), 400

    rows = db.session.execute(
        text(
            "SELECT b.barangay_name, m.municipality_name, s.year, s.season_type, y.yield_mt_ha "
            "FROM barangay_yield y "
            "JOIN barangays b ON b.barangay_id = y.barangay_id "
            "JOIN municipalities m ON m.municipality_id = b.municipality_id "
            "JOIN seasons s ON s.season_id = y.season_id "
            "WHERE b.municipality_id = :m AND y.yield_mt_ha IS NOT NULL "
            "ORDER BY s.year, s.season_type, b.barangay_name"
        ),
        {"m": mid},
    ).all()
    return jsonify({
        "municipality_id": mid,
        "records": [
            {
                "barangay": r.barangay_name,
                "municipality": r.municipality_name,
                "year": r.year,
                "season": r.season_type,
                "yield": round(r.yield_mt_ha, 3),
            }
            for r in rows
        ],
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


# --- CSV import -------------------------------------------------------------
# Upsert observed yields from a CSV upload — municipality or barangay level.
# Built for adding new seasons (e.g. 2026 Dry / Wet). Mirrors the offline
# loaders: resolve names to ids, get-or-create the (season_type, year) season,
# then upsert per (target, season). UNIQUE constraints keep re-uploads
# idempotent. Column headers are case-insensitive and order-independent.
def _pick(row, *names):
    """Return the first matching column value: exact header first, then substring."""
    lowered = {(k or "").strip().lower(): v for k, v in row.items()}
    for n in names:
        if n in lowered:
            return lowered[n]
    for key, val in lowered.items():
        if any(n in key for n in names):
            return val
    return None


@yields_bp.post("/import")
@jwt_required()
def import_yields():
    """Import observed yields from a CSV upload — municipality or barangay level.

    Body: { csv: str, level?: 'municipality'|'barangay', source?: str }.

    Municipality level → municipality_yield_records, keyed (municipality, season).
        Columns: municipality (or city), year, season, yield (or yield_mt_ha).
    Barangay level → barangay_yield, keyed (barangay, season). The barangay is
        resolved within its municipality (names aren't globally unique).
        Columns: municipality (or city), barangay (or brgy), year, season, yield.

    Both are idempotent upserts (UNIQUE constraints), validate each row, skip and
    report bad rows, and commit the good ones (partial success). Only yield_mt_ha
    is written for barangays (area_ha / production_mt are left untouched).
    """
    if get_jwt().get("role") not in IMPORT_ROLES:
        return jsonify({"error": "You don't have permission to import yield data."}), 403

    payload = request.get_json(silent=True) or {}
    csv_text = payload.get("csv")
    if not isinstance(csv_text, str) or not csv_text.strip():
        return jsonify({"error": "No CSV content provided."}), 400
    level = str(payload.get("level") or "municipality").strip().lower()
    if level not in ("municipality", "barangay"):
        return jsonify({"error": "level must be 'municipality' or 'barangay'."}), 400
    source = (str(payload.get("source") or "Manual import").strip() or "Manual import")[:50]

    try:
        rows = list(csv.DictReader(io.StringIO(csv_text)))
    except (csv.Error, ValueError):
        return jsonify({"error": "Could not parse the CSV file."}), 400
    if not rows:
        return jsonify({"error": "The CSV has no data rows."}), 400

    # municipality name -> id (normalised for spacing/case)
    muni = {
        r.municipality_name.strip().lower(): r.municipality_id
        for r in db.session.execute(text("SELECT municipality_id, municipality_name FROM municipalities"))
    }
    # (municipality_id, barangay name) -> barangay_id — barangay names repeat across
    # municipalities, so they're only unique within one. Only loaded for barangay imports.
    brgy = {}
    if level == "barangay":
        for r in db.session.execute(
            text("SELECT barangay_id, barangay_name, municipality_id FROM barangays")
        ):
            brgy[(r.municipality_id, r.barangay_name.strip().lower())] = r.barangay_id

    season_cache = {}

    def season_id(season_type, year):
        key = (season_type, year)
        if key in season_cache:
            return season_cache[key]
        sid = db.session.execute(
            text("SELECT season_id FROM seasons WHERE season_type = :t AND year = :y"),
            {"t": season_type, "y": year},
        ).scalar()
        if sid is None:
            sid = db.session.execute(
                text("INSERT INTO seasons (season_type, year) VALUES (:t, :y) RETURNING season_id"),
                {"t": season_type, "y": year},
            ).scalar()
        season_cache[key] = sid
        return sid

    inserted = updated = 0
    errors = []

    for i, row in enumerate(rows, start=2):  # +1 for header, +1 for 1-based
        raw_muni = (str(_pick(row, "municipality", "city") or "")).strip()
        raw_brgy = (str(_pick(row, "barangay", "brgy") or "")).strip()
        raw_year = (str(_pick(row, "year") or "")).strip()
        raw_season = (str(_pick(row, "season") or "")).strip()
        raw_yield = (str(_pick(row, "yield_mt_ha", "yield") or "")).strip()

        # Skip fully blank lines silently.
        if not any([raw_muni, raw_brgy, raw_year, raw_season, raw_yield]):
            continue

        mid = muni.get(raw_muni.lower())
        if mid is None:
            errors.append({"row": i, "error": f"Unknown municipality '{raw_muni}'."})
            continue

        # Barangay level: resolve the barangay within its municipality.
        bid = None
        if level == "barangay":
            if not raw_brgy:
                errors.append({"row": i, "error": "Missing barangay."})
                continue
            bid = brgy.get((mid, raw_brgy.lower()))
            if bid is None:
                errors.append({"row": i, "error": f"Unknown barangay '{raw_brgy}' in {raw_muni}."})
                continue

        season_type = _VALID_SEASONS.get(raw_season.lower().replace(" season", "").strip())
        if season_type is None:
            errors.append({"row": i, "error": f"Season must be Wet or Dry (got '{raw_season}')."})
            continue

        try:
            year = int(float(raw_year))
        except ValueError:
            errors.append({"row": i, "error": f"Invalid year '{raw_year}'."})
            continue
        if not (_MIN_YEAR <= year <= _MAX_YEAR):
            errors.append({"row": i, "error": f"Year {year} is out of range ({_MIN_YEAR}-{_MAX_YEAR})."})
            continue

        try:
            yld = float(raw_yield)
        except ValueError:
            errors.append({"row": i, "error": f"Invalid yield '{raw_yield}'."})
            continue
        if not (_MIN_YIELD < yld <= _MAX_YIELD):
            errors.append({"row": i, "error": f"Yield {yld} is out of range (0-{_MAX_YIELD} mt/ha)."})
            continue

        sid = season_id(season_type, year)

        if level == "barangay":
            existing = db.session.execute(
                text("SELECT brgy_yield_id FROM barangay_yield WHERE barangay_id = :b AND season_id = :s"),
                {"b": bid, "s": sid},
            ).scalar()
            if existing:
                db.session.execute(
                    text("UPDATE barangay_yield SET yield_mt_ha = :y, source = :src WHERE brgy_yield_id = :id"),
                    {"y": yld, "src": source, "id": existing},
                )
                updated += 1
            else:
                db.session.execute(
                    text(
                        "INSERT INTO barangay_yield (barangay_id, season_id, yield_mt_ha, source) "
                        "VALUES (:b, :s, :y, :src)"
                    ),
                    {"b": bid, "s": sid, "y": yld, "src": source},
                )
                inserted += 1
        else:
            existing = db.session.execute(
                text(
                    "SELECT muni_yield_id FROM municipality_yield_records "
                    "WHERE municipality_id = :m AND season_id = :s"
                ),
                {"m": mid, "s": sid},
            ).scalar()
            if existing:
                db.session.execute(
                    text(
                        "UPDATE municipality_yield_records "
                        "SET observed_yield = :y, source = :src, is_proxy = FALSE "
                        "WHERE muni_yield_id = :id"
                    ),
                    {"y": yld, "src": source, "id": existing},
                )
                updated += 1
            else:
                db.session.execute(
                    text(
                        "INSERT INTO municipality_yield_records "
                        "(observed_yield, municipality_id, season_id, source, is_proxy) "
                        "VALUES (:y, :m, :s, :src, FALSE)"
                    ),
                    {"y": yld, "m": mid, "s": sid, "src": source},
                )
                inserted += 1

    # Commit the valid rows (partial success); invalid rows are reported, not fatal.
    db.session.commit()
    total_table = "barangay_yield" if level == "barangay" else "municipality_yield_records"
    total = db.session.execute(text(f"SELECT COUNT(*) FROM {total_table}")).scalar()
    return jsonify(
        {
            "level": level,
            "inserted": inserted,
            "updated": updated,
            "skipped": len(errors),
            "errors": errors[:50],  # cap the payload; enough to diagnose a bad file
            "total": total,
        }
    )
