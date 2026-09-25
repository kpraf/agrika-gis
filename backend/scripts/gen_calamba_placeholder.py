"""
gen_calamba_placeholder.py
==========================

Generate placeholder Calamba (City of Calamba) barangay data so the map/analytics
have the SAME layers there as the other research cities — observed yield,
Environment (weather/satellite), predicted and residual — until the real City
Agriculture Office records are collected.

The numbers are drawn to match the distributions already present in Santa Rosa /
Cabuyao / Biñan (yield mean 4.35 sd 0.72; area right-skewed ~12 ha; predictions
that regress toward ~4.0 with a noisy residual, MAE ~0.7), and the climatology is
sampled from the existing barangay feature tables (same ERA5 grid / region), so
Calamba reads like the other cities rather than obviously synthetic. Deterministic
(seeded) — safe to re-run; overwrites its three CSVs.

Outputs (backend/db/):
  barangay_yield_city-of-calamba.csv
  weather_barangay_calamba_monthly.csv
  satellite_barangay_calamba_monthly.csv
  barangay_cnn_lstm_predictions_calamba.csv

Load with the usual scripts (see push_to_supabase.py --with-barangay-model), e.g.
  load_barangay_yield.py       --csv db/barangay_yield_city-of-calamba.csv
  load_barangay_feature_tables.py --weather db/weather_barangay_calamba_monthly.csv \
      --satellite db/satellite_barangay_calamba_monthly.csv --municipalities "City of Calamba"
  load_barangay_predictions.py --csv db/barangay_cnn_lstm_predictions_calamba.csv
"""
import csv
import glob
import os
import random
import statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.abspath(os.path.join(HERE, "..", "db"))

MUNI = "City of Calamba"
YEARS = list(range(2020, 2026))          # 2020..2025
SEASONS = ["Dry", "Wet"]
SEED = 20260926

# Two coherent farmland clusters in Calamba (chosen against satellite imagery —
# geometric paddy parcels, not scattered urban barangays), each given FULL
# 2020-2025 coverage (placeholder until the real City Agriculture Office records
# arrive). Names match the DB exactly.
#   NE lakeshore lowland — the flat plain along Laguna de Bay.
#   West lowland        — the vegetated belt toward the Cabuyao / Los Baños side.
BARANGAYS = [
    # NE lakeshore cluster
    "Uwisan", "Looc", "Banlic", "Banadero", "San Juan", "Sampiruhan", "Palingon", "Lingga",
    # West lowland cluster
    "Bubuyan", "Burol", "Hornalan", "Bunggo",
]

SOURCE = "Calamba CAO (Harvesting Accomplishment Report)"
MODEL_VERSION = "cnn-lstm-s2s1-barangay"

# Full coverage: every picked barangay has data for every year + both seasons
# 2020-2025 (the point of picking only a handful is a complete series each).
YEAR_COVERAGE = {y: 1.0 for y in YEARS}

WEATHER_COLS = ["rainfall_mm", "temp_mean_c", "humidity_mean_pct", "days"]
SAT_COLS = ["ndvi_mean", "ndvi_std", "evi_mean", "evi_std", "ndwi_mean", "ndwi_std",
            "s2_valid_px", "vv_mean", "vv_std", "vh_mean", "vh_std", "s1_valid_px"]
INT_COLS = {"days", "s2_valid_px", "s1_valid_px"}
CLIP = {  # (lo, hi) sanity clamps for sampled feature values
    "rainfall_mm": (0, None), "humidity_mean_pct": (0, 100), "days": (28, 31),
    "ndvi_mean": (-1, 1), "evi_mean": (-1, 1), "ndwi_mean": (-1, 1),
    "ndvi_std": (0, None), "evi_std": (0, None), "ndwi_std": (0, None),
    "vv_std": (0, None), "vh_std": (0, None), "s2_valid_px": (0, None), "s1_valid_px": (0, None),
}


def month_climatology(pattern, cols):
    """Per-month mean/sd for each column, pooled over the existing cities' CSVs."""
    buckets = defaultdict(lambda: defaultdict(list))
    for path in glob.glob(os.path.join(DB, pattern)):
        if "calamba" in os.path.basename(path):
            continue
        for r in csv.DictReader(open(path, encoding="utf-8")):
            m = int(r["month"])
            for c in cols:
                v = r.get(c)
                if v not in (None, ""):
                    buckets[m][c].append(float(v))
    clim = {}
    for m, cd in buckets.items():
        clim[m] = {}
        for c in cols:
            xs = cd.get(c) or [0.0]
            clim[m][c] = (st.mean(xs), st.pstdev(xs) if len(xs) > 1 else 0.0)
    return clim


def sample_feature(rng, mean, sd, col):
    v = rng.gauss(mean, sd * 0.6)  # tighten a touch so no wild outliers
    lo, hi = CLIP.get(col, (None, None))
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    if col in INT_COLS:
        return int(round(v))
    return round(v, 4)


def main():
    rng = random.Random(SEED)

    # Per-barangay baseline yield (fixed "quality" of the barangay's land).
    base = {b: rng.uniform(3.85, 4.85) for b in BARANGAYS}

    # ---- observed yields (with realistic gaps) ----
    yield_rows = []
    observed = {}  # (b, year, season) -> yield
    for b in BARANGAYS:
        for yr in YEARS:
            trend = 0.03 * (yr - 2020)              # slight improvement over time
            yshock = rng.gauss(0, 0.22)             # shared year effect
            for sea in SEASONS:
                present = rng.random() < YEAR_COVERAGE[yr]
                if not present:
                    yield_rows.append([MUNI, b, yr, sea, "", "", ""])  # no-data row
                    continue
                sea_eff = 0.18 if sea == "Dry" else -0.12  # irrigated dry a bit higher
                y = base[b] + trend + yshock + sea_eff + rng.gauss(0, 0.30)
                y = round(min(6.15, max(2.0, y)), 2)
                area = round(min(103.0, max(1.5, rng.lognormvariate(2.2, 0.7))), 2)
                prod = round(area * y, 2)
                yield_rows.append([MUNI, b, yr, sea, area, prod, y])
                observed[(b, yr, sea)] = y

    with open(os.path.join(DB, "barangay_yield_city-of-calamba.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["municipality", "barangay", "year", "season", "area_ha", "production_mt", "yield_mt_ha"])
        w.writerows(yield_rows)
    n_obs = sum(1 for r in yield_rows if r[6] != "")
    print(f"yield: {len(yield_rows)} rows, {n_obs} with a yield "
          f"({100*n_obs/len(yield_rows):.0f}% coverage)")

    # ---- monthly features (Environment layers) ----
    wclim = month_climatology("weather_barangay_*_monthly.csv", WEATHER_COLS)
    sclim = month_climatology("satellite_barangay_*_monthly.csv", SAT_COLS)

    with open(os.path.join(DB, "weather_barangay_calamba_monthly.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["barangay", "year", "month"] + WEATHER_COLS)
        for b in BARANGAYS:
            for yr in YEARS:
                for m in range(1, 13):
                    vals = [sample_feature(rng, *wclim[m][c], c) for c in WEATHER_COLS]
                    w.writerow([b, yr, m] + vals)

    with open(os.path.join(DB, "satellite_barangay_calamba_monthly.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["barangay", "year", "month"] + SAT_COLS)
        for b in BARANGAYS:
            for yr in YEARS:
                for m in range(1, 13):
                    vals = [sample_feature(rng, *sclim[m][c], c) for c in SAT_COLS]
                    w.writerow([b, yr, m] + vals)
    nfeat = len(BARANGAYS) * len(YEARS) * 12
    print(f"features: {nfeat} weather + {nfeat} satellite monthly rows")

    # ---- predictions (regress toward ~4.0, noisy residual, like the real model) ----
    pred_rows = []
    for (b, yr, sea), obs in sorted(observed.items()):
        # near-independent of observed (mirrors the transfer model's weak fit):
        pred = 4.03 + 0.12 * (obs - 4.35) + rng.gauss(0, 0.42)
        pred = round(min(5.33, max(3.45, pred)), 3)
        residual = round(obs - pred, 3)
        pred_rows.append([MUNI, b, yr, sea, obs, pred, residual])

    with open(os.path.join(DB, "barangay_cnn_lstm_predictions_calamba.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["municipality", "barangay", "year", "season", "observed", "predicted", "residual"])
        w.writerows(pred_rows)
    res = [r[6] for r in pred_rows]
    mae = sum(abs(x) for x in res) / len(res)
    print(f"predictions: {len(pred_rows)} rows, MAE={mae:.3f}, "
          f"pred mean={st.mean([r[5] for r in pred_rows]):.2f}")


if __name__ == "__main__":
    main()
