"""
faithful_model.py
=================

Objective 1 rebuilt faithfully on the previous AgriKA study's method (Ebron et al.,
2025), with Sentinel-1 added, predicting the real seasonal yield.

What is kept from the previous study
    * three growth phases per season (their Tables 11 and 12)
          Dry  Sep 16 - Nov 15 | Nov 16 - Jan 15 | Jan 16 - Mar 15
          Wet  Mar 16 - May 15 | May 16 - Jul 15 | Jul 16 - Sep 15
    * one Sentinel-2 NDVI picture per phase over their rice-field outlines,
      224 x 224, through ResNet50 (2,048 features)          previous_study_images.py
    * the other inputs of each phase: city code, temperature on the picture
      date, day of year, month, green ratio (2,053 values per phase in all)
    * their rules for a phase with no usable picture: mid-date, mean
      temperature, mean picture features
    * the CNN-LSTM of their thesis (Test Four, as recreated in cnn_lstm_model.py)

What changes
    * target: the observed seasonal yield of the city (metric tons per hectare),
      the quantity the system predicts. Their "Adjusted Yield" divided each
      season's yield among the phases by green ratio; here the three phases of
      a season are the three time steps of one sequence and the model predicts
      the season's yield once, so no yield is divided.
    * enhanced configuration: a Sentinel-1 picture per phase (VV, VH and their
      ratio, previous_study_s1_images.py) through the same ResNet50, adding
      2,048 values to each phase.
    * evaluation: leave one year out over 2018-2025 (the present study's
      protocol), repeated runs, baselines, chronological test, 2026 seasons,
      barangay transfer.

Variants (inputs per phase)
    base        their inputs: NDVI picture features, city, temperature, day, month, green ratio
    enh         base + Sentinel-1 picture features
    s1only      Sentinel-1 picture features + city, temperature, day, month (no NDVI picture)
    base_wx     base + rainfall and humidity over the phase
    enh_wx      enh + rainfall and humidity over the phase
    nogreen     enh without the green ratio
Phases (early forecast): k = 1, 2 or 3 phases of the season.

Jobs are split across workers (--worker/--workers); each saves its predictions in
db/experiments/faithful/ and is skipped when its file exists. --report collects
them into faithful_results.json and docs/experiment-results-faithful.md.

Usage
    python backend/scripts/faithful_model.py --describe
    python backend/scripts/faithful_model.py --worker 0 --workers 4 --threads 3
    python backend/scripts/faithful_model.py --report
"""
import argparse
import datetime as dt
import json
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import torch  # noqa: E402
from sklearn.ensemble import RandomForestRegressor  # noqa: E402
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score  # noqa: E402

import cnn_lstm_model as cm  # noqa: E402
import previous_study_images as psi  # noqa: E402

DB = os.path.abspath(os.path.join(HERE, "..", "db"))
PS = os.path.join(DB, "previous_study")
BR = os.path.join(PS, "barangay")
OUT = os.path.join(DB, "experiments", "faithful")
DOC = os.path.abspath(os.path.join(DB, "..", "..", "docs", "experiment-results-faithful.md"))
N_IMG = 2048
VARIANTS = {
    "base": dict(ndvi=True, s1=False, green=True, wx=False),
    "enh": dict(ndvi=True, s1=True, green=True, wx=False),
    "s1only": dict(ndvi=False, s1=True, green=False, wx=False),
    "base_wx": dict(ndvi=True, s1=False, green=True, wx=True),
    "enh_wx": dict(ndvi=True, s1=True, green=True, wx=True),
    "nogreen": dict(ndvi=True, s1=True, green=False, wx=False),
}
LABEL = {"base": "Baseline (previous study's inputs, NDVI pictures)", "enh": "Enhanced (+ Sentinel-1 pictures)",
         "s1only": "Sentinel-1 pictures without NDVI pictures", "base_wx": "Baseline + rainfall and humidity",
         "enh_wx": "Enhanced + rainfall and humidity", "nogreen": "Enhanced without green ratio"}


def key(name):
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    s = " ".join(s.split())
    return s[len("city of "):] if s.startswith("city of ") else s


def metrics(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return [float(np.sqrt(mean_squared_error(y, p))), float(mean_absolute_error(y, p)), float(r2_score(y, p))]


# ------------------------------------------------------------------ inputs
def load_npz(path):
    z = np.load(path, allow_pickle=False)
    return {f: i for i, f in enumerate(z["files"])}, z["features"].astype(np.float32)


def phase_weather(area_key, year, semester, phase, monthly):
    """Rainfall (mm, prorated) and mean humidity over a phase window from monthly municipality values."""
    start, end = [(s, e) for p, s, e in psi.phase_windows(year, semester) if p == phase][0]
    rain, hum, days, d = 0.0, 0.0, 0, start
    while d <= end:
        v = monthly.get((area_key, d.year, d.month))
        if v is not None:
            ndays = (dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1) - dt.date(d.year, d.month, 1)).days
            rain += v[0] / ndays
            hum += v[1]
            days += 1
        d += dt.timedelta(days=1)
    return (rain, hum / days) if days else (np.nan, np.nan)


class Data:
    """Phase rows for one level (cities from the previous study's fields, or the 42 barangays)."""

    def __init__(self, level="city"):
        self.level = level
        folder = PS if level == "city" else BR
        self.idx = pd.read_csv(os.path.join(folder, "image_index.csv")).fillna({"file": "", "date": ""})
        self.idx1 = pd.read_csv(os.path.join(folder, "image_index_s1.csv")).fillna({"file": "", "date": ""})
        self.pos, self.feat = load_npz(os.path.join(folder, "image_features.npz"))
        self.pos1, self.feat1 = load_npz(os.path.join(folder, "image_features_s1.npz"))
        t = pd.read_csv(os.path.join(PS, "temperature_daily.csv"))
        self.temp = {(key(c), d): v for c, d, v in t.itertuples(index=False)}
        self.temp_mean = float(t.temp_mean_c.mean())
        w = pd.read_csv(os.path.join(DB, "weather_laguna_monthly.csv"))
        self.monthly = {(key(r.municipality), int(r.year), int(r.month)): (r.rainfall_mm, r.humidity_mean_pct)
                        for r in w.itertuples()}
        rows = []
        s1 = {(r.city, int(r.year), int(r.semester), int(r.phase)): r for r in self.idx1.itertuples(index=False)}
        for r in self.idx.itertuples(index=False):
            area = r.city
            city = area.split("|")[0]
            start, end = [(s, e) for p, s, e in psi.phase_windows(int(r.year), int(r.semester)) if p == int(r.phase)][0]
            has = bool(r.file)
            date = dt.date.fromisoformat(r.date) if has else start + (end - start) / 2
            r1 = s1.get((area, int(r.year), int(r.semester), int(r.phase)))
            rain, hum = phase_weather(key(city), int(r.year), int(r.semester), int(r.phase), self.monthly)
            rows.append({"area": area, "city": key(city), "year": int(r.year), "semester": int(r.semester),
                         "phase": int(r.phase), "has_image": has, "date": date,
                         "feat": self.pos[r.file] if has and r.file in self.pos else -1,
                         "feat1": self.pos1[r1.file] if r1 is not None and r1.file and r1.file in self.pos1 else -1,
                         "green": float(r.green_ratio) if has else 0.0,
                         "temp": self.temp.get((key(city), date.isoformat()), np.nan) if has else np.nan,
                         "rain": rain, "humid": hum})
        df = pd.DataFrame(rows)
        df = df[df.groupby(["area", "year", "semester"])["phase"].transform("count") == 3]
        df = df.sort_values(["area", "year", "semester", "phase"]).reset_index(drop=True)
        df["temp"] = df["temp"].fillna(df.loc[df.has_image, "temp"].mean())        # their rule
        codes = {c: i + 1 for i, c in enumerate(sorted(pd.read_csv(os.path.join(PS, "image_index.csv")).city.map(key).unique()))}
        df["city_code"] = df["city"].map(codes).astype(float)
        df["day"] = [d.timetuple().tm_yday for d in df["date"]]
        df["month"] = [d.month for d in df["date"]]
        self.df = df
        self.seasons = df.drop_duplicates(["area", "year", "semester"])[["area", "city", "year", "semester"]].reset_index(drop=True)
        self.mean_feat = self.feat.mean(axis=0)
        self.mean_feat1 = self.feat1.mean(axis=0)

    def tensor(self, variant, phases=3):
        """(seasons, phases, features) for a variant, aligned with self.seasons."""
        v = VARIANTS[variant]
        df = self.df
        parts = []
        if v["ndvi"]:
            parts.append(np.stack([self.feat[i] if i >= 0 else self.mean_feat for i in df["feat"]]))
        if v["s1"]:
            parts.append(np.stack([self.feat1[i] if i >= 0 else self.mean_feat1 for i in df["feat1"]]))
        tab = ["city_code", "temp", "day", "month"] + (["green"] if v["green"] else []) + (["rain", "humid"] if v["wx"] else [])
        parts.append(df[tab].to_numpy(np.float32))
        flat = np.concatenate(parts, axis=1).astype(np.float32)
        X = flat.reshape(len(self.seasons), 3, -1)[:, :phases, :]
        return X, len(tab)


def minmax_tab(Xtr, *others, n_tab):
    """Min-max scale the tabular columns (the last n_tab) on the training rows, as their code did; pictures raw."""
    if n_tab == 0:
        return (Xtr, *others)
    flat = Xtr[:, :, -n_tab:].reshape(-1, n_tab)
    lo, hi = np.nanmin(flat, axis=0), np.nanmax(flat, axis=0)
    span = np.where(hi > lo, hi - lo, 1.0)

    def apply(a):
        a = a.copy()
        a[:, :, -n_tab:] = np.nan_to_num((a[:, :, -n_tab:] - lo) / span, nan=0.5)
        return a.astype(np.float32)

    return (apply(Xtr), *[apply(o) for o in others])


def yields_city():
    yl = pd.read_csv(os.path.join(DB, "ricelytics_laguna_yield.csv"))
    return {(key(r.municipality), int(r.year), int(r.semester)): float(r.yield_mt_ha) for r in yl.itertuples()}


def yields_barangay():
    files = ["barangay_cnn_lstm_predictions.csv", "barangay_cnn_lstm_predictions_calamba.csv"]
    p = pd.concat([pd.read_csv(os.path.join(DB, f)) for f in files])
    return {(f"{m}|{b}", int(y), 1 if s == "Dry" else 2): float(o)
            for m, b, y, s, o in zip(p.municipality, p.barangay, p.year, p.season, p.observed)}


# ------------------------------------------------------------------ training
def fit_predict(Xtr_all, ytr_all, Xte_list, seed, n_tab):
    rng = np.random.RandomState(seed)
    perm = rng.permutation(len(ytr_all))
    n_val = max(8, int(0.15 * len(ytr_all)))
    va, tr = perm[:n_val], perm[n_val:]
    scaled = minmax_tab(Xtr_all[tr], Xtr_all[va], *Xte_list, n_tab=n_tab)
    cm.SEED = seed
    model = cm.train_one(scaled[0], ytr_all[tr].astype(np.float32), scaled[1], ytr_all[va].astype(np.float32),
                         scaled[0].shape[-1])
    model.eval()
    with torch.no_grad():
        return [model(torch.tensor(x)).numpy() for x in scaled[2:]]


def rf_fit_predict(Xtr, ytr, Xte_list):
    m = RandomForestRegressor(n_estimators=400, random_state=42, n_jobs=-1)
    m.fit(Xtr.reshape(len(Xtr), -1), ytr)
    return [m.predict(x.reshape(len(x), -1)) for x in Xte_list]


# ------------------------------------------------------------------ jobs
def job_list():
    """In order of priority: the 12 paired runs first, then the other evaluations with 3 runs each."""
    jobs = []
    for seed in range(42, 54):
        for v in ("base", "enh"):
            jobs.append(("loyo", v, 3, seed))
    for v in ("base", "enh"):
        jobs.append(("rf_loyo", v, 3, 0))
    for seed in range(42, 45):
        for v in ("base", "enh"):
            for year in (2021, 2022, 2023, 2024, 2025, 2026):
                jobs.append(("chrono", v, 3, seed * 10000 + year))
        for k in (1, 2):
            for v in ("base", "enh"):
                jobs.append(("loyo", v, k, seed))
        for v in ("s1only", "base_wx", "enh_wx", "nogreen"):
            jobs.append(("loyo", v, 3, seed))
    for seed in range(42, 47):
        for v in ("base", "enh"):
            jobs.append(("final", v, 3, seed))          # 2018-2025 -> Dry 2026 cities and barangays 2020-2026
            jobs.append(("final_wet", v, 3, seed))      # 2018-Dry 2026 -> Wet 2026
            jobs.append(("final_wet", v, 2, seed))      # early forecast of Wet 2026 from two phases
    for seed in range(45, 54):                          # 2026-11-03: no-Sentinel-2 variant to 12 runs (panel)
        jobs.append(("loyo", "s1only", 3, seed))
    return jobs


def job_path(job):
    kind, v, k, seed = job
    return os.path.join(OUT, f"{kind}__{v}__k{k}__{seed}.csv")


def run_job(job, city, brgy):
    kind, v, k, seed = job
    X, n_tab = city.tensor(v, k)
    ys = yields_city()
    S = city.seasons
    y = np.array([ys.get((c, yr, se), np.nan) for c, yr, se in zip(S.city, S.year, S.semester)], dtype=np.float32)
    lab = ~np.isnan(y) & (S.year <= 2025).to_numpy()
    out_cols = ["area", "year", "semester"]
    if kind in ("loyo", "rf_loyo"):
        pred = np.full(len(S), np.nan, dtype=np.float32)
        for year in range(2018, 2026):
            te = lab & (S.year == year).to_numpy()
            tr = lab & ~te
            if kind == "loyo":
                pred[te] = fit_predict(X[tr], y[tr], [X[te]], seed + year, n_tab)[0]
            else:
                pred[te] = rf_fit_predict(X[tr], y[tr], [X[te]])[0]
        out = S[lab][out_cols].assign(observed=y[lab], pred=pred[lab])
    elif kind == "chrono":
        s, year = divmod(seed, 10000)
        y26 = np.array([ys.get((c, yr, se), np.nan) for c, yr, se in zip(S.city, S.year, S.semester)], dtype=np.float32)
        te = (S.year == year).to_numpy() & ~np.isnan(y26)
        if year == 2026:
            te &= (S.semester == 1).to_numpy()
        tr = lab & (S.year < year).to_numpy()
        pred = fit_predict(X[tr], y[tr], [X[te]], s + year, n_tab)[0]
        out = S[te][out_cols].assign(observed=y26[te], pred=pred)
    else:
        if kind == "final":
            tr = lab
            te_city = ((S.year == 2026) & (S.semester == 1)).to_numpy()
        else:
            y26 = np.array([ys.get((c, yr, se), np.nan) for c, yr, se in zip(S.city, S.year, S.semester)], dtype=np.float32)
            tr = ~np.isnan(y26) & ~((S.year == 2026) & (S.semester == 2)).to_numpy()
            y = y26
            te_city = ((S.year == 2026) & (S.semester == 2)).to_numpy()
        brgy = brgy()
        Xb, _ = brgy.tensor(v, k)
        B = brgy.seasons
        te_b = (B.year == 2026).to_numpy() & ((B.semester == 1) if kind == "final" else (B.semester == 2)).to_numpy()
        if kind == "final":
            te_b = te_b | (B.year <= 2025).to_numpy()
        pc, pb = fit_predict(X[tr], y[tr], [X[te_city], Xb[te_b]], seed, n_tab)
        yo = yields_city()
        yb = yields_barangay()
        oc = [yo.get((c, yr, se), np.nan) for c, yr, se in zip(S.city[te_city], S.year[te_city], S.semester[te_city])]
        ob = [yb.get((a, yr, se), np.nan) for a, yr, se in zip(B.area[te_b], B.year[te_b], B.semester[te_b])]
        out = pd.concat([S[te_city][out_cols].assign(level="city", observed=oc, pred=pc),
                         B[te_b][out_cols].assign(level="barangay", observed=ob, pred=pb)])
    out.to_csv(job_path(job), index=False)


# ------------------------------------------------------------------ report
def describe(city):
    S = city.seasons
    ys = yields_city()
    lab = np.array([(c, yr, se) in ys for c, yr, se in zip(S.city, S.year, S.semester)]) & (S.year <= 2025).to_numpy()
    df = city.df
    print(f"cities {S.area.nunique()} | seasons with phases {len(S)} | labelled 2018-2025 {lab.sum()}")
    print(f"NDVI picture usable: {df.has_image.mean():.1%} (dry {df[df.semester == 1].has_image.mean():.1%}, "
          f"wet {df[df.semester == 2].has_image.mean():.1%}) | Sentinel-1 picture: {(df.feat1 >= 0).mean():.1%}")
    for v in VARIANTS:
        X, n_tab = city.tensor(v)
        print(f"  {v:<8} input {X.shape} (tabular {n_tab})")


def main():
    ap = argparse.ArgumentParser(description="Faithful Objective 1 model (previous study's method + Sentinel-1).")
    ap.add_argument("--worker", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--threads", type=int, default=3)
    ap.add_argument("--describe", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    torch.set_num_threads(args.threads)
    jobs = job_list()
    if args.list:
        print(f"{len(jobs)} jobs, {sum(os.path.exists(job_path(j)) for j in jobs)} done")
        return 0
    if args.report:
        import faithful_report
        return faithful_report.main()
    city = Data("city")
    if args.describe:
        describe(city)
        return 0
    cache = {}

    def brgy():                             # loaded on first use: only the 2026 jobs need the barangay pictures
        if "b" not in cache:
            import time
            ready = os.path.join(BR, "image_features_s1.npz")
            while not os.path.exists(ready):    # the barangay Sentinel-1 download may still be running
                print("waiting for the barangay Sentinel-1 features ...", flush=True)
                time.sleep(300)
            cache["b"] = Data("barangay")
        return cache["b"]

    mine = [j for i, j in enumerate(jobs) if i % args.workers == args.worker]
    mine.sort(key=lambda j: j[0].startswith("final"))          # barangay-dependent jobs last
    for j in mine:
        if os.path.exists(job_path(j)):
            continue
        run_job(j, city, brgy)
        print(f"done {j}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
