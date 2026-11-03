"""
predict_season_faithful.py
==========================

Season prediction of the faithful Objective 1 model, the delivery end of the
pipeline (Objective 3). Once the third growth phase of a season has ended
(March 15 for the dry season, September 15 for the wet season), the enhanced
model (NDVI and Sentinel-1 pictures per phase, faithful_model.py) is trained on
every observed municipality season before it, read from the database, and
predicts the season for the 28 cities and for the barangays with a reported yield.
The prediction is the mean of several training runs, because single runs vary.

Retraining: every forecast is logged in forecast_runs with the number of reported
seasons it was trained on. On a later run, a season that already has a forecast is
predicted again only when more reported seasons exist than at its last forecast (new
yields were uploaded), so the forecast always uses every season reported so far. A
forecast made before this log existed is logged as it stands, not redone.

Needs the picture records on disk (phase_pictures_stage.py --export, then --fetch).

Usage
    python backend/scripts/predict_season_faithful.py --auto
    python backend/scripts/predict_season_faithful.py --year 2026 --season Wet --dry-run
"""
import argparse
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

import faithful_model as fm  # noqa: E402
import previous_study_images as psi  # noqa: E402

MODEL_VERSION = "cnn-lstm-faithful-s1"
MODEL_VERSION_BRGY = "cnn-lstm-faithful-s1-barangay"
SEASON = {1: "Dry", 2: "Wet"}
LOG_DDL = """
CREATE TABLE IF NOT EXISTS forecast_runs (
    run_id       serial PRIMARY KEY,
    year         integer NOT NULL,
    season       text    NOT NULL,
    model_version text   NOT NULL,
    n_train      integer NOT NULL,     -- reported city seasons the model was trained on
    n_cities     integer,
    n_barangays  integer,
    stored       boolean NOT NULL,     -- false: logged only (forecast made before the log)
    created_at   timestamptz NOT NULL DEFAULT now()
)"""


def latest_season(today=None):
    """(year, semester) of the latest season whose third growth phase has ended."""
    today = today or dt.date.today()
    ends = [(psi.phase_windows(y, s)[2][2], y, s) for y in (today.year - 1, today.year, today.year + 1) for s in (1, 2)]
    _, y, s = max(e for e in ends if e[0] < today)
    return y, s


def main():
    ap = argparse.ArgumentParser(description="Predict a season with the faithful model once its phases have ended.")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--year", type=int)
    ap.add_argument("--season", choices=["Dry", "Wet"])
    ap.add_argument("--runs", type=int, default=3, help="Training runs averaged into the prediction.")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.auto:
        year, sem = latest_season()
    elif args.year and args.season:
        year, sem = args.year, 1 if args.season == "Dry" else 2
        if psi.phase_windows(year, sem)[2][2] >= dt.date.today():
            sys.exit(f"ERROR: the third phase of {args.season} {year} has not ended yet.")
    else:
        sys.exit("ERROR: give --auto, or both --year and --season.")
    season = SEASON[sem]
    print(f"target season: {season} {year}")

    from sqlalchemy import text
    from app import create_app
    from extensions import db

    with create_app().app_context():
        db.session.execute(text(LOG_DDL))
        db.session.commit()
        done = db.session.execute(text(
            "SELECT COUNT(*) FROM municipality_predictions p JOIN seasons s ON s.season_id = p.season_id "
            "WHERE s.year = :y AND s.season_type = :t AND p.model_version = :mv"),
            {"y": year, "t": season, "mv": MODEL_VERSION}).scalar()
        munis = {fm.key(r.municipality_name): r.municipality_id for r in db.session.execute(
            text("SELECT municipality_id, municipality_name FROM municipalities"))}
        labels = {(fm.key(r.municipality_name), r.year, 1 if r.season_type == "Dry" else 2): float(r.observed_yield)
                  for r in db.session.execute(text(
                      "SELECT m.municipality_name, s.year, s.season_type, r.observed_yield "
                      "FROM municipality_yield_records r JOIN seasons s ON s.season_id = r.season_id "
                      "JOIN municipalities m ON m.municipality_id = r.municipality_id"))}
        brgys = {(fm.key(r.municipality_name), fm.key(r.barangay_name)): r.barangay_id for r in db.session.execute(text(
            "SELECT b.barangay_id, b.barangay_name, m.municipality_name FROM barangays b "
            "JOIN municipalities m ON m.municipality_id = b.municipality_id"))}

        city = fm.Data("city")
        X, n_tab = city.tensor("enh")
        S = city.seasons
        order = (S.year * 2 + S.semester).to_numpy()
        y = np.array([labels.get((c, yr, se), np.nan) for c, yr, se in zip(S.city, S.year, S.semester)], np.float32)
        tr = ~np.isnan(y) & (order < year * 2 + sem)
        tc = ((S.year == year) & (S.semester == sem)).to_numpy()
        targets = [X[tc]]
        brgy = None
        if os.path.exists(os.path.join(fm.BR, "image_features_s1.npz")):
            brgy = fm.Data("barangay")
            Xb, _ = brgy.tensor("enh")
            tb = ((brgy.seasons.year == year) & (brgy.seasons.semester == sem)).to_numpy()
            targets.append(Xb[tb])
        n_train = int(tr.sum())
        if done and not args.force:
            last = db.session.execute(text(
                "SELECT n_train FROM forecast_runs WHERE year = :y AND season = :t AND model_version = :mv "
                "ORDER BY created_at DESC LIMIT 1"), {"y": year, "t": season, "mv": MODEL_VERSION}).scalar()
            if last is None:
                if not args.dry_run:
                    db.session.execute(text(
                        "INSERT INTO forecast_runs (year, season, model_version, n_train, n_cities, stored) "
                        "VALUES (:y, :t, :mv, :n, :c, false)"),
                        {"y": year, "t": season, "mv": MODEL_VERSION, "n": n_train, "c": done})
                    db.session.commit()
                print(f"already predicted ({done} municipalities) before the forecast log; logged with "
                      f"{n_train} training seasons, not redone")
                return 0
            if n_train <= last:
                print(f"already predicted ({done} municipalities) with {last} training seasons; nothing new, nothing to do")
                return 0
            print(f"{n_train - last} more reported seasons since the last forecast ({last}); retraining")
        print(f"training on {n_train} observed seasons; predicting {int(tc.sum())} cities"
              + (f" and {int(tb.sum())} barangays" if brgy is not None else ""))
        preds = [fm.fit_predict(X[tr], y[tr], targets, 42 + i, n_tab) for i in range(args.runs)]
        pc = np.mean([p[0] for p in preds], axis=0)
        rows_c = [(munis.get(c), c, float(v)) for c, v in zip(S.city[tc], pc)]
        rows_b = []
        if brgy is not None:
            pb = np.mean([p[1] for p in preds], axis=0)
            for area, v in zip(brgy.seasons.area[tb], pb):
                m, b = area.split("|")
                rows_b.append((brgys.get((fm.key(m), fm.key(b))), area, float(v)))
        print(f"cities: {min(v for *_, v in rows_c):.2f} to {max(v for *_, v in rows_c):.2f} mt/ha")
        missing = [n for i, n, _ in rows_c + rows_b if i is None]
        if missing:
            print(f"not in the database, skipped: {missing}")
        if args.dry_run:
            print("dry run: nothing stored")
            return 0
        sid = db.session.execute(text("SELECT season_id FROM seasons WHERE season_type = :t AND year = :y"),
                                 {"t": season, "y": year}).scalar()
        if sid is None:
            sid = db.session.execute(text("INSERT INTO seasons (season_type, year) VALUES (:t, :y) RETURNING season_id"),
                                     {"t": season, "y": year}).scalar()
        db.session.execute(text(
            "INSERT INTO municipality_predictions (predicted_yield, municipality_id, season_id, model_version) "
            "VALUES (:v, :m, :s, :mv) ON CONFLICT (municipality_id, season_id, model_version) "
            "DO UPDATE SET predicted_yield = EXCLUDED.predicted_yield, generated_at = now()"),
            [{"v": v, "m": i, "s": sid, "mv": MODEL_VERSION} for i, _, v in rows_c if i is not None])
        if rows_b:
            db.session.execute(text(
                "INSERT INTO barangay_predictions (barangay_id, season_id, predicted_yield, model_version) "
                "VALUES (:b, :s, :p, :mv) ON CONFLICT (barangay_id, season_id, model_version) "
                "DO UPDATE SET predicted_yield = EXCLUDED.predicted_yield, generated_at = now()"),
                [{"b": i, "s": sid, "p": v, "mv": MODEL_VERSION_BRGY} for i, _, v in rows_b if i is not None])
        db.session.execute(text(
            "INSERT INTO forecast_runs (year, season, model_version, n_train, n_cities, n_barangays, stored) "
            "VALUES (:y, :t, :mv, :n, :c, :b, true)"),
            {"y": year, "t": season, "mv": MODEL_VERSION, "n": n_train,
             "c": sum(1 for i, *_ in rows_c if i), "b": sum(1 for i, *_ in rows_b if i)})
        db.session.commit()
        print(f"stored {sum(1 for i, *_ in rows_c if i)} city and {sum(1 for i, *_ in rows_b if i)} barangay predictions "
              f"for {season} {year} ({MODEL_VERSION})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
