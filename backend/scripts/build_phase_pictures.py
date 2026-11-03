"""
build_phase_pictures.py
=======================

Copies the growth-phase pictures the model uses (Sentinel-2 NDVI and Sentinel-1 radar,
one per phase, per city or barangay and season) into the web app as small WebP files,
with an index the Spatial GIS side panel reads.

Source (not in the repository; made by previous_study_images.py / previous_study_s1_images.py):
    <src>/image_index.csv, image_index_s1.csv, images/, images_s1/                 cities
    <src>/barangay/image_index.csv, image_index_s1.csv, images/, images_s1/        barangays

Output:
    public/phase-pictures/<m|b>/<place>/<year><D|W><phase>-<n|r>.webp   n = NDVI, r = radar
    public/phase-pictures/index.json
        {"m": {"<city key>": {"<year> <Dry|Wet>": [[phase, ndvi_date, radar_date], ...]}},
         "b": {"<city key>|<barangay key>": {...}}}
    Keys are names folded like src/lib/text.js foldText (lower case, no accents) with a
    leading "city of " dropped, so they match the map's names in any database.
    A date is null when that phase has no picture (e.g. no cloud-free NDVI scene).

Semester 1 (October to March) is the Dry season and semester 2 the Wet season, as in
the model. Each place's pictures are cropped to the area its pictures cover (the union of
their non-transparent pixels, plus a small margin), the same crop for every phase and
season, so scattered city rice fields are not lost in an empty frame.

Usage
    python backend/scripts/build_phase_pictures.py --src <path to backend/db/previous_study>
"""
import argparse
import csv
import json
import os
import re
import unicodedata

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "public", "phase-pictures")
SEASON = {"1": ("Dry", "D"), "2": ("Wet", "W")}


def fold(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().strip()
    return re.sub(r"^city of ", "", s)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def read_index(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def place_of(level, name):
    if level == "b":
        city, brgy = name.split("|", 1)
        return f"{fold(city)}|{fold(brgy)}", os.path.join(slug(fold(city)), slug(fold(brgy)))
    return fold(name), slug(fold(name))


def build(src, level, manifest, quality, pad=4):
    base = os.path.join(src, "barangay") if level == "b" else src
    jobs = []
    for kind, index_name, folder in (("n", "image_index.csv", "images"), ("r", "image_index_s1.csv", "images_s1")):
        for row in read_index(os.path.join(base, index_name)):
            if row.get("file"):
                jobs.append((kind, os.path.join(base, folder, row["file"]), row))
    # one crop box per place: union of the non-transparent areas of all its pictures
    boxes = {}
    for _, path, row in jobs:
        bb = Image.open(path).getchannel("A").getbbox()
        if bb:
            k = place_of(level, row["city"])[0]
            b0 = boxes.get(k)
            boxes[k] = bb if not b0 else (min(b0[0], bb[0]), min(b0[1], bb[1]), max(b0[2], bb[2]), max(b0[3], bb[3]))
    count = 0
    for kind, path, row in jobs:
        key, place = place_of(level, row["city"])
        img = Image.open(path)
        if key in boxes:
            x0, y0, x1, y1 = boxes[key]
            img = img.crop((max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad)))
        season, letter = SEASON[row["semester"]]
        phase = int(row["phase"])
        name = f"{row['year']}{letter}{phase}-{kind}.webp"
        out_dir = os.path.join(OUT, level, place)
        os.makedirs(out_dir, exist_ok=True)
        img.save(os.path.join(out_dir, name), "WEBP", quality=quality, method=4)
        phases = manifest[level].setdefault(key, {}).setdefault(f"{row['year']} {season}", {})
        entry = phases.setdefault(phase, [phase, None, None])
        entry[1 if kind == "n" else 2] = row["date"] or None
        count += 1
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="backend/db/previous_study of the main checkout")
    ap.add_argument("--quality", type=int, default=80)
    a = ap.parse_args()
    manifest = {"m": {}, "b": {}}
    n_m = build(a.src, "m", manifest, a.quality)
    n_b = build(a.src, "b", manifest, a.quality)
    # phase dicts -> sorted lists
    for level in manifest.values():
        for seasons in level.values():
            for k in seasons:
                seasons[k] = [seasons[k][p] for p in sorted(seasons[k])]
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {n_m} city and {n_b} barangay pictures; {len(manifest['m'])} cities, {len(manifest['b'])} barangays")


if __name__ == "__main__":
    main()
