"""
export_cnn_lstm_predictions.py
==============================

Convert the CNN-LSTM out-of-fold predictions into the CSV format that
load_municipality_predictions.py expects, so they can be loaded into the app's
municipality_predictions table and drive the observed-vs-predicted comparison.

We export the ENHANCED (S2+S1) model's predictions - the one with the significant
Sentinel-1 improvement. These are leave-one-year-out predictions, so each year's
value came from a model that never saw that year (honest historical predictions).

Input : db/cnn_lstm_oof_predictions.csv   (from cnn_lstm_model.py)
Output: db/cnn_lstm_predictions_for_app.csv  (municipality, year, season, predicted_yield)

Then load with:
    python backend/scripts/load_municipality_predictions.py \
        --csv db/cnn_lstm_predictions_for_app.csv --model-version cnn-lstm-s2s1
"""
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.abspath(os.path.join(HERE, "..", "db"))
SRC = os.path.join(DB_DIR, "cnn_lstm_oof_predictions.csv")
OUT = os.path.join(DB_DIR, "cnn_lstm_predictions_for_app.csv")


def main():
    df = pd.read_csv(SRC)
    out = df[["municipality", "year", "season"]].copy()
    out["predicted_yield"] = df["pred_s2_s1"].round(4)  # enhanced (S2+S1) model
    out.to_csv(OUT, index=False)
    print(f"wrote {len(out)} predictions -> {OUT}")
    print(out.head().to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
