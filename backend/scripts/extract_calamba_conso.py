"""
extract_calamba_conso.py
========================

Convert the Calamba City Agricultural Services Dept. consolidated harvesting
workbook ("CALAMBA rice production per brgy 2020-2025.xlsx") into the tidy CSV
that load_barangay_yield.py expects. This is the REAL Calamba record and replaces
the earlier gen_calamba_placeholder.py output.

Workbook layout (single sheet "harvesting calamba conso"):
  - Row 2: one merged header per season, "DRY SEASON 2020" ... "WET SEASON 2025".
  - Row 3: under each season, three columns - Harvest Area (Ha.), Average Yield
    (MT./Ha.), Production (MT).
  - Rows 4+: one row per barangay, then a TOTAL row (ignored).

The office reports Banlic and Lecheria as two service areas each (A / B). They are
single barangays in the boundary data, so A + B are combined: area and production
are summed and yield = production / area. Blank cells mean no harvest was reported
and produce no row.

Requires: openpyxl.

Usage
    python backend/scripts/extract_calamba_conso.py \
        --excel "backend/data/CALAMBA rice production per brgy 2020-2025.xlsx"
"""
import argparse
import csv
import os
import re
import unicodedata
from collections import defaultdict

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.abspath(os.path.join(HERE, "..", "db"))

MUNI = "City of Calamba"
SEASON_RE = re.compile(r"(DRY|WET)\s+SEASON\s+(\d{4})", re.IGNORECASE)

# Workbook label (folded) -> barangay name as stored in the barangays table.
NAME_MAP = {
    "BANLIC A": "Banlic", "BANLIC B": "Banlic",
    "LECHERIA A": "Lecheria", "LECHERIA B": "Lecheria",
    "BARANGAY VII": "Barangay 7",
}


def fold(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


def canon(label):
    f = fold(label)
    if f in NAME_MAP:
        return NAME_MAP[f]
    if re.fullmatch(r"BA.?ADERO", f):  # the workbook's N-tilde does not survive the export
        return "Banadero"
    return f.title()


def num(v):
    return float(v) if isinstance(v, (int, float)) else None


def main():
    ap = argparse.ArgumentParser(description="Extract Calamba consolidated barangay yield to CSV.")
    ap.add_argument("--excel", required=True, help="The Calamba consolidated workbook (.xlsx)")
    ap.add_argument("--out", default=os.path.join(DB, "barangay_yield_city-of-calamba.csv"))
    args = ap.parse_args()

    ws = openpyxl.load_workbook(args.excel, data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    hdr = next(i for i, r in enumerate(rows) if any(SEASON_RE.search(str(v or "")) for v in r))

    # column index of each season's "Harvest Area" cell -> (year, season)
    seasons = {}
    for c, v in enumerate(rows[hdr]):
        m = SEASON_RE.search(str(v or ""))
        if m:
            seasons[c] = (int(m.group(2)), m.group(1).capitalize())

    totals = defaultdict(lambda: [0.0, 0.0])  # (barangay, year, season) -> [area, production]
    for r in rows[hdr + 2:]:
        label = r[0]
        if not label or fold(label) == "TOTAL":
            continue
        brgy = canon(label)
        for c, (year, season) in seasons.items():
            area, prod = num(r[c]), num(r[c + 2])
            if not area or prod is None:
                continue
            t = totals[(brgy, year, season)]
            t[0] += area
            t[1] += prod

    out = [
        [MUNI, b, y, s, round(a, 2), round(p, 2), round(p / a, 2)]
        for (b, y, s), (a, p) in totals.items()
    ]
    out.sort(key=lambda x: (x[1], x[2], x[3]))
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["municipality", "barangay", "year", "season", "area_ha", "production_mt", "yield_mt_ha"])
        w.writerows(out)

    brgys = sorted({o[1] for o in out})
    print(f"wrote {len(out)} rows for {len(brgys)} barangays -> {args.out}")
    print("  " + ", ".join(brgys))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
