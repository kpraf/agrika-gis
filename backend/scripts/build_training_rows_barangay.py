"""
build_training_rows_barangay.py
===============================

Barangay-level counterpart of build_training_rows.py. Joins the barangay monthly
feature series (weather + satellite) to the observed per-barangay yield labels to
produce training-ready rows for the barangay baseline (and, later, a barangay
CNN-LSTM).

Same alignment as the municipality builder (PSA semester halves):
    Dry -> Jan..Jun, Wet -> Jul..Dec (6 monthly steps).

Labels come from the collected barangay yield CSVs (extract_barangay_yield.py /
the Cabuyao compile), NOT the province Ricelytics set. Only barangays that have a
yield for a (year, season) are emitted. Barangay names are unique within the two
municipalities collected so far (Santa Rosa + Cabuyao), so features (keyed by
barangay name) join unambiguously.

Weather is REQUIRED (complete series); satellite is OPTIONAL (S2 cloud / S1 gaps
left blank, with per-sample completeness counts).

Inputs (backend/db/, overridable)
    weather_barangay_sr_cabuyao_monthly.csv     - from fetch_weather_openmeteo.py --level barangay
    satellite_barangay_sr_cabuyao_monthly.csv   - from fetch_satellite_cdse.py --level barangay
    barangay_yield_city-of-santa-rosa.csv, barangay_yield_city-of-cabuyao.csv - labels

Outputs (backend/db/)
    training_features_barangay_wide.csv
    training_features_barangay_sequences.csv

Usage
    python backend/scripts/build_training_rows_barangay.py
"""
import argparse
import csv
import os
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.abspath(os.path.join(HERE, "..", "db"))

DEF_WEATHER = os.path.join(DB_DIR, "weather_barangay_sr_cabuyao_monthly.csv")
DEF_SATELLITE = os.path.join(DB_DIR, "satellite_barangay_sr_cabuyao_monthly.csv")
DEF_YIELDS = [
    os.path.join(DB_DIR, "barangay_yield_city-of-santa-rosa.csv"),
    os.path.join(DB_DIR, "barangay_yield_city-of-cabuyao.csv"),
]
OUT_LONG = os.path.join(DB_DIR, "training_features_barangay_sequences.csv")
OUT_WIDE = os.path.join(DB_DIR, "training_features_barangay_wide.csv")

SEASON_MONTHS = {"Dry": [1, 2, 3, 4, 5, 6], "Wet": [7, 8, 9, 10, 11, 12]}
STEPS = 6

# (source, source_column, short_name) — same spec/order as the municipality builder.
FEATURES = [
    ("weather", "rainfall_mm",       "rain"),
    ("weather", "temp_mean_c",       "temp"),
    ("weather", "humidity_mean_pct", "humid"),
    ("sat",     "ndvi_mean",         "ndvi"),
    ("sat",     "evi_mean",          "evi"),
    ("sat",     "ndwi_mean",         "ndwi"),
    ("sat",     "vv_mean",           "vv"),
    ("sat",     "vh_mean",           "vh"),
]
WEATHER_REQUIRED = [f for f in FEATURES if f[0] == "weather"]
SAT_FEATURES = [f for f in FEATURES if f[0] == "sat"]


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.strip().lower().split())


def fold(s):
    """norm() plus a couple of barangay spelling folds seen in the source data."""
    n = norm(s).replace(".", "")
    return n.replace("sta ", "santa ")


def _f(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def load_monthly(path, columns):
    """{(fold_barangay, year, month): {col: float|None}}; {} if the file is absent."""
    idx = {}
    if not os.path.exists(path):
        return idx
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        name_key = "barangay" if "barangay" in reader.fieldnames else reader.fieldnames[0]
        for r in reader:
            key = (fold(r[name_key]), int(r["year"]), int(r["month"]))
            idx[key] = {c: _f(r.get(c)) for c in columns}
    return idx


def load_labels(paths):
    """[(municipality, barangay, year, season, yield)] from the barangay yield CSVs."""
    labels = []
    for p in paths:
        if not os.path.exists(p):
            print(f"NOTE: label file not found: {p}")
            continue
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                y = _f(r.get("yield_mt_ha"))
                if y is None:
                    continue  # no-data barangay/season
                labels.append((
                    r["municipality"], r["barangay"], int(float(r["year"])),
                    str(r["season"]).strip().capitalize(), y,
                ))
    return labels


def main():
    ap = argparse.ArgumentParser(description="Build barangay training rows (weather+satellite -> yield).")
    ap.add_argument("--weather", default=DEF_WEATHER)
    ap.add_argument("--satellite", default=DEF_SATELLITE)
    ap.add_argument("--yields", nargs="*", default=DEF_YIELDS)
    ap.add_argument("--out-wide", default=OUT_WIDE)
    ap.add_argument("--out-long", default=OUT_LONG)
    args = ap.parse_args()

    weather = load_monthly(args.weather, [c for _, c, _ in WEATHER_REQUIRED])
    satellite = load_monthly(args.satellite, [c for _, c, _ in SAT_FEATURES])
    labels = load_labels(args.yields)

    if not weather:
        print(f"ERROR: no weather rows read from {args.weather}. Nothing to do.")
        return 1
    have_sat = bool(satellite)
    if not have_sat:
        print(f"NOTE: {args.satellite} not found - satellite columns will be blank.\n")

    long_rows, wide_rows, skipped = [], [], []

    for muni, brgy, year, season, yld in labels:
        months = SEASON_MONTHS.get(season)
        if not months:
            skipped.append((muni, brgy, year, season, "unknown season"))
            continue

        steps, missing = [], []
        for month in months:
            wx = weather.get((fold(brgy), year, month))
            if wx is None or any(wx.get(c) is None for _, c, _ in WEATHER_REQUIRED):
                missing.append(month)
                continue
            sx = satellite.get((fold(brgy), year, month), {})
            step_vals = {}
            for source, col, short in FEATURES:
                step_vals[short] = (wx if source == "weather" else sx).get(col)
            steps.append((month, step_vals))
        if len(steps) != STEPS:
            skipped.append((muni, brgy, year, season, f"missing weather months {missing}"))
            continue

        for step_i, (month, vals) in enumerate(steps, 1):
            row = {"municipality": muni, "barangay": brgy, "year": year, "season": season,
                   "seq_step": step_i, "month": month}
            for _, _, short in FEATURES:
                row[short] = vals[short]
            row["yield_mt_ha"] = yld
            long_rows.append(row)

        wide = {"municipality": muni, "barangay": brgy, "year": year, "season": season}
        for step_i, (_, vals) in enumerate(steps, 1):
            for _, _, short in FEATURES:
                wide[f"{short}_m{step_i}"] = vals[short]
        wide["ndvi_present"] = sum(1 for _, v in steps if v.get("ndvi") is not None)
        wide["s1_present"] = sum(1 for _, v in steps if v.get("vv") is not None)
        wide["yield_mt_ha"] = yld
        wide_rows.append(wide)

    long_fields = (["municipality", "barangay", "year", "season", "seq_step", "month"]
                   + [short for _, _, short in FEATURES] + ["yield_mt_ha"])
    with open(args.out_long, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=long_fields)
        w.writeheader()
        w.writerows(long_rows)

    wide_fields = ["municipality", "barangay", "year", "season"]
    for _, _, short in FEATURES:
        wide_fields += [f"{short}_m{i}" for i in range(1, STEPS + 1)]
    wide_fields += ["ndvi_present", "s1_present", "yield_mt_ha"]
    with open(args.out_wide, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=wide_fields)
        w.writeheader()
        w.writerows(wide_rows)

    print(f"labels read:      {len(labels)}")
    print(f"training samples: {len(wide_rows)}  ({len(long_rows)} long rows)")
    if have_sat:
        full_ndvi = sum(1 for r in wide_rows if r["ndvi_present"] == STEPS)
        full_s1 = sum(1 for r in wide_rows if r["s1_present"] == STEPS)
        any_ndvi = sum(1 for r in wide_rows if r["ndvi_present"] > 0)
        print(f"  full NDVI (6/6): {full_ndvi}   any NDVI: {any_ndvi}")
        print(f"  full S1   (6/6): {full_s1}")
    print(f"skipped:          {len(skipped)}")
    for muni, brgy, year, season, why in skipped[:25]:
        print(f"    - {muni}/{brgy} {year} {season}: {why}")
    if len(skipped) > 25:
        print(f"    ... and {len(skipped) - 25} more")
    print(f"\nwrote {args.out_wide}")
    print(f"wrote {args.out_long}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
