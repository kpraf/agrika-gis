"""
load_barangay_predictions.py
============================

Create (if needed) and load the barangay_predictions table from
predict_barangay_cnn_lstm.py's output. Idempotent: upserts on
(barangay_id, season_id, model_version).

Observed yields stay in barangay_yield; this stores only the model's predicted
value per (barangay, season). /yield/barangays/compare joins the two.

Usage
    python backend/scripts/load_barangay_predictions.py
    python backend/scripts/load_barangay_predictions.py --csv db/barangay_cnn_lstm_predictions.csv
"""
import argparse
import csv
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "db"))
DEF_CSV = os.path.join(DB_DIR, "barangay_cnn_lstm_predictions.csv")
MODEL_VERSION = "cnn-lstm-s2s1-barangay"

DDL = [
    """
    CREATE TABLE IF NOT EXISTS barangay_predictions (
        brgy_pred_id    SERIAL PRIMARY KEY,
        barangay_id     INTEGER NOT NULL REFERENCES barangays(barangay_id),
        season_id       INTEGER NOT NULL REFERENCES seasons(season_id),
        predicted_yield DOUBLE PRECISION NOT NULL,
        model_version   VARCHAR(60) NOT NULL,
        generated_at    TIMESTAMP DEFAULT NOW(),
        UNIQUE (barangay_id, season_id, model_version)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_barangay_predictions_brgy ON barangay_predictions(barangay_id)",
]


def fold(s):
    return re.sub(r"\s+", " ", str(s).strip().lower()).replace(".", "").replace("sta ", "santa ")


def main():
    ap = argparse.ArgumentParser(description="Load barangay CNN-LSTM predictions.")
    ap.add_argument("--csv", default=DEF_CSV)
    ap.add_argument("--model-version", default=MODEL_VERSION)
    args = ap.parse_args()

    with open(args.csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    app = create_app()
    with app.app_context():
        for stmt in DDL:
            db.session.execute(text(stmt))
        db.session.commit()

        brgy_map = {
            (fold(r.municipality_name), fold(r.barangay_name)): r.barangay_id
            for r in db.session.execute(text(
                "SELECT b.barangay_id, b.barangay_name, m.municipality_name "
                "FROM barangays b JOIN municipalities m ON m.municipality_id = b.municipality_id"
            ))
        }
        season_cache = {}

        def season_id(stype, year):
            key = (stype, year)
            if key not in season_cache:
                season_cache[key] = db.session.execute(
                    text("SELECT season_id FROM seasons WHERE season_type = :t AND year = :y"),
                    {"t": stype, "y": year},
                ).scalar()
            return season_cache[key]

        upsert = text(
            "INSERT INTO barangay_predictions (barangay_id, season_id, predicted_yield, model_version) "
            "VALUES (:b, :s, :p, :mv) "
            "ON CONFLICT (barangay_id, season_id, model_version) DO UPDATE SET "
            "predicted_yield = EXCLUDED.predicted_yield, generated_at = NOW()"
        )

        loaded = skipped = 0
        unmatched = set()
        for r in rows:
            bid = brgy_map.get((fold(r["municipality"]), fold(r["barangay"])))
            sid = season_id(str(r["season"]).strip().capitalize(), int(float(r["year"])))
            if bid is None or sid is None:
                unmatched.add(f'{r["municipality"]}/{r["barangay"]} {r["season"]} {r["year"]}')
                skipped += 1
                continue
            db.session.execute(upsert, {"b": bid, "s": sid, "p": float(r["predicted"]), "mv": args.model_version})
            loaded += 1
        db.session.commit()
        total = db.session.execute(text("SELECT COUNT(*) FROM barangay_predictions")).scalar()
        print(f"loaded {loaded}, skipped {skipped}. barangay_predictions now has {total} rows.")
        if unmatched:
            print(f"  unmatched: {sorted(unmatched)[:10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
