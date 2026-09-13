"""
extract_barangay_yield.py
=========================

Extract barangay-level rice yield from an LGU "Planting and Harvesting" workbook
into a tidy CSV. Built for Santa Rosa; reusable for the other cities (Binan,
Cabuyao, Calamba) whose workbooks follow the same layout.

Workbook layout (per the Santa Rosa file):
  - One sheet per season-year, named like "WS 2023" / "DS2024"
    (WS = Wet Season, DS = Dry Season).
  - Harvesting sheets ("HARVESTING BY BARANGAY", row 2) hold per-period columns
    that alternate Area(Has) then Prodn(MT), split by seed type (CS/Hyb). We sum
    every Area(Has) column for total harvested area and every Prodn(MT) column for
    total production, then yield = production / area (mt/ha).
  - Planting-only sheets ("PLANTING BY BARANGAY", e.g. WS 2020) have no production
    and are skipped (no yield derivable).
  - Some sheets omit the row-5 header labels (e.g. WS 2023); there we fall back to
    the fixed alternating pattern (area on even columns from D, prodn on odd from E).

Output: one row per (barangay, year, season) for EVERY barangay of the target
municipality (from the DB). Barangays absent from the workbook, and season-years
with no harvest data, are written with blank area/production/yield ("no data").

Requires: openpyxl (pip install openpyxl), plus the app DB for the barangay list.

Usage
    python backend/scripts/extract_barangay_yield.py \
        --excel "path/to/Planting and Harvesting.xlsx" \
        --municipality "City of Santa Rosa"
"""
import argparse
import csv
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import openpyxl  # noqa: E402
from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "db"))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fold(s):
    """Normalise a barangay name for matching (diacritics/case/'Sta.'->'Santa')."""
    s = re.sub(r"\s+", " ", str(s).strip().lower()).replace(".", "").replace("sta ", "santa ")
    return re.sub(r"\s*(np|no planting|nh)$", "", s).strip()  # drop status suffixes


def parse_sheet_name(name):
    m = re.match(r"(WS|DS)\s*([0-9]{4})", name.strip())
    if not m:
        return None, None
    return ("Wet" if m.group(1) == "WS" else "Dry"), int(m.group(2))


def sheet_columns(ws):
    """Return (area_cols, prod_cols) for a harvesting sheet."""
    labels = {c: str(ws.cell(5, c).value).strip() for c in range(1, ws.max_column + 1)}
    prod_cols = [c for c, v in labels.items() if "prodn" in v.lower()]
    area_cols = [c for c, v in labels.items() if v == "Area(Has)"]
    if not prod_cols and not area_cols:  # unlabeled sheet (e.g. WS 2023)
        area_cols = list(range(4, ws.max_column + 1, 2))
        prod_cols = list(range(5, ws.max_column + 1, 2))
    return area_cols, prod_cols


def main():
    ap = argparse.ArgumentParser(description="Extract barangay yield from an LGU workbook.")
    ap.add_argument("--excel", required=True, help="Path to the Planting and Harvesting .xlsx")
    ap.add_argument("--municipality", required=True, help="e.g. 'City of Santa Rosa'")
    ap.add_argument("--out", help="Output CSV (default db/barangay_yield_<slug>.csv)")
    ap.add_argument("--exclude-years", default="2026",
                    help="Comma-separated years to skip (default 2026).")
    args = ap.parse_args()

    exclude = {int(y) for y in args.exclude_years.split(",") if y.strip()}

    app = create_app()
    with app.app_context():
        brgys = [
            r.barangay_name
            for r in db.session.execute(
                text("SELECT b.barangay_name FROM barangays b "
                     "JOIN municipalities m ON m.municipality_id = b.municipality_id "
                     "WHERE m.municipality_name = :m ORDER BY b.barangay_name"),
                {"m": args.municipality},
            )
        ]
    if not brgys:
        sys.exit(f"No barangays found for municipality {args.municipality!r} in the DB.")
    fold_to_name = {fold(b): b for b in brgys}

    wb = openpyxl.load_workbook(args.excel, data_only=True)
    data = {}          # (barangay, year, season) -> (area, prod, yield)
    season_years = set()
    unmatched = set()
    for name in wb.sheetnames:
        season, year = parse_sheet_name(name)
        if season is None or year in exclude:
            continue
        ws = wb[name]
        header = str(ws.cell(2, 1).value or ws.cell(3, 1).value or "").upper()
        if "HARVEST" not in header:
            continue  # planting-only sheet: no production
        area_cols, prod_cols = sheet_columns(ws)
        season_years.add((year, season))
        for r in range(6, ws.max_row + 1):
            b = ws.cell(r, 1).value
            if b is None:
                continue
            if str(b).strip().upper().startswith("TOTAL"):
                break
            our = fold_to_name.get(fold(b))
            if not our:
                unmatched.add(str(b).strip())
                continue
            area = sum(num(ws.cell(r, c).value) or 0 for c in area_cols)
            prod = sum(num(ws.cell(r, c).value) or 0 for c in prod_cols)
            yld = round(prod / area, 3) if area > 0 and prod > 0 else None
            data[(our, year, season)] = (round(area, 2) or None, round(prod, 2) or None, yld)

    # Full grid: every barangay x every harvest season-year.
    slug = re.sub(r"[^a-z0-9]+", "-", args.municipality.lower()).strip("-")
    out_path = args.out or os.path.join(DB_DIR, f"barangay_yield_{slug}.csv")
    rows = []
    for bg in brgys:
        for (yr, se) in sorted(season_years):
            a, p, y = data.get((bg, yr, se), (None, None, None))
            rows.append({"municipality": args.municipality, "barangay": bg, "year": yr,
                         "season": se, "area_ha": a, "production_mt": p, "yield_mt_ha": y})
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["municipality", "barangay", "year", "season",
                                           "area_ha", "production_mt", "yield_mt_ha"])
        w.writeheader()
        w.writerows(rows)

    filled = sum(1 for r in rows if r["yield_mt_ha"] is not None)
    ys = [r["yield_mt_ha"] for r in rows if r["yield_mt_ha"] is not None]
    print(f"{args.municipality}: {len(brgys)} barangays x {len(season_years)} season-years "
          f"= {len(rows)} rows; {filled} with yield.")
    if ys:
        print(f"  yield: min {min(ys)} max {max(ys)} avg {round(sum(ys)/len(ys),3)}")
    if unmatched:
        print(f"  WARNING unmatched workbook names (check spelling): {sorted(unmatched)}")
    print(f"  wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
