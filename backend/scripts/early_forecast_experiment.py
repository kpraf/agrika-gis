"""
early_forecast_experiment.py
============================

How early in a season can the model forecast yield? The thesis model uses all
six months of a season (Dry: Jan-Jun, Wet: Jul-Dec), so its output is ready only
after the season ends. Here the same leave-one-year-out evaluation is repeated
with only the first k months of each season (k = 6, 5, 4, 3), for training and
testing alike, so each fold sees exactly what would be known k months in.

Models
    CNN-LSTM, enhanced feature set (rain, temp, humid, ndvi, vv, vh), several
    seeds per k (training is not reproducible run to run); reported as the mean
    of single runs and as the seed-averaged prediction.
    Random Forest on the same k months (flattened), as a stable reference.
    Seasonal mean: each municipality's mean yield for that season in the
    training years (needs no months at all).

Usage
    python backend/scripts/early_forecast_experiment.py --seeds 3
Output
    db/experiments/early_forecast_results.csv, early_forecast_oof.csv
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
from sklearn.ensemble import RandomForestRegressor  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402

import scripts.cnn_lstm_model as cm  # noqa: E402

FEATURES = cm.FEATURE_SETS["S2+S1 (enhanced)"]
OUT_DIR = os.path.join(cm.DB_DIR, "experiments")


def metrics(y, p):
    return (float(np.sqrt(mean_squared_error(y, p))), float(mean_absolute_error(y, p)), float(r2_score(y, p)))


def cnn_oof(X, y, groups, seed):
    cm.SEED = seed  # train_one seeds from the module constant
    oof = np.full(len(y), np.nan, dtype=np.float32)
    rng = np.random.RandomState(seed)
    for tr, te in GroupKFold(n_splits=len(np.unique(groups))).split(X, y, groups):
        perm = rng.permutation(len(tr))
        n_val = max(8, int(0.15 * len(tr)))
        va_idx, tr_idx = tr[perm[:n_val]], tr[perm[n_val:]]
        Xtr, Xva, Xte = cm.standardize(X[tr_idx], X[va_idx], X[te])
        model = cm.train_one(Xtr, y[tr_idx], Xva, y[va_idx], X.shape[-1])
        model.eval()
        with torch.no_grad():
            oof[te] = model(torch.tensor(Xte)).numpy()
    return oof


def rf_oof(X, y, groups):
    Xf = X.reshape(len(X), -1)
    oof = np.full(len(y), np.nan)
    for tr, te in GroupKFold(n_splits=len(np.unique(groups))).split(Xf, y, groups):
        m = Pipeline([("impute", SimpleImputer(strategy="mean")),
                      ("model", RandomForestRegressor(n_estimators=400, random_state=42, n_jobs=-1))])
        m.fit(Xf[tr], y[tr])
        oof[te] = m.predict(Xf[te])
    return oof


def seasonal_mean_oof(keys, y, groups):
    df = keys[["municipality", "season"]].copy()
    df["y"], df["year"] = y, groups
    oof = np.full(len(y), np.nan)
    for yr in np.unique(groups):
        tr, te = df[df.year != yr], df.year == yr
        mean = tr.groupby(["municipality", "season"]).y.mean()
        overall = tr.groupby("season").y.mean()
        oof[te.to_numpy()] = [mean.get((m, s), overall[s]) for m, s in zip(df.municipality[te], df.season[te])]
    return oof


def main():
    ap = argparse.ArgumentParser(description="Leave-one-year-out with only the first k months of each season.")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--months", default="6,5,4,3")
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)

    X, y, groups, keys = cm.load_sequences(FEATURES)
    print(f"{len(y)} samples, features {FEATURES}, seeds {args.seeds}\n", flush=True)
    rows = []
    oofs = keys[["municipality", "year", "season", "yield_mt_ha"]].copy()

    p = seasonal_mean_oof(keys, y, groups)
    oofs["seasonal_mean"] = p
    rows.append(("Seasonal mean (no months)", 0, *metrics(y, p), "", ""))
    print("seasonal mean        RMSE %.3f MAE %.3f R2 %.3f" % metrics(y, p), flush=True)

    for k in [int(v) for v in args.months.split(",")]:
        Xk = X[:, :k, :]
        p = rf_oof(Xk, y, groups)
        oofs[f"rf_k{k}"] = p
        rows.append(("Random Forest", k, *metrics(y, p), "", ""))
        print(f"k={k} random forest  RMSE %.3f MAE %.3f R2 %.3f" % metrics(y, p), flush=True)

        runs = []
        for i in range(args.seeds):
            runs.append(cnn_oof(Xk, y, groups, seed=42 + i))
            print(f"k={k} cnn-lstm seed {42 + i}  RMSE %.3f MAE %.3f R2 %.3f" % metrics(y, runs[-1]), flush=True)
        single = np.array([metrics(y, r) for r in runs])
        avg = np.mean(runs, axis=0)
        oofs[f"cnn_k{k}"] = avg
        r2s = single[:, 2]
        rows.append(("CNN-LSTM (seed-averaged prediction)", k, *metrics(y, avg), "", ""))
        rows.append(("CNN-LSTM (mean of single runs)", k, *single.mean(axis=0),
                     f"{r2s.min():.3f}", f"{r2s.max():.3f}"))

    res = pd.DataFrame(rows, columns=["model", "months", "rmse", "mae", "r2", "r2_min_run", "r2_max_run"])
    res.to_csv(os.path.join(OUT_DIR, "early_forecast_results.csv"), index=False, float_format="%.4f")
    oofs.to_csv(os.path.join(OUT_DIR, "early_forecast_oof.csv"), index=False, float_format="%.4f")
    print("\n" + res.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
