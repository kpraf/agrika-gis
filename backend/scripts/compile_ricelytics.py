"""
compile_ricelytics.py
=====================

Combine many per-semester Ricelytics exports ("Average Yield of Palay ... by
Municipality") into one tidy dataset for LAGUNA only.

Why this exists
---------------
Ricelytics lets you export average palay yield (mt/ha) by municipality, but:
  * each export is a single semester (no year ranges),
  * every export is the whole Philippines (1,300+ municipalities), and
  * the semester is only in the file *name*, not in the data.

This script reads a folder of those exports, keeps only Laguna's
municipalities, tags each row with its year + semester (parsed from the file
name), normalises the municipality name so it matches the names already in the
PostGIS `municipalities` table, and writes:

  * <output>.csv        - long format, one row per municipality-year-semester
                          (ready to load into the DB once yield storage is
                          decided), and
  * <output>.wide.csv   - a municipality x (year-semester) pivot for eyeballing
                          in Excel / dropping into the thesis appendix.

It also prints a validation report: coverage per file, municipalities missing
from each export, and suspected "proxy" values (identical yields shared by
several municipalities in the same file - Ricelytics appears to backfill
low-rice cities this way, so those cells deserve a caveat in the data chapter).

Usage
-----
    python backend/scripts/compile_ricelytics.py \
        --input  "C:/Users/kpraf/Downloads" \
        --output "backend/db/ricelytics_laguna_yield"

Both .xlsx and .csv exports are supported. Only files whose name looks like a
Ricelytics municipality yield export are read; anything else in the folder is
ignored.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

import pandas as pd

# --- Season convention -------------------------------------------------------
# Philippine palay cropping: Semester 1 (Jan-Jun harvest) is the DRY-season
# crop, Semester 2 (Jul-Dec) the WET-season crop. This matches the PRiSM
# province series where Sem 1 yields consistently exceed Sem 2. If your adviser
# defines the mapping differently, flip it here.
SEMESTER_TO_SEASON = {1: "Dry", 2: "Wet"}

# Only read files that look like the Ricelytics municipality yield export.
FILE_GLOBS = ["*Average Yield of Palay*by Municipality*.xlsx",
              "*Average Yield of Palay*by Municipality*.csv"]

# Pull "2019" and "1" out of "2019 Semester 1 Average Yield ...".
YEAR_SEM_RE = re.compile(r"(\d{4})\s+Semester\s+([12])", re.IGNORECASE)

PROVINCE = "Laguna"

# Columns as they appear in the export (header is on the 3rd row).
COL_PROVINCE = "Province Name"
COL_LOCATION = "Location Name"
COL_YIELD = "Average Yield"
COL_ECOSYSTEM = "Ecosystem"
COL_YEAR = "Year"

HERE = os.path.dirname(os.path.abspath(__file__))
GEOJSON = os.path.join(HERE, "..", "db", "geojson", "Laguna_Municipalities.geojson")


def norm(s: str) -> str:
    """Fold to plain ASCII lower-case for matching (Bi\u00f1an -> binan)."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.strip().lower().split())


def load_canonical_names() -> dict[str, str]:
    """norm(name) -> canonical municipality name, from the boundary GeoJSON."""
    with open(GEOJSON, encoding="utf-8") as fh:
        fc = json.load(fh)
    return {norm(f["properties"]["name"]): f["properties"]["name"] for f in fc["features"]}


def parse_year_semester(path: str) -> tuple[int, int] | tuple[None, None]:
    m = YEAR_SEM_RE.search(os.path.basename(path))
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def read_export(path: str) -> pd.DataFrame:
    """Read one export, header on row index 2 (the 3rd row)."""
    if path.lower().endswith(".csv"):
        return pd.read_csv(path, header=2)
    return pd.read_excel(path, header=2)


def find_files(folder: str) -> list[str]:
    found: list[str] = []
    for pat in FILE_GLOBS:
        found.extend(glob.glob(os.path.join(folder, pat)))
    return sorted(set(found))


def main() -> int:
    ap = argparse.ArgumentParser(description="Combine Ricelytics municipality yield exports for Laguna.")
    ap.add_argument("--input", "-i", required=True, help="Folder containing the Ricelytics export files.")
    ap.add_argument("--output", "-o", default="ricelytics_laguna_yield",
                    help="Output path prefix (a .csv and a .wide.csv are written). Default: ./ricelytics_laguna_yield")
    args = ap.parse_args()

    canonical = load_canonical_names()
    all_canon_names = sorted(set(canonical.values()))

    files = find_files(args.input)
    if not files:
        print(f"No Ricelytics export files found in: {args.input}", file=sys.stderr)
        print(f"(looking for: {', '.join(FILE_GLOBS)})", file=sys.stderr)
        return 1

    rows: list[dict] = []
    report: list[str] = []
    unmatched_names: set[str] = set()

    print(f"Found {len(files)} export file(s) in {args.input}\n")

    for path in files:
        fname = os.path.basename(path)
        year, sem = parse_year_semester(path)
        if year is None:
            report.append(f"SKIP  {fname}: could not read year/semester from the file name.")
            continue

        try:
            df = read_export(path)
        except Exception as exc:  # noqa: BLE001 - report and move on
            report.append(f"SKIP  {fname}: could not read ({exc}).")
            continue

        df.columns = [str(c).strip() for c in df.columns]
        if COL_PROVINCE not in df.columns or COL_LOCATION not in df.columns or COL_YIELD not in df.columns:
            report.append(f"SKIP  {fname}: unexpected columns {list(df.columns)}.")
            continue

        lag = df[df[COL_PROVINCE].astype(str).str.strip().str.lower() == PROVINCE.lower()].copy()

        # Flag suspected proxy values (same yield shared by >1 municipality here).
        value_counts = lag[COL_YIELD].round(5).value_counts()
        proxy_values = set(value_counts[value_counts > 1].index)

        seen_canon: set[str] = set()
        for _, r in lag.iterrows():
            loc = str(r[COL_LOCATION]).strip()
            key = norm(loc)
            canon = canonical.get(key)
            if canon is None:
                unmatched_names.add(loc)
                continue
            try:
                yld = float(r[COL_YIELD])
            except (TypeError, ValueError):
                continue
            seen_canon.add(canon)
            rows.append({
                "province": PROVINCE,
                "municipality": canon,
                "year": year,
                "semester": sem,
                "season_type": SEMESTER_TO_SEASON[sem],
                "yield_mt_ha": round(yld, 5),
                "ecosystem": str(r.get(COL_ECOSYSTEM, "")).strip(),
                "source_file": fname,
                "suspected_proxy": round(yld, 5) in proxy_values,
            })

        missing = [n for n in all_canon_names if n not in seen_canon]
        n_proxy = sum(1 for x in rows if x["source_file"] == fname and x["suspected_proxy"])
        report.append(
            f"OK    {year} S{sem}  {fname[:34]:34}  matched {len(seen_canon):2}/{len(all_canon_names)}"
            f"  proxy-flagged {n_proxy:2}  missing: {', '.join(missing) if missing else 'none'}"
        )

    if not rows:
        print("No Laguna rows were compiled. Check the input files.", file=sys.stderr)
        for line in report:
            print("  " + line, file=sys.stderr)
        return 1

    long_df = pd.DataFrame(rows).sort_values(["year", "semester", "municipality"]).reset_index(drop=True)

    out_long = args.output if args.output.lower().endswith(".csv") else args.output + ".csv"
    out_wide = os.path.splitext(out_long)[0] + ".wide.csv"
    os.makedirs(os.path.dirname(os.path.abspath(out_long)), exist_ok=True)
    long_df.to_csv(out_long, index=False)

    # Wide pivot: rows = municipality, cols = "YYYY S#".
    wide = long_df.copy()
    wide["period"] = wide["year"].astype(str) + " S" + wide["semester"].astype(str)
    pivot = wide.pivot_table(index="municipality", columns="period", values="yield_mt_ha", aggfunc="first")
    pivot.to_csv(out_wide)

    # --- Report ---------------------------------------------------------------
    print("Per-file summary")
    print("-" * 96)
    for line in report:
        print("  " + line)

    print("\nProvince roll-up (simple mean of municipalities; not area-weighted)")
    print("-" * 96)
    prov = (long_df.groupby(["year", "semester"])["yield_mt_ha"].mean().round(3))
    for (year, sem), val in prov.items():
        print(f"  {year} S{sem} ({SEMESTER_TO_SEASON[sem]}): {val} mt/ha  (compare to PRiSM province series)")

    if unmatched_names:
        print("\nWARNING - Laguna location names that did NOT match the DB (fix the normaliser):")
        for n in sorted(unmatched_names):
            print(f"  - {n!r}")

    print(f"\nWrote {len(long_df)} rows")
    print(f"  long : {out_long}")
    print(f"  wide : {out_wide}")
    print("\nNote: Ricelytics is yield-only (no area/production). San Pedro has no "
          "palay data and will be blank. 'suspected_proxy' flags cells to caveat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
