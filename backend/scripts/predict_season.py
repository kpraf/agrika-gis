"""
predict_season.py
=================

Forward prediction for one season, straight from the centralized database - the
"deliver to the model" end of the pipeline (Objective 3).

Takes the thesis' final CNN-LSTM (enhanced Sentinel-2 + Sentinel-1 feature set,
same architecture and training routine as cnn_lstm_model.py), trains it on every
observed municipality yield from seasons BEFORE the target season, and predicts
the target season from that season's six monthly feature steps. The model never
sees the season it predicts, so the result is a genuine forecast, not a fit.

Two levels, one trained model:
    municipality  every municipality that has a yield record (the ones that grow rice)
                  -> municipality_predictions
    barangay      every barangay that has at least one REPORTED yield on record (a
                  City Agriculture Office has reported a harvest there; estimates do
                  not count) -> barangay_predictions. As for the historical barangay
                  predictions, the municipality-trained model is applied to the
                  barangay's own monthly features.

Everything is read from the database (weather_monthly, satellite_monthly, their
_barangay counterparts, municipality_yield_records, barangay_yield) rather than
the CSVs, so it runs the same way on a laptop and on the scheduled runner.

A season is only predicted once its six months are complete in the weather
archive (Dry = Jan-Jun, Wet = Jul-Dec; the archive lags about five days).

Output: the two prediction tables (upsert), plus CSV copies in
db/cnn_lstm_forward_predictions.csv and db/barangay_cnn_lstm_forward_predictions.csv.

Usage
    python backend/scripts/predict_season.py --auto            # latest complete season, if not done
    python backend/scripts/predict_season.py --year 2026 --season Dry
    python backend/scripts/predict_season.py --auto --levels barangay
    python backend/scripts/predict_season.py --year 2026 --season Dry --force   # regenerate
    python backend/scripts/predict_season.py --auto --dry-run  # compute, do not store
"""
import argparse
import calendar
import csv
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.abspath(os.path.join(HERE, "..", "db"))
OUT_CSV = os.path.join(DB_DIR, "cnn_lstm_forward_predictions.csv")
OUT_CSV_BRGY = os.path.join(DB_DIR, "barangay_cnn_lstm_forward_predictions.csv")

MODEL_VERSION = "cnn-lstm-s2s1"
MODEL_VERSION_BRGY = "cnn-lstm-s2s1-barangay"   # same tag as load_barangay_predictions.py
SEASON_MONTHS = {"Dry": [1, 2, 3, 4, 5, 6], "Wet": [7, 8, 9, 10, 11, 12]}
SEASON_ORDER = {"Dry": 0, "Wet": 1}
# Enhanced (S2+S1) feature set - the thesis' final model. (table, column) per feature.
FEATURES = [
    ("weather", "rainfall_mm"), ("weather", "temp_mean_c"), ("weather", "humidity_mean_pct"),
    ("sat", "ndvi_mean"), ("sat", "vv_mean"), ("sat", "vh_mean"),
]
ARCHIVE_LAG_DAYS = 6
# A barangay counts as rice-producing once a harvest has been REPORTED for it.
REPORTED = "y.yield_mt_ha IS NOT NULL AND NOT COALESCE(y.source ILIKE 'estimated%', FALSE)"


def latest_complete_season(today=None):
    """The most recent (year, season) whose last month the weather archive fully covers."""
    reach = (today or date.today()) - timedelta(days=ARCHIVE_LAG_DAYS)
    if reach >= date(reach.year, 12, 31):
        return reach.year, "Wet"
    if reach >= date(reach.year, 6, 30):
        return reach.year, "Dry"
    return reach.year - 1, "Wet"


def _monthly(table_weather, table_sat, id_col):
    """({(id, year, month): weather row}, {(id, year, month): satellite row}) for one level."""
    from sqlalchemy import text
    from extensions import db

    weather = {(getattr(r, id_col), r.year, r.month): r for r in db.session.execute(text(
        f"SELECT {id_col}, year, month, rainfall_mm, temp_mean_c, humidity_mean_pct, days "
        f"FROM {table_weather}"))}
    sat = {(getattr(r, id_col), r.year, r.month): r for r in db.session.execute(text(
        f"SELECT {id_col}, year, month, ndvi_mean, vv_mean, vh_mean FROM {table_sat}"))}
    return weather, sat


def load_db():
    """Municipality-level monthly features and yield labels, keyed by municipality id."""
    from sqlalchemy import text
    from extensions import db

    munis = {r.municipality_id: r.municipality_name for r in db.session.execute(
        text("SELECT municipality_id, municipality_name FROM municipalities"))}
    weather, sat = _monthly("weather_monthly", "satellite_monthly", "municipality_id")
    labels = [(r.municipality_id, r.year, r.season_type, float(r.observed_yield))
              for r in db.session.execute(text(
                  "SELECT r.municipality_id, s.year, s.season_type, r.observed_yield "
                  "FROM municipality_yield_records r JOIN seasons s ON s.season_id = r.season_id "
                  "ORDER BY r.municipality_id, s.year, s.season_type"))]
    return munis, weather, sat, labels


def load_barangays():
    """Barangays with a reported yield, their monthly features, and their reported yields.

    Returns (None, ...) if this database has no barangay tables.
    """
    from sqlalchemy import text
    from extensions import db

    for t in ("barangay_yield", "weather_monthly_barangay", "satellite_monthly_barangay"):
        if db.session.execute(text("SELECT to_regclass(:t)"), {"t": t}).scalar() is None:
            return None, {}, {}, {}
    brgys = {r.barangay_id: (r.municipality_name, r.barangay_name) for r in db.session.execute(text(
        "SELECT b.barangay_id, b.barangay_name, m.municipality_name FROM barangays b "
        "JOIN municipalities m ON m.municipality_id = b.municipality_id "
        f"WHERE EXISTS (SELECT 1 FROM barangay_yield y WHERE y.barangay_id = b.barangay_id AND {REPORTED})"))}
    weather, sat = _monthly("weather_monthly_barangay", "satellite_monthly_barangay", "barangay_id")
    observed = {(r.barangay_id, r.year, r.season_type): float(r.yield_mt_ha) for r in db.session.execute(text(
        "SELECT y.barangay_id, s.year, s.season_type, y.yield_mt_ha FROM barangay_yield y "
        f"JOIN seasons s ON s.season_id = y.season_id WHERE {REPORTED}"))}
    return brgys, weather, sat, observed


def sequence(key, year, season, weather, sat, require_full_months=False):
    """The season's 6 x F feature steps, or None if any weather month is missing.

    Weather is required (as in build_training_rows.py); satellite gaps stay NaN and
    are handled by the model's standardisation, exactly as in training.
    require_full_months additionally rejects a month the archive has not finished.
    """
    import numpy as np

    steps = np.full((len(SEASON_MONTHS[season]), len(FEATURES)), np.nan, dtype=np.float32)
    for i, month in enumerate(SEASON_MONTHS[season]):
        wx = weather.get((key, year, month))
        if wx is None or wx.rainfall_mm is None or wx.temp_mean_c is None or wx.humidity_mean_pct is None:
            return None
        if require_full_months and (wx.days or 0) < calendar.monthrange(year, month)[1]:
            return None
        sx = sat.get((key, year, month))
        for j, (source, col) in enumerate(FEATURES):
            v = getattr(wx, col) if source == "weather" else (getattr(sx, col) if sx else None)
            if v is not None:
                steps[i, j] = v
    return steps


def write_csv(path, rows, fields, key_fields):
    """Merge this run's rows into the CSV copy (replacing the same area-season)."""
    kept = []
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as fh:
            new_keys = {tuple(str(r[k]) for k in key_fields) for r in rows}
            kept = [r for r in csv.DictReader(fh) if tuple(r[k] for k in key_fields) not in new_keys]
    merged = kept + [{k: r[k] for k in fields} for r in rows]
    merged.sort(key=lambda r: (int(r["year"]), SEASON_ORDER[r["season"]], *(str(r[k]) for k in key_fields)))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(merged)


def score(pairs):
    """(MAE, RMSE) over (predicted, observed) pairs."""
    mae = sum(abs(p - o) for p, o in pairs) / len(pairs)
    rmse = (sum((p - o) ** 2 for p, o in pairs) / len(pairs)) ** 0.5
    return mae, rmse


def main():
    ap = argparse.ArgumentParser(description="Forward-predict one season from the database.")
    ap.add_argument("--auto", action="store_true",
                    help="Target the latest complete season; do nothing if it is already predicted.")
    ap.add_argument("--year", type=int)
    ap.add_argument("--season", choices=["Dry", "Wet"])
    ap.add_argument("--levels", default="municipality,barangay",
                    help="Which levels to predict: municipality, barangay, or both (default).")
    ap.add_argument("--force", action="store_true", help="Regenerate even if predictions exist.")
    ap.add_argument("--dry-run", action="store_true", help="Compute and print; store nothing.")
    args = ap.parse_args()
    levels = {x.strip() for x in args.levels.split(",") if x.strip()}
    if not levels or levels - {"municipality", "barangay"}:
        sys.exit("ERROR: --levels takes municipality, barangay, or both.")

    if args.auto:
        year, season = latest_complete_season()
    elif args.year and args.season:
        year, season = args.year, args.season
        ly, ls = latest_complete_season()
        if (year, SEASON_ORDER[season]) > (ly, SEASON_ORDER[ls]):
            sys.exit(f"ERROR: {season} {year} is not complete yet - its months are still being recorded.")
    else:
        sys.exit("ERROR: give --auto, or both --year and --season.")
    print(f"target season: {season} {year}")

    from sqlalchemy import text
    from app import create_app
    from extensions import db

    app = create_app()
    with app.app_context():
        def stored(table, version):
            if db.session.execute(text("SELECT to_regclass(:t)"), {"t": table}).scalar() is None:
                return 0
            return db.session.execute(text(
                f"SELECT COUNT(*) FROM {table} p JOIN seasons s ON s.season_id = p.season_id "
                "WHERE s.year = :y AND s.season_type = :t AND p.model_version = :mv"),
                {"y": year, "t": season, "mv": version}).scalar()

        munis, weather, sat, labels = load_db()

        # --- what to predict, per level --------------------------------------
        muni_targets = []
        if "municipality" in levels:
            n = stored("municipality_predictions", MODEL_VERSION)
            if n and not args.force:
                print(f"municipality: up to date ({n} predictions already stored).")
            else:
                rice = sorted({m for m, *_ in labels}, key=lambda m: munis[m])
                seqs = [(m, sequence(m, year, season, weather, sat, require_full_months=True)) for m in rice]
                muni_targets = [(m, s) for m, s in seqs if s is not None]
                short = [munis[m] for m, s in seqs if s is None]
                if short:
                    print(f"municipality: {len(short)} skipped, weather months incomplete: " + ", ".join(short))

        brgy_targets, brgys, brgy_observed = [], {}, {}
        if "barangay" in levels:
            brgys, bweather, bsat, brgy_observed = load_barangays()
            n = stored("barangay_predictions", MODEL_VERSION_BRGY)
            if brgys is None:
                print("barangay: this database has no barangay tables. Skipped.")
                brgys = {}
            elif n and not args.force:
                print(f"barangay: up to date ({n} predictions already stored).")
            else:
                order = sorted(brgys, key=lambda b: brgys[b])
                seqs = [(b, sequence(b, year, season, bweather, bsat, require_full_months=True)) for b in order]
                brgy_targets = [(b, s) for b, s in seqs if s is not None]
                short = [f"{brgys[b][1]} ({brgys[b][0]})" for b, s in seqs if s is None]
                print(f"barangay: {len(brgys)} barangays have a reported yield on record; "
                      f"{len(brgy_targets)} have all six {season} {year} months of features.")
                if short:
                    print(f"  not ready ({len(short)}): " + ", ".join(short[:12]) + (" ..." if len(short) > 12 else ""))

        if not muni_targets and not brgy_targets:
            print("Nothing to do.")
            return 0

        # --- what to learn from: every observed municipality season before the target
        train = []
        for mid, y, s, yld in labels:
            if (y, SEASON_ORDER[s]) >= (year, SEASON_ORDER[season]):
                continue
            seq = sequence(mid, y, s, weather, sat)
            if seq is not None:
                train.append((seq, yld, y, s))
        if len(train) < 100:
            sys.exit(f"ERROR: only {len(train)} training samples before {season} {year}; refusing to "
                     "train a model on that little.")
        last_y, last_s = max(((y, s) for _, _, y, s in train), key=lambda k: (k[0], SEASON_ORDER[k[1]]))
        through = f"{last_s} {last_y}"
        print(f"training on {len(train)} observed municipality-seasons (through {through}); predicting "
              f"{len(muni_targets)} municipalities and {len(brgy_targets)} barangays")

        # Heavy imports only once there is something to do.
        import numpy as np
        import torch
        from scripts.cnn_lstm_model import SEED, set_seed, standardize, train_one

        set_seed(SEED)
        Xm = np.stack([t[0] for t in train])
        ym = np.array([t[1] for t in train], dtype=np.float32)
        targets = muni_targets + brgy_targets
        Xt = np.stack([seq for _, seq in targets])
        Xm_s, Xt_s = standardize(Xm, Xt)   # targets scaled with the TRAINING mean/std

        # Same routine as the historical barangay predictions: all prior data, with a
        # small random slice held out for early stopping.
        n = len(Xm_s)
        perm = np.random.RandomState(SEED).permutation(n)
        n_val = max(8, int(0.15 * n))
        va, tr = perm[:n_val], perm[n_val:]
        model = train_one(Xm_s[tr], ym[tr], Xm_s[va], ym[va], len(FEATURES))
        model.eval()
        with torch.no_grad():
            pred = [round(float(p), 4) for p in model(torch.tensor(Xt_s)).numpy()]
        muni_pred, brgy_pred = pred[:len(muni_targets)], pred[len(muni_targets):]

        muni_rows = [{"mid": m, "municipality": munis[m], "year": year, "season": season, "predicted_yield": p,
                      "trained_on_samples": len(train), "trained_through": through}
                     for (m, _), p in zip(muni_targets, muni_pred)]
        brgy_rows = [{"bid": b, "municipality": brgys[b][0], "barangay": brgys[b][1], "year": year,
                      "season": season, "predicted": p, "trained_on_samples": len(train),
                      "trained_through": through}
                     for (b, _), p in zip(brgy_targets, brgy_pred)]

        if muni_rows:
            vals = [r["predicted_yield"] for r in muni_rows]
            print(f"municipality: predicted range {min(vals):.2f}-{max(vals):.2f} mt/ha")
            observed = {m: yld for m, y, s, yld in labels if (y, s) == (year, season)}
            pairs = [(r["predicted_yield"], observed[r["mid"]]) for r in muni_rows if r["mid"] in observed]
            if pairs:
                mae, rmse = score(pairs)
                print(f"  against the {len(pairs)} observed yields already on record: "
                      f"MAE {mae:.3f} | RMSE {rmse:.3f} mt/ha (out-of-sample)")
        if brgy_rows:
            vals = [r["predicted"] for r in brgy_rows]
            print(f"barangay: predicted range {min(vals):.2f}-{max(vals):.2f} mt/ha")
            pairs = [(r["predicted"], brgy_observed[(r["bid"], year, season)]) for r in brgy_rows
                     if (r["bid"], year, season) in brgy_observed]
            if pairs:
                mae, rmse = score(pairs)
                print(f"  against the {len(pairs)} reported yields already on record: "
                      f"MAE {mae:.3f} | RMSE {rmse:.3f} mt/ha (out-of-sample)")
            else:
                print("  no barangay yield has been reported for this season yet, so there is nothing to score.")

        if args.dry_run:
            print("dry run: nothing stored.")
            return 0

        # --- store ------------------------------------------------------------
        sid = db.session.execute(text(
            "SELECT season_id FROM seasons WHERE season_type = :t AND year = :y"),
            {"t": season, "y": year}).scalar()
        if sid is None:
            sid = db.session.execute(text(
                "INSERT INTO seasons (season_type, year) VALUES (:t, :y) RETURNING season_id"),
                {"t": season, "y": year}).scalar()
        if muni_rows:
            db.session.execute(text(
                "INSERT INTO municipality_predictions (predicted_yield, municipality_id, season_id, model_version) "
                "VALUES (:v, :m, :s, :mv) "
                "ON CONFLICT (municipality_id, season_id, model_version) "
                "DO UPDATE SET predicted_yield = EXCLUDED.predicted_yield, generated_at = now()"),
                [{"v": r["predicted_yield"], "m": r["mid"], "s": sid, "mv": MODEL_VERSION} for r in muni_rows])
        if brgy_rows:
            from scripts.load_barangay_predictions import DDL as BRGY_DDL
            for stmt in BRGY_DDL:
                db.session.execute(text(stmt))
            db.session.execute(text(
                "INSERT INTO barangay_predictions (barangay_id, season_id, predicted_yield, model_version) "
                "VALUES (:b, :s, :p, :mv) "
                "ON CONFLICT (barangay_id, season_id, model_version) "
                "DO UPDATE SET predicted_yield = EXCLUDED.predicted_yield, generated_at = now()"),
                [{"b": r["bid"], "s": sid, "p": r["predicted"], "mv": MODEL_VERSION_BRGY} for r in brgy_rows])
        db.session.commit()
        if muni_rows:
            write_csv(OUT_CSV, muni_rows,
                      ["municipality", "year", "season", "predicted_yield", "trained_on_samples", "trained_through"],
                      ["municipality", "year", "season"])
            print(f"stored {len(muni_rows)} municipality predictions for {season} {year}")
        if brgy_rows:
            write_csv(OUT_CSV_BRGY, brgy_rows,
                      ["municipality", "barangay", "year", "season", "predicted", "trained_on_samples",
                       "trained_through"], ["municipality", "barangay", "year", "season"])
            print(f"stored {len(brgy_rows)} barangay predictions for {season} {year}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
