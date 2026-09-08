"""
run_pipeline.py
===============

Objective 3 orchestrator: run the full data pipeline end to end from one command,
with per-stage logging and a machine-readable run summary.

Stages (in order):
  1. acquire weather    - fetch_weather_openmeteo.py   (Open-Meteo)      [fetch]
  2. acquire satellite  - fetch_satellite_cdse.py       (Copernicus/CDSE) [fetch]
  3. ensure DB tables   - add_feature_tables.py
  4. load features → DB - load_feature_tables.py         (centralized spatial DB)
  5. build training set - build_training_rows.py         (deliver to the model)

The two [fetch] stages hit external APIs; the satellite fetch consumes CDSE
processing units. Use --skip-fetch to re-integrate and reload from the existing
CSVs without touching the APIs (the common case during development).

By default a stage failure stops the pipeline (later stages depend on earlier
ones); pass --continue-on-error to run them all regardless.

A summary of the run (stage, status, seconds) is written to
db/pipeline_last_run.json for the reliability report to consume.

Usage
    python backend/scripts/run_pipeline.py                 # full pipeline (fetches)
    python backend/scripts/run_pipeline.py --skip-fetch    # re-integrate + reload only
    python backend/scripts/run_pipeline.py --start 2018 --end 2025
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.abspath(os.path.join(HERE, "..", "db"))
SUMMARY_PATH = os.path.join(DB_DIR, "pipeline_last_run.json")


def build_stages(args):
    """(name, script, argv, is_fetch) for each stage."""
    return [
        ("acquire weather", "fetch_weather_openmeteo.py",
         ["--start", str(args.start), "--end", str(args.end), "--sleep", "1.5"], True),
        ("acquire satellite", "fetch_satellite_cdse.py",
         ["--start", str(args.start), "--end", str(args.end)], True),
        ("ensure DB tables", "add_feature_tables.py", [], False),
        ("load features to DB", "load_feature_tables.py", [], False),
        ("build training set", "build_training_rows.py", [], False),
    ]


def run_stage(name, script, argv):
    """Run one stage as a subprocess; return (ok, seconds)."""
    banner = f" STAGE: {name} "
    print("\n" + banner.center(70, "="), flush=True)
    cmd = [sys.executable, os.path.join(HERE, script), *argv]
    print(f"$ {' '.join(cmd[1:])}\n", flush=True)
    t0 = time.time()
    result = subprocess.run(cmd, cwd=os.path.join(HERE, ".."))
    secs = round(time.time() - t0, 1)
    ok = result.returncode == 0
    print(f"\n-> {name}: {'OK' if ok else 'FAILED (exit %d)' % result.returncode} in {secs}s",
          flush=True)
    return ok, secs


def main():
    ap = argparse.ArgumentParser(description="Run the AgriKA-GIS data pipeline end to end.")
    ap.add_argument("--start", type=int, default=2018)
    ap.add_argument("--end", type=int, default=2025)
    ap.add_argument("--skip-fetch", action="store_true",
                    help="Skip the API acquisition stages; re-integrate/reload from existing CSVs.")
    ap.add_argument("--continue-on-error", action="store_true",
                    help="Run every stage even if one fails (default: stop on first failure).")
    args = ap.parse_args()

    stages = build_stages(args)
    started = datetime.now().isoformat(timespec="seconds")
    print(f"AgriKA-GIS pipeline | started {started} | "
          f"{'SKIP-FETCH' if args.skip_fetch else 'full (with fetch)'} | {args.start}-{args.end}")

    summary = {"started": started, "skip_fetch": args.skip_fetch, "stages": []}
    overall_ok = True
    for name, script, argv, is_fetch in stages:
        if is_fetch and args.skip_fetch:
            print(f"\n{(' SKIPPED: %s ' % name).center(70, '=')}")
            summary["stages"].append({"stage": name, "status": "skipped", "seconds": 0})
            continue
        ok, secs = run_stage(name, script, argv)
        summary["stages"].append({"stage": name, "status": "ok" if ok else "failed", "seconds": secs})
        if not ok:
            overall_ok = False
            if not args.continue_on_error:
                print(f"\nPipeline stopped: '{name}' failed. "
                      f"(use --continue-on-error to run remaining stages)")
                break

    summary["finished"] = datetime.now().isoformat(timespec="seconds")
    summary["overall"] = "ok" if overall_ok else "failed"
    with open(SUMMARY_PATH, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    # Final report
    print("\n" + " PIPELINE SUMMARY ".center(70, "="))
    for s in summary["stages"]:
        print(f"  {s['stage']:<22} {s['status']:<8} {s['seconds']:>6}s")
    print(f"\noverall: {summary['overall'].upper()}  |  summary -> {SUMMARY_PATH}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
