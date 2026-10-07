"""
impute_cabuyao_barangay_yield.py
================================

ESTIMATE (not observe) Cabuyao barangay yields for the seasons whose City
Agriculture Office reports were unusable because the source repeated the same
figures: Dry 2022, Wet 2022 and Dry 2023.

These rows are model-based estimates. They are written to their OWN file so the
observed file (barangay_yield_city-of-cabuyao.csv) stays purely observed, and
they must never be used as training labels or scored as "observed" (the barangay
training rows and predictions are built from the observed file only).

Method (chosen by leave-one-season-out validation, printed on every run)
  yield(barangay, season) = season level + barangay effect
    season level    Santa Rosa's mean barangay yield that season, plus Cabuyao's
                    average offset from Santa Rosa over the seasons both cities
                    reported. The two adjoining cities move together: hiding each
                    known Cabuyao season and predicting it this way misses its
                    mean by 0.14 mt/ha on average, against 0.46 for a plain
                    dry/wet average and 0.56 for the municipal Ricelytics figure.
    barangay effect the barangay's average deviation from the Cabuyao season
                    mean, shrunk toward zero (n / (n + 4)). Barangay differences
                    are mostly not repeatable from season to season, so this term
                    is deliberately small.
  area_ha           the barangay's median harvested area in observed seasons of
                    the same type (dry areas are much smaller than wet areas).
  production_mt     area_ha x yield.

No random noise is added: the estimates are smoother than real reports would be.

Usage
    python backend/scripts/impute_cabuyao_barangay_yield.py
"""
import csv
import os
import statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.abspath(os.path.join(HERE, "..", "db"))
OBSERVED = os.path.join(DB, "barangay_yield_city-of-cabuyao.csv")
ANCHOR = os.path.join(DB, "barangay_yield_city-of-santa-rosa.csv")
OUT = os.path.join(DB, "barangay_yield_city-of-cabuyao_estimated.csv")

MUNI = "City of Cabuyao"
TARGETS = [(2022, "Dry"), (2022, "Wet"), (2023, "Dry")]
SHRINK = 4.0  # barangay effect = sum(deviations) / (n + SHRINK)


def read(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not (r.get("yield_mt_ha") or "").strip():
                continue
            rows.append({
                "barangay": r["barangay"], "key": (int(float(r["year"])), r["season"].strip().capitalize()),
                "area": float(r["area_ha"]) if (r.get("area_ha") or "").strip() else None,
                "yield": float(r["yield_mt_ha"]),
            })
    return rows


def season_means(rows):
    by = defaultdict(list)
    for r in rows:
        by[r["key"]].append(r["yield"])
    return {k: st.mean(v) for k, v in by.items()}


def fit(rows, anchor_mean):
    """(offset from the anchor city, {barangay: shrunk effect}) from observed rows."""
    means = season_means(rows)
    offset = st.mean(means[k] - anchor_mean[k] for k in means)
    devs = defaultdict(list)
    for r in rows:
        devs[r["barangay"]].append(r["yield"] - means[r["key"]])
    effect = {b: sum(d) / (len(d) + SHRINK) for b, d in devs.items()}
    return offset, effect


def validate(rows, anchor_mean):
    """Hide each observed season in turn and predict it from the rest."""
    means = season_means(rows)
    errs, level_errs = [], []
    for held in sorted(means):
        train = [r for r in rows if r["key"] != held]
        offset, effect = fit(train, anchor_mean)
        level = anchor_mean[held] + offset
        level_errs.append(abs(level - means[held]))
        errs += [abs(level + effect.get(r["barangay"], 0.0) - r["yield"]) for r in rows if r["key"] == held]
    return st.mean(errs), st.mean(level_errs), max(level_errs), len(errs)


def main():
    rows = read(OBSERVED)
    anchor_mean = season_means(read(ANCHOR))

    mae, level_mae, level_max, n = validate(rows, anchor_mean)
    print(f"leave-one-season-out on {n} observed barangay-seasons:")
    print(f"  season mean  : off by {level_mae:.2f} mt/ha on average (worst {level_max:.2f})")
    print(f"  per barangay : off by {mae:.2f} mt/ha on average")

    offset, effect = fit(rows, anchor_mean)
    areas = defaultdict(list)
    for r in rows:
        if r["area"] is not None:
            areas[(r["barangay"], r["key"][1])].append(r["area"])

    out = []
    for year, season in TARGETS:
        level = anchor_mean[(year, season)] + offset
        for b in sorted(effect):
            a = areas.get((b, season))
            if not a:
                continue  # never harvested in this season type
            area = round(st.median(a), 2)
            yld = round(level + effect[b], 2)
            out.append([MUNI, b, year, season, area, round(area * yld, 2), yld, "estimated"])
        print(f"  {year} {season}: season level {level:.2f} mt/ha "
              f"(Santa Rosa {anchor_mean[(year, season)]:.2f} {offset:+.2f})")

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["municipality", "barangay", "year", "season", "area_ha", "production_mt",
                    "yield_mt_ha", "basis"])
        w.writerows(out)
    print(f"wrote {len(out)} ESTIMATED rows -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
