"""
load_municipality_predictions.py
================================

Load CNN-LSTM model output into municipality_predictions.

Expected CSV columns (header row, case-insensitive; extra columns ignored):
    municipality      - municipality name (matched to the DB, diacritics-folded)
    year              - e.g. 2026
    season            - "Dry" or "Wet"   (or a column named season_type)
    predicted_yield   - predicted average yield in mt/ha  (or a column named yield/prediction)

Idempotent per (municipality, season, year, model_version): re-running updates
existing rows rather than duplicating them. Seasons are created as needed.

Usage
-----
    python backend/scripts/load_municipality_predictions.py \
        --csv path/to/cnn_lstm_predictions.csv \
        --model-version cnn-lstm-v1

When your model produces output, save it as a CSV with the columns above and run
this — the Predicted / residual overlay lights up automatically.
"""
import argparse
import csv
import os
import sys
import unicodedata

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.strip().lower().split())


def pick(row_lower, *names):
    """Return the first present column value from a lower-cased-key dict."""
    for n in names:
        if n in row_lower and str(row_lower[n]).strip() != "":
            return row_lower[n]
    return None


def main():
    ap = argparse.ArgumentParser(description="Load CNN-LSTM predictions into municipality_predictions.")
    ap.add_argument("--csv", required=True, help="Prediction CSV (see module docstring for columns).")
    ap.add_argument("--model-version", default="cnn-lstm", help="Tag for this model run (default: cnn-lstm).")
    args = ap.parse_args()

    with open(args.csv, newline="", encoding="utf-8") as fh:
        raw = list(csv.DictReader(fh))
    if not raw:
        print("CSV has no rows.", file=sys.stderr)
        return 1
    rows = [{(k or "").strip().lower(): v for k, v in r.items()} for r in raw]

    app = create_app()
    with app.app_context():
        muni = {
            norm(r.municipality_name): r.municipality_id
            for r in db.session.execute(text("SELECT municipality_id, municipality_name FROM municipalities"))
        }
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

        inserted = updated = skipped = 0
        for r in rows:
            name = pick(r, "municipality", "municipality_name", "location name", "location_name")
            season = pick(r, "season", "season_type")
            year = pick(r, "year")
            pred = pick(r, "predicted_yield", "prediction", "yield", "predicted")
            if not (name and season and year and pred is not None):
                skipped += 1
                continue
            mid = muni.get(norm(name))
            if mid is None:
                print(f"  skip: no municipality match for {name!r}")
                skipped += 1
                continue
            season = str(season).strip().capitalize()  # dry -> Dry
            sid = season_id(season, int(float(year)))
            val = float(pred)

            existing = db.session.execute(
                text(
                    "SELECT muni_pred_id FROM municipality_predictions "
                    "WHERE municipality_id = :m AND season_id = :s AND model_version = :mv"
                ),
                {"m": mid, "s": sid, "mv": args.model_version},
            ).scalar()
            if existing:
                db.session.execute(
                    text(
                        "UPDATE municipality_predictions "
                        "SET predicted_yield = :v, generated_at = now() WHERE muni_pred_id = :id"
                    ),
                    {"v": val, "id": existing},
                )
                updated += 1
            else:
                db.session.execute(
                    text(
                        "INSERT INTO municipality_predictions "
                        "(predicted_yield, municipality_id, season_id, model_version) "
                        "VALUES (:v, :m, :s, :mv)"
                    ),
                    {"v": val, "m": mid, "s": sid, "mv": args.model_version},
                )
                inserted += 1

        db.session.commit()
        total = db.session.execute(text("SELECT COUNT(*) FROM municipality_predictions")).scalar()
        print(f"done. inserted {inserted}, updated {updated}, skipped {skipped}. table now has {total} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
