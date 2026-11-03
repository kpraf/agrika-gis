"""
phase_pictures_stage.py
=======================

Pipeline stage of the faithful Objective 1 model (Objective 3): keeps the
growth-phase pictures and their ResNet50 features up to date and stored in the
centralized database, so that a fresh scheduled runner can predict a season.

    --export   write the picture features held in the database to the files that
               faithful_model.py reads (index CSVs and .npz, for the cities and the
               barangays), and the monthly weather to weather_laguna_monthly.csv when
               the database is at least as recent as that file (the weekly pipeline
               loads new months into the database, not into the repository); the
               first step on a fresh runner
    --fetch    download the NDVI and Sentinel-1 pictures of every growth phase that has
               ended and is not yet in the index, for the 28 cities and the barangays,
               and compute the features of the new pictures only
    --load     store in the database every picture record not yet there
               (table phase_picture_features; features as float16)

A phase whose window has not ended is never requested. A phase with no usable
picture is stored too (without features), so it is not requested again every week.

Usage
    python backend/scripts/phase_pictures_stage.py --export
    python backend/scripts/phase_pictures_stage.py --fetch --max-pu 300
    python backend/scripts/phase_pictures_stage.py --load
"""
import argparse
import csv
import datetime as dt
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

import previous_study_images as psi  # noqa: E402

PS = psi.OUT_DIR
BR = os.path.join(PS, "barangay")
BR_GEOJSON = os.path.join(BR, "barangays_42.geojson")
LEVELS = {"city": PS, "barangay": BR}
WEATHER_CSV = os.path.abspath(os.path.join(PS, "..", "weather_laguna_monthly.csv"))
WEATHER_COLS = ["municipality", "year", "month", "rainfall_mm", "temp_mean_c", "humidity_mean_pct", "days"]
NDVI_COLS = psi.COLUMNS
S1_COLS = ["city", "year", "semester", "phase", "date", "ndvi_date", "file", "pu"]
DDL = """
CREATE TABLE IF NOT EXISTS phase_picture_features (
    level       text     NOT NULL,          -- city or barangay
    area        text     NOT NULL,          -- city name, or 'City of X|Barangay'
    year        integer  NOT NULL,
    semester    smallint NOT NULL,          -- 1 = dry, 2 = wet
    phase       smallint NOT NULL,          -- growth phase 1 to 3
    sensor      text     NOT NULL,          -- ndvi or s1
    image_date  date,
    green_ratio real,
    file        text,
    record      jsonb,                      -- the full index row
    features    bytea,                      -- 2,048 float16 values; NULL when no usable picture
    loaded_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (level, area, year, semester, phase, sensor)
)"""


def run(script, argv):
    cmd = [sys.executable, os.path.join(HERE, script), *argv]
    print("  $", " ".join(cmd[1:]), flush=True)
    return subprocess.run(cmd, check=False).returncode


def files_of(folder, sensor):
    idx = os.path.join(folder, "image_index.csv" if sensor == "ndvi" else "image_index_s1.csv")
    npz = os.path.join(folder, "image_features.npz" if sensor == "ndvi" else "image_features_s1.npz")
    return idx, npz


def read_index(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ------------------------------------------------------------------ stages
def export(db, text):
    db.session.execute(text(DDL))
    db.session.commit()
    for level, folder in LEVELS.items():
        os.makedirs(folder, exist_ok=True)
        for sensor in ("ndvi", "s1"):
            rows = db.session.execute(text(
                "SELECT record, file, features FROM phase_picture_features WHERE level = :l AND sensor = :s "
                "ORDER BY area, year, semester, phase"), {"l": level, "s": sensor}).all()
            if not rows:
                continue
            idx, npz = files_of(folder, sensor)
            cols = NDVI_COLS if sensor == "ndvi" else S1_COLS
            with open(idx, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                w.writerows(r.record for r in rows)
            have = [(r.file, np.frombuffer(r.features, dtype=np.float16).astype(np.float32)) for r in rows
                    if r.file and r.features is not None]
            if have:
                feats = np.stack([f for _, f in have])
                np.savez_compressed(npz, files=np.array([f for f, _ in have]), features=feats, features_aug=feats)
            print(f"exported {level} {sensor}: {len(rows)} records, {len(have)} with features")
    export_weather(db, text)
    return "ok"


def export_weather(db, text):
    rows = db.session.execute(text(
        "SELECT m.municipality_name AS municipality, w.year, w.month, w.rainfall_mm, w.temp_mean_c, "
        "w.humidity_mean_pct, w.days FROM weather_monthly w "
        "JOIN municipalities m ON m.municipality_id = w.municipality_id ORDER BY 1, 2, 3")).mappings().all()
    if not rows:
        print("weather: none in the database; keeping", os.path.basename(WEATHER_CSV))
        return
    have = read_index(WEATHER_CSV)
    last = lambda rs: max((int(r["year"]) * 100 + int(r["month"]) for r in rs), default=0)
    if last(rows) < last(have) or len(rows) < len(have):
        print(f"weather: database ends {last(rows)}, file ends {last(have)}; keeping the file")
        return
    with open(WEATHER_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=WEATHER_COLS)
        w.writeheader()
        w.writerows(dict(r) for r in rows)
    print(f"weather: exported {len(rows)} months, to {last(rows)}")


def fetch(max_pu):
    today = dt.date.today()
    years = f"{today.year - 1}-{today.year}"
    status = 0
    status |= run("previous_study_images.py", ["--years", years, "--resume", "--max-pu", str(max_pu / 4)])
    status |= run("previous_study_s1_images.py", ["--years", years, "--resume", "--max-pu", str(max_pu / 4)])
    if os.path.exists(BR_GEOJSON):
        status |= run("previous_study_images.py", ["--geojson", BR_GEOJSON, "--out-dir", BR, "--years", years,
                                                   "--resume", "--max-pu", str(max_pu / 4)])
        status |= run("previous_study_s1_images.py", ["--geojson", BR_GEOJSON, "--out-dir", BR, "--ndvi-index",
                                                      os.path.join(BR, "image_index.csv"), "--years", years,
                                                      "--resume", "--max-pu", str(max_pu / 4)])
    for folder in LEVELS.values():
        for sensor in ("ndvi", "s1"):
            if read_index(files_of(folder, sensor)[0]):
                status |= run("previous_study_features.py", ["--sensor", sensor, "--dir", folder])
    return "ok" if status == 0 else "partial"


def load(db, text):
    db.session.execute(text(DDL))
    added = 0
    for level, folder in LEVELS.items():
        for sensor in ("ndvi", "s1"):
            idx, npz = files_of(folder, sensor)
            rows = read_index(idx)
            if not rows:
                continue
            feats = {}
            if os.path.exists(npz):
                z = np.load(npz, allow_pickle=False)
                feats = dict(zip(z["files"], z["features"]))
            stored = {(r.area, r.year, r.semester, r.phase) for r in db.session.execute(text(
                "SELECT area, year, semester, phase FROM phase_picture_features WHERE level = :l AND sensor = :s "
                "AND (features IS NOT NULL OR file IS NULL OR file = '')"), {"l": level, "s": sensor})}
            import json
            new = []
            for r in rows:
                k = (r["city"], int(r["year"]), int(r["semester"]), int(r["phase"]))
                if k in stored:
                    continue
                f = feats.get(r["file"]) if r["file"] else None
                if r["file"] and f is None:
                    continue                    # picture without features yet: wait for the next run
                new.append({"l": level, "a": k[0], "y": k[1], "sem": k[2], "p": k[3], "s": sensor,
                            "d": r["date"] or None, "g": float(r["green_ratio"]) if r.get("green_ratio") else None,
                            "f": r["file"] or None, "rec": json.dumps(r),
                            "x": f.astype(np.float16).tobytes() if f is not None else None})
            if new:
                db.session.execute(text(
                    "INSERT INTO phase_picture_features (level, area, year, semester, phase, sensor, image_date, "
                    "green_ratio, file, record, features) VALUES (:l, :a, :y, :sem, :p, :s, :d, :g, :f, "
                    "CAST(:rec AS jsonb), :x) ON CONFLICT (level, area, year, semester, phase, sensor) DO UPDATE SET "
                    "image_date = EXCLUDED.image_date, green_ratio = EXCLUDED.green_ratio, file = EXCLUDED.file, "
                    "record = EXCLUDED.record, features = EXCLUDED.features, loaded_at = now()"), new)
            added += len(new)
            print(f"loaded {level} {sensor}: {len(new)} new records")
    db.session.commit()
    return "ok", added


def main():
    ap = argparse.ArgumentParser(description="Growth-phase pictures for the faithful model, kept in the database.")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--load", action="store_true")
    ap.add_argument("--max-pu", type=float, default=300, help="Processing-unit limit for the whole fetch.")
    args = ap.parse_args()
    if args.fetch:
        print("fetch:", fetch(args.max_pu))
    if args.export or args.load:
        from sqlalchemy import text
        from app import create_app
        from extensions import db
        with create_app().app_context():
            if args.export:
                print("export:", export(db, text))
            if args.load:
                print("load:", load(db, text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
