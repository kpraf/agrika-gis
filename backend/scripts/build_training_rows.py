"""
build_training_rows.py
======================

Join the monthly feature series (weather + satellite) to the observed yield
labels to produce training-ready rows for the CNN-LSTM.

Alignment (chosen: PSA semester halves)
---------------------------------------
Each yield record is a (municipality, year, season) label. We attach the six
monthly steps of that season's own calendar half-year:

    Dry  (semester 1)  ->  Jan, Feb, Mar, Apr, May, Jun
    Wet  (semester 2)  ->  Jul, Aug, Sep, Oct, Nov, Dec

Features per monthly step
-------------------------
    weather   rainfall_mm, temp_mean_c        (from weather_laguna_monthly.csv)
    satellite ndvi_mean, vv_mean, vh_mean      (from satellite_laguna_monthly.csv)

Weather is REQUIRED: a sample is emitted only if all six weather months exist
(they always do - that series is complete). Satellite is OPTIONAL and often has
gaps (S2 clouds, the 2022 S1 coverage dip), so missing satellite values are left
BLANK rather than dropping the sample. Two completeness counts per sample let you
filter or decide how to gap-fill at training time - this script does NOT
interpolate, so nothing is silently invented:

    ndvi_present   how many of the 6 steps have an NDVI value   (0-6)
    s1_present     how many of the 6 steps have VV/VH values     (0-6)

If satellite_laguna_monthly.csv is absent, the satellite columns are still
written (blank) and a warning is printed - run fetch_satellite_cdse.py to fill
them, then re-run this. The output schema does not change either way.

Inputs  (backend/db/)
    weather_laguna_monthly.csv       - REQUIRED, from fetch_weather_openmeteo.py
    satellite_laguna_monthly.csv     - OPTIONAL, from fetch_satellite_cdse.py
    ricelytics_laguna_yield.csv      - labels

Outputs (backend/db/)
    training_features_sequences.csv  - LONG / tidy: one row per (muni, season, step)
    training_features_wide.csv       - WIDE: one row per training sample
        (short column names: rain_m*, temp_m*, ndvi_m*, vv_m*, vh_m*;
         m1 = first month of the window: Jan for Dry, Jul for Wet)

Usage
    python backend/scripts/build_training_rows.py
"""
import csv
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.abspath(os.path.join(HERE, "..", "db"))
WEATHER_CSV = os.path.join(DB_DIR, "weather_laguna_monthly.csv")
SATELLITE_CSV = os.path.join(DB_DIR, "satellite_laguna_monthly.csv")
YIELD_CSV = os.path.join(DB_DIR, "ricelytics_laguna_yield.csv")
OUT_LONG = os.path.join(DB_DIR, "training_features_sequences.csv")
OUT_WIDE = os.path.join(DB_DIR, "training_features_wide.csv")

# Season -> ordered calendar months of that season's half-year.
SEASON_MONTHS = {
    "Dry": [1, 2, 3, 4, 5, 6],
    "Wet": [7, 8, 9, 10, 11, 12],
}
STEPS = 6

# Feature spec: (source, source_column, short_name). Order = column order.
# Edit here to add features (e.g. ndvi_std) - long + wide outputs follow.
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


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.strip().lower().split())


def fold(s: str) -> str:
    """norm() plus dropping a leading 'city of ' so name sets line up."""
    n = norm(s)
    return n[len("city of "):] if n.startswith("city of ") else n


def _f(v):
    """Parse a CSV cell to float, or None if blank/absent."""
    if v is None or str(v).strip() == "":
        return None
    return float(v)


def load_monthly(path, columns):
    """{(fold_name, year, month): {col: float|None}} for the given columns.

    Returns {} if the file does not exist.
    """
    idx = {}
    if not os.path.exists(path):
        return idx
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        name_key = "municipality" if "municipality" in reader.fieldnames else reader.fieldnames[0]
        for r in reader:
            key = (fold(r[name_key]), int(r["year"]), int(r["month"]))
            idx[key] = {c: _f(r.get(c)) for c in columns}
    return idx


def load_yield():
    """[(municipality, year, season, yield, suspected_proxy)] labels."""
    labels = []
    with open(YIELD_CSV, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            labels.append((
                r["municipality"],
                int(r["year"]),
                r["season_type"].strip().capitalize(),
                float(r["yield_mt_ha"]),
                str(r.get("suspected_proxy", "")).strip().lower() in ("true", "1", "yes"),
            ))
    return labels


def main():
    weather = load_monthly(WEATHER_CSV, [c for _, c, _ in WEATHER_REQUIRED])
    satellite = load_monthly(SATELLITE_CSV, [c for _, c, _ in SAT_FEATURES])
    labels = load_yield()

    have_sat = bool(satellite)
    if not have_sat:
        print("NOTE: satellite_laguna_monthly.csv not found - satellite columns "
              "will be blank. Run fetch_satellite_cdse.py, then re-run this.\n")

    long_rows, wide_rows, skipped = [], [], []

    for muni, year, season, yld, proxy in labels:
        months = SEASON_MONTHS.get(season)
        if not months:
            skipped.append((muni, year, season, "unknown season"))
            continue

        # Weather is required and complete; bail on the sample if any step is missing.
        steps, missing = [], []
        for month in months:
            wx = weather.get((fold(muni), year, month))
            if wx is None or any(wx.get(c) is None for _, c, _ in WEATHER_REQUIRED):
                missing.append(month)
                continue
            sx = satellite.get((fold(muni), year, month), {})
            step_vals = {}
            for source, col, short in FEATURES:
                step_vals[short] = (wx if source == "weather" else sx).get(col)
            steps.append((month, step_vals))
        if len(steps) != STEPS:
            skipped.append((muni, year, season, f"missing weather months {missing}"))
            continue

        # Long rows
        for step_i, (month, vals) in enumerate(steps, 1):
            row = {"municipality": muni, "year": year, "season": season,
                   "seq_step": step_i, "month": month}
            for _, _, short in FEATURES:
                row[short] = vals[short]
            row["suspected_proxy"] = proxy
            row["yield_mt_ha"] = yld
            long_rows.append(row)

        # Wide row
        wide = {"municipality": muni, "year": year, "season": season}
        for step_i, (_, vals) in enumerate(steps, 1):
            for _, _, short in FEATURES:
                wide[f"{short}_m{step_i}"] = vals[short]
        wide["ndvi_present"] = sum(1 for _, v in steps if v.get("ndvi") is not None)
        wide["s1_present"] = sum(1 for _, v in steps if v.get("vv") is not None)
        wide["suspected_proxy"] = proxy
        wide["yield_mt_ha"] = yld
        wide_rows.append(wide)

    # --- write LONG -----------------------------------------------------------
    long_fields = (["municipality", "year", "season", "seq_step", "month"]
                   + [short for _, _, short in FEATURES]
                   + ["suspected_proxy", "yield_mt_ha"])
    with open(OUT_LONG, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=long_fields)
        w.writeheader()
        w.writerows(long_rows)

    # --- write WIDE -----------------------------------------------------------
    wide_fields = ["municipality", "year", "season"]
    for _, _, short in FEATURES:
        wide_fields += [f"{short}_m{i}" for i in range(1, STEPS + 1)]
    wide_fields += ["ndvi_present", "s1_present", "suspected_proxy", "yield_mt_ha"]
    with open(OUT_WIDE, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=wide_fields)
        w.writeheader()
        w.writerows(wide_rows)

    # --- report ---------------------------------------------------------------
    print(f"labels read:        {len(labels)}")
    print(f"training samples:   {len(wide_rows)}  ({len(long_rows)} long rows)")
    print(f"  of which proxy:   {sum(1 for r in wide_rows if r['suspected_proxy'])}")
    if have_sat:
        full_ndvi = sum(1 for r in wide_rows if r["ndvi_present"] == STEPS)
        full_s1 = sum(1 for r in wide_rows if r["s1_present"] == STEPS)
        any_ndvi = sum(1 for r in wide_rows if r["ndvi_present"] > 0)
        print(f"  full NDVI (6/6):  {full_ndvi}   any NDVI: {any_ndvi}")
        print(f"  full S1   (6/6):  {full_s1}")
    else:
        print("  satellite:        (none - weather-only rows)")
    print(f"skipped:            {len(skipped)}")
    for muni, year, season, why in skipped:
        print(f"    - {muni} {year} {season}: {why}")
    print(f"\nwrote {OUT_LONG}")
    print(f"wrote {OUT_WIDE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
