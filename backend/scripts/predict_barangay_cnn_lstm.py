"""
predict_barangay_cnn_lstm.py
============================

Barangay-level predictions from the thesis CNN-LSTM. There is no separate
barangay model (the barangay baseline underperforms at this sample size — see
docs/experiment-results-barangay.md). Instead we take the SAME CNN-LSTM
(enhanced S2+S1 feature set), train it on ALL municipality data, and apply it to
each barangay's own environmental features. The residual (observed − predicted)
then shows how the municipality-trained model transfers to barangay scale.

Predictions are produced only for (barangay, year, season) that have an observed
yield — the barangay sequences are built from barangay_yield labels.

Inputs
    db/training_features_sequences.csv           (municipality, for training)
    db/training_features_barangay_sequences.csv  (barangay, to predict)
Output
    db/barangay_cnn_lstm_predictions.csv
        municipality, barangay, year, season, observed, predicted, residual
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402

from scripts.cnn_lstm_model import (  # noqa: E402
    STEPS, SEED, set_seed, load_sequences, standardize, train_one,
)

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.abspath(os.path.join(HERE, "..", "db"))
BRGY_SEQ = os.path.join(DB_DIR, "training_features_barangay_sequences.csv")
OUT = os.path.join(DB_DIR, "barangay_cnn_lstm_predictions.csv")

# Enhanced (S2+S1) feature set — the thesis' final model.
FEATURES = ["rain", "temp", "humid", "ndvi", "vv", "vh"]
KEY = ["municipality", "barangay", "year", "season"]


def load_barangay_sequences(cols):
    df = pd.read_csv(BRGY_SEQ).sort_values(KEY + ["seq_step"])
    keys = df[KEY + ["yield_mt_ha"]].drop_duplicates(KEY).reset_index(drop=True)
    X = np.full((len(keys), STEPS, len(cols)), np.nan, dtype=np.float32)
    idx = {tuple(r): i for i, r in enumerate(keys[KEY].itertuples(index=False, name=None))}
    for r in df.itertuples(index=False):
        i = idx[(r.municipality, r.barangay, r.year, r.season)]
        step = int(r.seq_step) - 1
        for j, c in enumerate(cols):
            X[i, step, j] = getattr(r, c)
    return X, keys


def main():
    set_seed(SEED)
    Xm, ym, _groups, _mkeys = load_sequences(FEATURES)   # municipality (train)
    Xb, bkeys = load_barangay_sequences(FEATURES)        # barangay (predict)
    # Standardize barangay features with the MUNICIPALITY mean/std (same scale).
    Xm_s, Xb_s = standardize(Xm, Xb)

    # Train on all municipality samples, holding out a small random slice for
    # early stopping (barangays are never in the training set — no leakage).
    n = len(Xm_s)
    perm = np.random.RandomState(SEED).permutation(n)
    n_val = max(8, int(0.15 * n))
    va, tr = perm[:n_val], perm[n_val:]
    model = train_one(Xm_s[tr], ym[tr], Xm_s[va], ym[va], len(FEATURES))
    model.eval()
    with torch.no_grad():
        pred = model(torch.tensor(Xb_s)).numpy()

    out = bkeys.rename(columns={"yield_mt_ha": "observed"}).copy()
    out["predicted"] = np.round(pred, 3)
    out["residual"] = np.round(out["observed"] - out["predicted"], 3)
    out = out[["municipality", "barangay", "year", "season", "observed", "predicted", "residual"]]
    out.to_csv(OUT, index=False)

    mae = float(np.mean(np.abs(out["residual"])))
    print(f"predicted {len(out)} barangay-seasons | MAE {mae:.3f} mt/ha "
          f"| pred range {out['predicted'].min():.2f}-{out['predicted'].max():.2f}")
    print(out.head(10).to_string(index=False))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
