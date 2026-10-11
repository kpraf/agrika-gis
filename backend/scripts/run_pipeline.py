"""
run_pipeline.py
===============

Objective 3 orchestrator: run the data pipeline end to end from one command,
with per-stage logging, and record every run in the database (pipeline_runs).

Three modes
-----------
--incremental   What the weekly scheduled run does (.github/workflows/data-pipeline.yml).
                Fetches only a window of recent months - the month in progress
                plus the previous --lookback months (default 1), re-fetched in case
                late scenes or archive corrections arrived - upserts that window
                into the database, checks it, and predicts the latest season once
                its six months are complete.
(default)       Full rebuild: fetch whole years (--start/--end) into the CSVs,
                reload the database, rebuild the training set. Costly; by hand only.
--skip-fetch    With --incremental: load the CSV copies already in the repository
                instead of fetching (costs no Copernicus units), then verify and
                predict. Without it: reload and rebuild the training set from the CSVs.

Two levels (incremental mode, --levels)
---------------------------------------
municipality    all 30 cities and municipalities of Laguna.
barangay        only the barangays that have at least one REPORTED yield on record
                (a City Agriculture Office has reported a harvest there). The list is
                read from the database at the start of every run, so a barangay
                joins the schedule as soon as its first yield is imported.

Stages, incremental
   1. acquire weather              fetch_weather_openmeteo.py  (Open-Meteo)       [fetch]
   2. acquire satellite            fetch_satellite_cdse.py     (Copernicus/CDSE)  [fetch]
   3. select barangays             those with a reported yield, boundaries from PostGIS
   4. acquire barangay weather     same script, --level barangay                  [fetch]
   5. acquire barangay satellite   same script, --level barangay                  [fetch]
   6. ensure DB tables             add_feature_tables.py, add_barangay_feature_tables.py
   7. load window to DB            idempotent upsert, both levels
   8. update CSV copies            merge the window into the db/*.csv copies
   9. verify window                area-months present, values in physical range
  10. predict season               predict_season.py --auto (only when a season is complete)

Quota: the satellite stages spend Copernicus processing units (free tier:
30,000 a month). --max-pu caps the municipality fetch of one run (the barangay
fetch has its own small cap); what was actually spent is logged.

A fetch that returns only part of its data (exit code 2) does not stop the run:
what arrived is loaded, the run is recorded as "partial", and the next run
re-fetches the same window. Any other stage failure stops the pipeline unless
--continue-on-error is given.

The run is also summarised in db/pipeline_last_run.json and, on GitHub Actions,
in the job summary.

Usage
    python backend/scripts/run_pipeline.py --incremental
    python backend/scripts/run_pipeline.py --incremental --from-month 2025-12 --levels barangay
    python backend/scripts/run_pipeline.py --incremental --skip-fetch --from-month 2025-12
    python backend/scripts/run_pipeline.py                 # full rebuild (fetches years)
    python backend/scripts/run_pipeline.py --skip-fetch    # re-integrate + reload only
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, ".."))
DB_DIR = os.path.join(BACKEND, "db")
RUN_DIR = os.path.join(DB_DIR, "_run")
SUMMARY_PATH = os.path.join(DB_DIR, "pipeline_last_run.json")
WEATHER_CSV = os.path.join(DB_DIR, "weather_laguna_monthly.csv")
SATELLITE_CSV = os.path.join(DB_DIR, "satellite_laguna_monthly.csv")
WEATHER_WINDOW = os.path.join(RUN_DIR, "weather_window.csv")
SATELLITE_WINDOW = os.path.join(RUN_DIR, "satellite_window.csv")
BRGY_GEOJSON = os.path.join(RUN_DIR, "barangays_scheduled.geojson")
BRGY_WEATHER_WINDOW = os.path.join(RUN_DIR, "weather_barangay_window.csv")
BRGY_SATELLITE_WINDOW = os.path.join(RUN_DIR, "satellite_barangay_window.csv")
BRGY_MAX_PU = 500

# The per-city barangay CSV copies kept in the repository: (weather, satellite, cities covered).
BRGY_CSV_SETS = [
    ("weather_barangay_sr_cabuyao_monthly.csv", "satellite_barangay_sr_cabuyao_monthly.csv",
     ["City of Santa Rosa", "City of Cabuyao"]),
    ("weather_barangay_binan_monthly.csv", "satellite_barangay_binan_monthly.csv", ["City of Biñan"]),
    ("weather_barangay_calamba_monthly.csv", "satellite_barangay_calamba_monthly.csv", ["City of Calamba"]),
]

sys.path.insert(0, BACKEND)

# Physical ranges for the per-run integrity check (same bounds as pipeline_reliability.py).
RANGES = {
    "weather": {"rainfall_mm": (0, 3000), "temp_mean_c": (10, 40), "humidity_mean_pct": (0, 100)},
    "satellite": {"ndvi_mean": (-1, 1), "ndwi_mean": (-1, 1), "vv_mean": (-40, 5), "vh_mean": (-40, 5)},
}
TABLES = {
    "municipality": {"weather": "weather_monthly", "satellite": "satellite_monthly"},
    "barangay": {"weather": "weather_monthly_barangay", "satellite": "satellite_monthly_barangay"},
}


# --- months -------------------------------------------------------------------
def month_add(ym, n):
    y, m = ym
    i = y * 12 + (m - 1) + n
    return i // 12, i % 12 + 1


def month_str(ym):
    return f"{ym[0]}-{ym[1]:02d}"


def parse_month(s):
    try:
        y, m = (int(p) for p in s.split("-"))
        if not 1 <= m <= 12:
            raise ValueError
        return y, m
    except ValueError:
        sys.exit(f"ERROR: month must look like 2026-08 (got {s!r}).")


def months_between(a, b):
    out = []
    while a <= b:
        out.append(a)
        a = month_add(a, 1)
    return out


# --- stages -------------------------------------------------------------------
def run_script(script, argv):
    """Run one stage as a subprocess; return its exit code."""
    cmd = [sys.executable, os.path.join(HERE, script), *argv]
    print(f"$ {' '.join(cmd[1:])}\n", flush=True)
    return subprocess.run(cmd, cwd=BACKEND).returncode


def read_csv(path):
    if not os.path.exists(path):
        return [], []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames, list(reader)


def csv_rows(path):
    return len(read_csv(path)[1])


def write_merged(main_path, window_rows):
    """Fold rows into a CSV copy: the same area-year-month is replaced, the rest kept."""
    fields, main = read_csv(main_path)
    if not fields:
        return 0, 0
    name = fields[0]
    key = lambda r: (r[name], int(r["year"]), int(r["month"]))  # noqa: E731
    merged = {key(r): r for r in main}
    new = sum(1 for r in window_rows if key(r) not in merged)
    merged.update({key(r): {f: r.get(f, "") for f in fields} for r in window_rows})
    with open(main_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(merged[k] for k in sorted(merged))
    return len(window_rows), new


def merge_csv(main_path, window_path):
    if not os.path.exists(window_path):
        return "no window file"
    n, new = write_merged(main_path, read_csv(window_path)[1])
    return f"{n} rows merged ({new} new)"


def fold(s):
    """Same name folding as load_barangay_feature_tables.py."""
    return re.sub(r"\s+", " ", str(s).strip().lower()).replace(".", "").replace("sta ", "santa ")


def merge_barangay_csvs(window_path, kind, selected):
    """Fold a barangay window ('<id>:<name>' rows) into the per-city CSV copies (keyed by name)."""
    rows = read_csv(window_path)[1]
    if not rows:
        return "no window file"
    total = new = unfiled = 0
    for weather_csv, satellite_csv, cities in BRGY_CSV_SETS:
        path = os.path.join(DB_DIR, weather_csv if kind == "weather" else satellite_csv)
        fields, existing = read_csv(path)
        if not fields:
            continue
        spelling = {fold(r[fields[0]]): r[fields[0]] for r in existing}   # keep the file's own spelling
        mine = []
        for r in rows:
            bid = int(str(r["barangay"]).split(":", 1)[0])
            city, name = selected.get(bid, (None, None))
            if city in cities:
                mine.append({**r, fields[0]: spelling.get(fold(name), name)})
        n, k = write_merged(path, mine)
        total, new = total + n, new + k
    filed = {c for _, _, cities in BRGY_CSV_SETS for c in cities}
    unfiled = sum(1 for r in rows if selected.get(int(str(r["barangay"]).split(":", 1)[0]), (None,))[0] not in filed)
    return (f"{total} rows merged ({new} new)"
            + (f"; {unfiled} rows of cities without a CSV copy stay in the database only" if unfiled else ""))


# --- run log (pipeline_runs) --------------------------------------------------
class RunLog:
    """One row in pipeline_runs for this run. Never lets a logging problem stop the run."""

    def __init__(self, mode, window):
        self.run_id = None
        self.app = None
        self.fields = {}
        event = os.environ.get("GITHUB_EVENT_NAME", "")
        self.triggered_by = {"schedule": "schedule", "workflow_dispatch": "manual"}.get(event, "local")
        run_ref = None
        if os.environ.get("GITHUB_RUN_ID"):
            run_ref = (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
                       f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ['GITHUB_RUN_ID']}")
        try:
            from sqlalchemy import text
            from app import app as flask_app
            from extensions import db
            import audit

            self.app, self.db, self.text = flask_app, db, text
            with self.app.app_context():
                audit.ensure_pipeline_runs()
                raw = db.session.connection().connection.driver_connection
                encrypted = bool(raw.pgconn.ssl_in_use)
                self.run_id = db.session.execute(text(
                    "INSERT INTO pipeline_runs (triggered_by, mode, window_from, window_to, "
                    "db_encrypted, run_ref) VALUES (:t, :m, :wf, :wt, :enc, :ref) RETURNING run_id"),
                    {"t": self.triggered_by, "m": mode,
                     "wf": month_str(window[0]) if window else None,
                     "wt": month_str(window[-1]) if window else None,
                     "enc": encrypted, "ref": run_ref}).scalar()
                db.session.commit()
            print(f"run #{self.run_id} logged in pipeline_runs | started by: {self.triggered_by} | "
                  f"database connection encrypted: {encrypted}")
        except Exception as e:  # noqa: BLE001
            print(f"WARNING: could not open the run log ({type(e).__name__}: {e}). "
                  "Continuing without it.", file=sys.stderr)

    def _count(self, table):
        exists = self.db.session.execute(self.text("SELECT to_regclass(:t)"), {"t": table}).scalar()
        return self.db.session.execute(self.text(f"SELECT COUNT(*) FROM {table}")).scalar() if exists else 0

    def counts(self):
        """Row counts of the tables a run adds to (None if the DB is unreachable)."""
        if self.app is None:
            return None
        try:
            with self.app.app_context():
                return {t: self._count(t) for t in (
                    "weather_monthly", "satellite_monthly", "municipality_predictions",
                    "weather_monthly_barangay", "satellite_monthly_barangay", "barangay_predictions")}
        except Exception:  # noqa: BLE001
            return None

    def select_barangays(self, path):
        """Write the boundaries of every barangay with a reported yield; return {id: (city, name)}."""
        with self.app.app_context():
            rows = self.db.session.execute(self.text(
                "SELECT b.barangay_id, b.barangay_name, m.municipality_name, "
                "ST_AsGeoJSON(b.boundary_geometry) AS geometry "
                "FROM barangays b JOIN municipalities m ON m.municipality_id = b.municipality_id "
                "WHERE b.boundary_geometry IS NOT NULL AND EXISTS ("
                "  SELECT 1 FROM barangay_yield y WHERE y.barangay_id = b.barangay_id "
                "  AND y.yield_mt_ha IS NOT NULL AND NOT COALESCE(y.source ILIKE 'estimated%', FALSE)) "
                "ORDER BY m.municipality_name, b.barangay_name")).all()
        features = [{"type": "Feature",
                     # "<id>:<name>" - unique (barangay names repeat across cities) and readable in the logs
                     "properties": {"name": f"{r.barangay_id}:{r.barangay_name}", "municipality": r.municipality_name},
                     "geometry": json.loads(r.geometry)} for r in rows]
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"type": "FeatureCollection", "features": features}, fh)
        return {r.barangay_id: (r.municipality_name, r.barangay_name) for r in rows}

    def verify(self, level, window, ids=None):
        """(expected area-months, weather found, satellite found, values out of range) for the window."""
        id_col = "municipality_id" if level == "municipality" else "barangay_id"
        with self.app.app_context():
            q = lambda sql, **p: self.db.session.execute(self.text(sql), p).scalar()  # noqa: E731
            keys = [y * 100 + m for y, m in window]
            where, params = "(year * 100 + month) = ANY(:keys)", {"keys": keys}
            if ids is None:
                n_areas = q("SELECT COUNT(*) FROM municipalities")
            else:
                n_areas = len(ids)
                where += f" AND {id_col} = ANY(:ids)"
                params["ids"] = list(ids)
            found, violations = {}, 0
            for kind, table in TABLES[level].items():
                found[kind] = q(f"SELECT COUNT(*) FROM {table} WHERE {where}", **params)
                for col, (lo, hi) in RANGES[kind].items():
                    violations += q(
                        f"SELECT COUNT(*) FROM {table} WHERE {where} AND {col} IS NOT NULL AND "
                        f"({col} < :lo OR {col} > :hi OR {col} = 'NaN')", lo=lo, hi=hi, **params)
        return n_areas * len(window), found["weather"], found["satellite"], violations

    def finish(self, status, stages, notes):
        if self.run_id is None:
            return
        try:
            with self.app.app_context():
                sets = ", ".join(f"{k} = :{k}" for k in self.fields)
                self.db.session.execute(self.text(
                    "UPDATE pipeline_runs SET finished_at = now(), status = :status, "
                    "stages = CAST(:stages AS JSONB), notes = :notes"
                    + (", " + sets if sets else "") + " WHERE run_id = :id"),
                    {"status": status, "stages": json.dumps(stages), "notes": notes or None,
                     "id": self.run_id, **self.fields})
                self.db.session.commit()
        except Exception as e:  # noqa: BLE001
            print(f"WARNING: could not complete the run log ({type(e).__name__}: {e}).", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Run the AgriKA-GIS data pipeline end to end.")
    ap.add_argument("--incremental", action="store_true",
                    help="Fetch and load only a window of recent months (the scheduled run).")
    ap.add_argument("--from-month", metavar="YYYY-MM",
                    help="Incremental: first month of the window (default: current month minus --lookback).")
    ap.add_argument("--to-month", metavar="YYYY-MM",
                    help="Incremental: last month of the window (default: the current month).")
    ap.add_argument("--lookback", type=int, default=1,
                    help="Incremental: how many finished months to re-fetch besides the current one (default 1).")
    ap.add_argument("--levels", default="municipality,barangay",
                    help="Incremental: municipality, barangay, or both (default).")
    ap.add_argument("--max-pu", type=float, default=3000,
                    help="Incremental: stop the municipality satellite fetch after this many Copernicus "
                         "processing units (default 3000; the free tier allows 30,000 a month).")
    ap.add_argument("--skip-predict", action="store_true", help="Incremental: do not run the prediction stage.")
    ap.add_argument("--start", type=int, default=2018, help="Full rebuild: first year.")
    ap.add_argument("--end", type=int, default=2025, help="Full rebuild: last year.")
    ap.add_argument("--skip-fetch", action="store_true",
                    help="Skip the API stages. Incremental: load the CSV copies in the repository instead.")
    ap.add_argument("--continue-on-error", action="store_true",
                    help="Run every stage even if one fails (default: stop on first failure).")
    args = ap.parse_args()
    levels = [x.strip() for x in args.levels.split(",") if x.strip()]
    if not levels or set(levels) - {"municipality", "barangay"}:
        sys.exit("ERROR: --levels takes municipality, barangay, or both.")
    do_muni, do_brgy = "municipality" in levels, "barangay" in levels

    now = datetime.now(timezone.utc)
    this_month = (now.year, now.month)
    window = []
    if args.incremental:
        if args.lookback < 1:
            sys.exit("ERROR: --lookback must be at least 1 (the weather archive lags about five days, "
                     "so in the first week the current month has no weather yet).")
        w_from = parse_month(args.from_month) if args.from_month else month_add(this_month, -args.lookback)
        w_to = parse_month(args.to_month) if args.to_month else this_month
        if w_from > w_to or w_from > this_month:
            sys.exit("ERROR: the window is empty or in the future.")
        window = months_between(w_from, min(w_to, this_month))
    mode = "incremental" if args.incremental else ("reload" if args.skip_fetch else "full")

    started = now.isoformat(timespec="seconds")
    print(f"AgriKA-GIS pipeline | started {started} | mode: {mode}"
          + (f" | window {month_str(window[0])} .. {month_str(window[-1])} ({len(window)} months)"
             f" | levels: {', '.join(levels)}" + (" | no fetch (CSV copies)" if args.skip_fetch else "")
             if window else f" | {args.start}-{args.end}"))
    log = RunLog(mode, window)
    selected = {}        # barangay_id -> (city, name), filled by the "select barangays" stage

    # (name, callable returning (status, detail)); is_fetch marks the API stages.
    def script_stage(script, argv, partial_ok=False):
        def run():
            code = run_script(script, argv)
            if code == 0:
                return "ok", ""
            if partial_ok and code == 2:
                return "partial", "some areas failed; what arrived was kept"
            return "failed", f"exit {code}"
        return run

    def scripts_stage(calls):
        """Several scripts as one stage; the first failure fails the stage."""
        def run():
            for script, argv in calls:
                code = run_script(script, argv)
                if code != 0:
                    return "failed", f"{script} exit {code}"
            return "ok", ""
        return run

    if args.incremental:
        os.makedirs(RUN_DIR, exist_ok=True)
        windows = (WEATHER_WINDOW, SATELLITE_WINDOW, BRGY_WEATHER_WINDOW, BRGY_SATELLITE_WINDOW)
        for stale in (*windows, *(w + ".meta.json" for w in windows), BRGY_GEOJSON):
            if os.path.exists(stale):   # never load a previous run's leftovers
                os.remove(stale)
        win = ["--from-month", month_str(window[0]), "--to-month", month_str(window[-1])]

        def select_barangays():
            if log.app is None:
                return "failed", "no database connection"
            selected.update(log.select_barangays(BRGY_GEOJSON))
            log.fields["barangays"] = len(selected)
            if not selected:
                return "failed", "no barangay has a reported yield on record"
            by_city = {}
            for city, _ in selected.values():
                by_city[city] = by_city.get(city, 0) + 1
            return "ok", (f"{len(selected)} barangays with a reported yield: "
                          + ", ".join(f"{c} {n}" for c, n in sorted(by_city.items())))

        def load_window():
            calls = []
            if do_muni:
                if args.skip_fetch:
                    calls.append(("load_feature_tables.py", []))
                else:
                    argv = []
                    if os.path.exists(WEATHER_WINDOW):
                        argv += ["--weather-csv", WEATHER_WINDOW]
                    if os.path.exists(SATELLITE_WINDOW):
                        argv += ["--satellite-csv", SATELLITE_WINDOW]
                    if len(argv) == 2:   # only one source arrived: load just that one
                        argv += ["--only", "weather" if "--weather-csv" in argv else "satellite"]
                    if argv:
                        calls.append(("load_feature_tables.py", argv))
            if do_brgy:
                if args.skip_fetch:
                    for weather_csv, satellite_csv, cities in BRGY_CSV_SETS:
                        calls.append(("load_barangay_feature_tables.py",
                                      ["--weather", os.path.join(DB_DIR, weather_csv),
                                       "--satellite", os.path.join(DB_DIR, satellite_csv),
                                       "--municipalities", ",".join(cities)]))
                else:
                    argv = ["--by-id"]
                    if os.path.exists(BRGY_WEATHER_WINDOW):
                        argv += ["--weather", BRGY_WEATHER_WINDOW]
                    if os.path.exists(BRGY_SATELLITE_WINDOW):
                        argv += ["--satellite", BRGY_SATELLITE_WINDOW]
                    if len(argv) > 1:
                        calls.append(("load_barangay_feature_tables.py", argv))
            if not calls:
                return "failed", "nothing was fetched"
            return scripts_stage(calls)()

        def update_csvs():
            parts = []
            if do_muni:
                parts.append(f"weather: {merge_csv(WEATHER_CSV, WEATHER_WINDOW)}; "
                             f"satellite: {merge_csv(SATELLITE_CSV, SATELLITE_WINDOW)}")
            if do_brgy:
                parts.append(f"barangay weather: {merge_barangay_csvs(BRGY_WEATHER_WINDOW, 'weather', selected)}; "
                             f"barangay satellite: {merge_barangay_csvs(BRGY_SATELLITE_WINDOW, 'satellite', selected)}")
            return "ok", "; ".join(parts)

        def verify():
            parts, bad = [], 0
            if do_muni:
                expected, weather, sat, v = log.verify("municipality", window)
                log.fields.update(cells_expected=expected, weather_cells=weather, satellite_cells=sat)
                parts.append(f"municipality: weather {weather}/{expected} area-months, satellite {sat}/{expected}")
                bad += v
            if do_brgy and selected:
                expected, weather, sat, v = log.verify("barangay", window, ids=selected)
                log.fields.update(barangay_cells_expected=2 * expected, barangay_cells=weather + sat)
                parts.append(f"barangay: weather {weather}/{expected}, satellite {sat}/{expected}")
                bad += v
            log.fields["integrity_violations"] = bad
            parts.append(f"{bad} values out of range")
            return ("ok" if bad == 0 else "failed"), "; ".join(parts)

        stages = []
        if do_muni:
            stages += [
                ("acquire weather", script_stage("fetch_weather_openmeteo.py",
                                                 [*win, "--out", WEATHER_WINDOW, "--sleep", "1.5"], True), True),
                ("acquire satellite", script_stage("fetch_satellite_cdse.py",
                                                   [*win, "--out", SATELLITE_WINDOW,
                                                    "--max-pu", str(args.max_pu)], True), True),
            ]
        if do_brgy:
            brgy = ["--level", "barangay", "--geojson", BRGY_GEOJSON, *win]
            stages += [
                ("select barangays", select_barangays, False),
                ("acquire barangay weather", script_stage("fetch_weather_openmeteo.py",
                                                          [*brgy, "--out", BRGY_WEATHER_WINDOW,
                                                           "--sleep", "1.5"], True), True),
                ("acquire barangay satellite", script_stage("fetch_satellite_cdse.py",
                                                            [*brgy, "--out", BRGY_SATELLITE_WINDOW,
                                                             "--max-pu", str(BRGY_MAX_PU)], True), True),
            ]
        ensure = [("add_feature_tables.py", [])] + ([("add_barangay_feature_tables.py", [])] if do_brgy else [])
        stages += [
            ("ensure DB tables", scripts_stage(ensure), False),
            ("load window to DB", load_window, False),
        ]
        if not args.skip_fetch:
            stages.append(("update CSV copies", update_csvs, False))
        stages.append(("verify window", verify, False))
        if not args.skip_predict:
            stages.append(("predict season",
                           script_stage("predict_season.py", ["--auto", "--levels", ",".join(levels)]), False))
    else:
        years = ["--start", str(args.start), "--end", str(args.end)]
        stages = [
            ("acquire weather", script_stage("fetch_weather_openmeteo.py", [*years, "--sleep", "1.5"], True), True),
            ("acquire satellite", script_stage("fetch_satellite_cdse.py", years, True), True),
            ("ensure DB tables", script_stage("add_feature_tables.py", []), False),
            ("load features to DB", script_stage("load_feature_tables.py", []), False),
            ("build training set", script_stage("build_training_rows.py", []), False),
        ]

    before = log.counts()
    summary = {"started": started, "mode": mode, "triggered_by": log.triggered_by,
               "window": [month_str(m) for m in window], "levels": levels if window else [], "stages": []}
    overall = "ok"
    for name, fn, is_fetch in stages:
        if is_fetch and args.skip_fetch:
            print(f"\n{(' SKIPPED: %s ' % name).center(70, '=')}")
            summary["stages"].append({"stage": name, "status": "skipped", "seconds": 0})
            continue
        print("\n" + f" STAGE: {name} ".center(70, "="), flush=True)
        t0 = time.time()
        try:
            status, detail = fn()
        except Exception as e:  # noqa: BLE001
            status, detail = "failed", f"{type(e).__name__}: {e}"
        secs = round(time.time() - t0, 1)
        print(f"\n-> {name}: {status.upper()} in {secs}s" + (f" ({detail})" if detail else ""), flush=True)
        entry = {"stage": name, "status": status, "seconds": secs}
        if detail:
            entry["detail"] = detail
        summary["stages"].append(entry)
        if status == "partial" and overall == "ok":
            overall = "partial"
        if status == "failed":
            overall = "failed"
            if not args.continue_on_error:
                print(f"\nPipeline stopped: '{name}' failed. "
                      f"(use --continue-on-error to run remaining stages)")
                break

    # What the run changed, from the tables themselves.
    after = log.counts()
    notes = []
    if before and after:
        diff = {t: after[t] - before[t] for t in after}
        loaded = any(s["stage"].startswith("load") and s["status"] == "ok" for s in summary["stages"])
        fetched = args.incremental and not args.skip_fetch
        if do_muni or not args.incremental:
            w_file = csv_rows(WEATHER_WINDOW if fetched else WEATHER_CSV) if loaded else 0
            s_file = csv_rows(SATELLITE_WINDOW if fetched else SATELLITE_CSV) if loaded else 0
            log.fields.update(
                weather_rows_new=diff["weather_monthly"],
                weather_rows_refreshed=max(w_file - diff["weather_monthly"], 0),
                satellite_rows_new=diff["satellite_monthly"],
                satellite_rows_refreshed=max(s_file - diff["satellite_monthly"], 0),
                predictions_new=diff["municipality_predictions"])
        if args.incremental and do_brgy:
            b_new = diff["weather_monthly_barangay"] + diff["satellite_monthly_barangay"]
            if fetched:
                b_file = (csv_rows(BRGY_WEATHER_WINDOW) + csv_rows(BRGY_SATELLITE_WINDOW)) if loaded else 0
            else:
                b_file = sum(csv_rows(os.path.join(DB_DIR, f)) for w, s, _ in BRGY_CSV_SETS
                             for f in (w, s)) if loaded else 0
            log.fields.update(barangay_rows_new=b_new, barangay_rows_refreshed=max(b_file - b_new, 0),
                              barangay_predictions_new=diff["barangay_predictions"])
    spent = None
    for meta_path, label in ((SATELLITE_WINDOW + ".meta.json", "satellite"),
                             (BRGY_SATELLITE_WINDOW + ".meta.json", "barangay satellite")):
        if args.incremental and os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as fh:
                meta = json.load(fh)
            spent = (spent or 0) + (meta.get("processing_units") or 0)
            if meta.get("areas_failed"):
                notes.append(f"{label}: {meta['areas_failed']} of {meta['areas']} areas not fetched")
    if spent is not None:
        log.fields["processing_units"] = round(spent, 1)
    if args.incremental and args.skip_fetch:
        notes.append("no fetch: loaded the CSV copies in the repository")
    if args.incremental and len(levels) == 1:
        notes.append(f"{levels[0]} level only")
    for s in summary["stages"]:
        if s["status"] in ("failed", "partial"):
            notes.append(f"{s['stage']}: {s['status']}" + (f" ({s['detail']})" if s.get("detail") else ""))
    log.finish(overall, summary["stages"], "; ".join(notes))

    summary["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary["overall"] = overall
    summary["run_id"] = log.run_id
    summary.update(log.fields)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    # Final report
    print("\n" + " PIPELINE SUMMARY ".center(70, "="))
    for s in summary["stages"]:
        print(f"  {s['stage']:<27} {s['status']:<8} {s['seconds']:>6}s  {s.get('detail', '')}")
    for k, v in log.fields.items():
        print(f"  {k:<26} {v}")
    print(f"\noverall: {overall.upper()}  |  summary -> {SUMMARY_PATH}")

    gh = os.environ.get("GITHUB_STEP_SUMMARY")
    if gh:
        with open(gh, "a", encoding="utf-8") as fh:
            fh.write(f"## Data pipeline run #{log.run_id}: {overall.upper()}\n\n")
            fh.write(f"Started by **{log.triggered_by}**, mode **{mode}**"
                     + (f", window **{month_str(window[0])} to {month_str(window[-1])}**" if window else "")
                     + ".\n\n| Stage | Result | Seconds | Detail |\n|---|---|---|---|\n")
            for s in summary["stages"]:
                fh.write(f"| {s['stage']} | {s['status']} | {s['seconds']} | {s.get('detail', '')} |\n")
            fh.write("\n| Measure | Value |\n|---|---|\n")
            for k, v in log.fields.items():
                fh.write(f"| {k.replace('_', ' ')} | {v} |\n")
    return 0 if overall == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
