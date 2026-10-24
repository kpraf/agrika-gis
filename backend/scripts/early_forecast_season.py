"""
early_forecast_season.py
========================

Forecast a season BEFORE it ends, from its first k months only, and save the
result as a dated CSV. Read-only: nothing is written to the database and the
app is not touched.

Backed by early_forecast_experiment.py: under leave-one-year-out, a model given
only the first 3 months of each season was about as accurate as the 6-month
model (CNN-LSTM MAE 0.405 vs 0.403; Random Forest 0.375 vs 0.384).

Models (all trained on every observed municipality season before the target,
using the same first k months of each season):
    CNN-LSTM     thesis architecture and features, mean of several seeds
                 (training is not reproducible run to run)
    Random Forest  400 trees, the k months flattened into columns
    Seasonal average  the municipality's mean yield for that season type

Barangays with a reported yield get the CNN-LSTM forecast from their own
features, as in the historical barangay predictions.

Usage
    python backend/scripts/early_forecast_season.py --year 2026 --season Wet --months 3
Output
    db/forecasts/<season><year>_forecast_<k>months_issued_<date>.csv  (+ _barangay)
"""
import argparse
import calendar
import csv
import os
import sys
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.predict_season import (  # noqa: E402
    FEATURES, SEASON_MONTHS, SEASON_ORDER, load_barangays, load_db,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.abspath(os.path.join(HERE, "..", "db", "forecasts"))
MONTH = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def sequence(key, year, season, k, weather, sat, require_full_months=False):
    """First k monthly steps of a season (k x F), or None if a weather month is missing."""
    import numpy as np

    steps = np.full((k, len(FEATURES)), np.nan, dtype=np.float32)
    for i, month in enumerate(SEASON_MONTHS[season][:k]):
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


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"saved {len(rows)} rows -> {path}")


def main():
    ap = argparse.ArgumentParser(description="Forecast a season from its first k months (CSV only).")
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--season", choices=["Dry", "Wet"], required=True)
    ap.add_argument("--months", type=int, default=3)
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    year, season, k = args.year, args.season, args.months
    months_label = f"{MONTH[SEASON_MONTHS[season][0]]}-{MONTH[SEASON_MONTHS[season][k - 1]]} {year}"
    issued = date.today().isoformat()

    from app import create_app

    app = create_app()
    with app.app_context():
        munis, weather, sat, labels = load_db()
        brgys, bweather, bsat, _ = load_barangays()

    if any((y, s) == (year, season) for _, y, s, _ in labels):
        sys.exit(f"ERROR: {season} {year} already has observed yields; this would not be a forecast.")

    import numpy as np
    import torch
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline

    import scripts.cnn_lstm_model as cm

    train = []
    for mid, y, s, yld in labels:
        if (y, SEASON_ORDER[s]) >= (year, SEASON_ORDER[season]):
            continue
        seq = sequence(mid, y, s, k, weather, sat)
        if seq is not None:
            train.append((mid, y, s, seq, yld))
    last = max(((y, s) for _, y, s, _, _ in train), key=lambda t: (t[0], SEASON_ORDER[t[1]]))
    through = f"{last[1]} {last[0]}"

    rice = sorted({m for m, *_ in labels}, key=lambda m: munis[m])
    mt = [(m, sequence(m, year, season, k, weather, sat, require_full_months=True)) for m in rice]
    short = [munis[m] for m, s in mt if s is None]
    mt = [(m, s) for m, s in mt if s is not None]
    bt = []
    if brgys:
        bt = [(b, sequence(b, year, season, k, bweather, bsat, require_full_months=True))
              for b in sorted(brgys, key=lambda b: brgys[b])]
        bt = [(b, s) for b, s in bt if s is not None]
    print(f"forecasting {season} {year} from {months_label} ({k} months), issued {issued}")
    print(f"training on {len(train)} municipality-seasons through {through}; "
          f"{len(mt)} municipalities, {len(bt)} barangays" + (f"; skipped (months incomplete): {short}" if short else ""))

    Xm = np.stack([t[3] for t in train])
    ym = np.array([t[4] for t in train], dtype=np.float32)
    Xt = np.stack([s for _, s in mt] + [s for _, s in bt])
    Xm_s, Xt_s = cm.standardize(Xm, Xt)

    runs = []
    for i in range(args.seeds):
        seed = 42 + i
        cm.SEED = seed  # train_one seeds from the module constant
        perm = np.random.RandomState(seed).permutation(len(Xm_s))
        n_val = max(8, int(0.15 * len(Xm_s)))
        va, tr = perm[:n_val], perm[n_val:]
        model = cm.train_one(Xm_s[tr], ym[tr], Xm_s[va], ym[va], len(FEATURES))
        model.eval()
        with torch.no_grad():
            runs.append(model(torch.tensor(Xt_s)).numpy())
        print(f"  cnn-lstm seed {seed} done", flush=True)
    cnn = np.mean(runs, axis=0)

    rf = Pipeline([("impute", SimpleImputer(strategy="mean")),
                   ("model", RandomForestRegressor(n_estimators=400, random_state=42, n_jobs=-1))])
    rf.fit(Xm.reshape(len(Xm), -1), ym)
    rf_pred = rf.predict(np.stack([s for _, s in mt]).reshape(len(mt), -1))

    hist = {}
    for mid, y, s, _, yld in train:
        if s == season:
            hist.setdefault(mid, []).append(yld)

    common = {"year": year, "season": season, "months_used": months_label, "issued_on": issued,
              "trained_on_samples": len(train), "trained_through": through}
    os.makedirs(OUT_DIR, exist_ok=True)
    stem = f"{season.lower()}{year}_forecast_{k}months_issued_{issued}"
    muni_rows = [{"municipality": munis[m], **common,
                  "cnn_lstm_forecast": round(float(cnn[i]), 3),
                  "cnn_lstm_run_min": round(float(min(r[i] for r in runs)), 3),
                  "cnn_lstm_run_max": round(float(max(r[i] for r in runs)), 3),
                  "random_forest_forecast": round(float(rf_pred[i]), 3),
                  "seasonal_average": round(float(np.mean(hist[m])), 3) if m in hist else ""}
                 for i, (m, _) in enumerate(mt)]
    write(os.path.join(OUT_DIR, stem + ".csv"), muni_rows)
    if bt:
        off = len(mt)
        write(os.path.join(OUT_DIR, stem + "_barangay.csv"),
              [{"municipality": brgys[b][0], "barangay": brgys[b][1], **common,
                "cnn_lstm_forecast": round(float(cnn[off + i]), 3)} for i, (b, _) in enumerate(bt)])

    c = np.array([r["cnn_lstm_forecast"] for r in muni_rows])
    f = np.array([r["random_forest_forecast"] for r in muni_rows])
    a = np.array([r["seasonal_average"] for r in muni_rows if r["seasonal_average"] != ""], dtype=float)
    print(f"\nmunicipality means: CNN-LSTM {c.mean():.2f} (range {c.min():.2f}-{c.max():.2f}) | "
          f"Random Forest {f.mean():.2f} | past {season} average {a.mean():.2f} mt/ha")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
