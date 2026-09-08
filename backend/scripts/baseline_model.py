"""
baseline_model.py
=================

Simple, non-deep baselines for rice-yield prediction on the AgriKA-GIS training
set. Establishes the floor that the CNN-LSTM must beat to justify its complexity,
and defines the shared evaluation protocol reused by every later model so all
comparisons stay apples-to-apples.

Target      yield_mt_ha (real municipality seasonal yield, mt/ha)
Features    30 sensor columns (rain/temp/ndvi/vv/vh x 6 monthly steps), plus
            optionally season + municipality identity.
Missing     satellite gaps (blank NDVI/SAR months) are mean-imputed.

Evaluation  LEAVE-ONE-YEAR-OUT cross-validation (GroupKFold over the 8 years,
            2018-2025). Each sample is predicted once, in the fold where its year
            is held out - so we measure generalization to an unseen season, the
            real use case. Metrics (RMSE, MAE, R2) are computed on the pooled
            out-of-fold predictions, and per-year R2 is reported to show spread.

Note on comparability: the previous paper's RMSE/MAE (0.55 / 0.43) are on a
redistributed "Adjusted Yield" (~1.2 t/ha mean); ours are on real seasonal yield
(~4 mt/ha mean). Absolute errors are NOT comparable; R2 is the fair cross-metric.

Usage
    python backend/scripts/baseline_model.py
"""
import os

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.abspath(os.path.join(HERE, "..", "db"))
WIDE_CSV = os.path.join(DB_DIR, "training_features_wide.csv")

SENSOR_PREFIXES = ["rain", "temp", "ndvi", "vv", "vh"]
STEPS = 6


def load_xy():
    df = pd.read_csv(WIDE_CSV)
    sensor_cols = [f"{p}_m{i}" for p in SENSOR_PREFIXES for i in range(1, STEPS + 1)]
    X_sensor = df[sensor_cols].copy()

    # season as binary, municipality as one-hot (matches the identity info the
    # previous model also had access to).
    season = (df["season"] == "Wet").astype(int).rename("season_wet")
    muni = pd.get_dummies(df["municipality"], prefix="muni")

    y = df["yield_mt_ha"].to_numpy()
    groups = df["year"].to_numpy()
    return X_sensor, season, muni, y, groups, sensor_cols


def evaluate(model, X, y, groups, n_years):
    """Leave-one-year-out OOF predictions -> pooled + per-year metrics."""
    gkf = GroupKFold(n_splits=n_years)
    oof = np.full(len(y), np.nan)
    per_year = {}
    for tr, te in gkf.split(X, y, groups):
        model.fit(X[tr], y[tr])
        oof[te] = model.predict(X[te])
        yr = groups[te][0]
        per_year[yr] = r2_score(y[te], oof[te])
    rmse = np.sqrt(mean_squared_error(y, oof))
    mae = mean_absolute_error(y, oof)
    r2 = r2_score(y, oof)
    return rmse, mae, r2, per_year


def main():
    X_sensor, season, muni, y, groups, sensor_cols = load_xy()
    n_years = len(np.unique(groups))
    print(f"samples: {len(y)} | years: {n_years} | sensor features: {len(sensor_cols)}")
    print(f"target yield_mt_ha: mean {y.mean():.3f}, std {y.std():.3f}, "
          f"range {y.min():.2f}-{y.max():.2f}\n")

    # Two feature sets: environmental only, vs environmental + identity.
    feat_sets = {
        "sensors only": X_sensor,
        "sensors + season + municipality": pd.concat([X_sensor, season, muni], axis=1),
    }

    def ridge():
        return Pipeline([
            ("impute", SimpleImputer(strategy="mean")),
            ("scale", StandardScaler()),
            ("model", Ridge(alpha=10.0)),
        ])

    def rf():
        return Pipeline([
            ("impute", SimpleImputer(strategy="mean")),
            ("model", RandomForestRegressor(n_estimators=400, random_state=42, n_jobs=-1)),
        ])

    rows = []
    # Naive floor (feature-independent).
    r = evaluate(DummyRegressor(strategy="mean"), X_sensor.to_numpy(), y, groups, n_years)
    rows.append(("Mean (naive floor)", "-", *r[:3]))

    for fname, X in feat_sets.items():
        Xv = X.to_numpy()
        rows.append(("Ridge", fname, *evaluate(ridge(), Xv, y, groups, n_years)[:3]))
        rows.append(("RandomForest", fname, *evaluate(rf(), Xv, y, groups, n_years)[:3]))

    # Report
    print(f"{'model':<16}{'features':<34}{'RMSE':>8}{'MAE':>8}{'R2':>8}")
    print("-" * 74)
    for name, feats, rmse, mae, r2 in rows:
        print(f"{name:<16}{feats:<34}{rmse:>8.3f}{mae:>8.3f}{r2:>8.3f}")

    # Per-year spread for the strongest baseline (RF, full features).
    _, _, _, per_year = evaluate(rf(), feat_sets["sensors + season + municipality"].to_numpy(),
                                 y, groups, n_years)
    print("\nRandomForest (full) per-year R2 (leave-that-year-out):")
    for yr in sorted(per_year):
        print(f"  {yr}: {per_year[yr]:+.3f}")

    print("\nReminder: R2 is the fair comparison to the previous paper (their R2 ~0.31 "
          "on a different target scale). Absolute RMSE/MAE are not comparable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
