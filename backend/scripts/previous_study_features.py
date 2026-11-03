"""
previous_study_features.py
==========================

Second step of rebuilding the previous AgriKA study's dataset (after
previous_study_images.py): turn each NDVI image into the inputs their model
used.

    * Image features - ResNet50 with ImageNet weights, classification layers
      removed, global average pooling: one 2,048-value vector per image (their
      "Image Feature Collection"). They used the Keras copy of ResNet50; this
      uses the torchvision copy of the same network.
    * Augmented copy  - each image rotated and flipped, features extracted again
      (their "Data Augmentation"; used only in their test and validation sets).
    * Temperature     - daily mean air temperature from Open-Meteo at the city
      coordinates listed in their code, so each image can take the temperature
      of its own date.

Outputs (backend/db/previous_study/)
    image_features.npz       files, features (N x 2048), features_aug (N x 2048)
    temperature_daily.csv    city, date, temp_mean_c

Usage
    python backend/scripts/previous_study_features.py
    python backend/scripts/previous_study_features.py --sensor s1            # Sentinel-1 pictures
    python backend/scripts/previous_study_features.py --dir <folder> --sensor s1   # e.g. barangay pictures
"""
import argparse
import csv
import datetime as dt
import json
import os
import time
import urllib.parse
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.abspath(os.path.join(HERE, "..", "db", "previous_study"))
IMG_DIR = os.path.join(OUT_DIR, "images")
INDEX = os.path.join(OUT_DIR, "image_index.csv")
FEATURES = os.path.join(OUT_DIR, "image_features.npz")
TEMPERATURE = os.path.join(OUT_DIR, "temperature_daily.csv")
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
# Open-Meteo's archive runs about five days behind; ask up to a week ago.
END_DATE = (dt.date.today() - dt.timedelta(days=7)).isoformat()

# City coordinates from the previous study's code (model/variablescollection.py).
COORDS = {
    "Alaminos": (14.0616, 121.2604), "Bay": (14.1320, 121.2569), "Cabuyao": (14.2471, 121.1367),
    "Calauan": (14.1384, 121.3198), "Cavinti": (14.2647, 121.5455), "Binan": (14.3036, 121.0781),
    "Calamba": (14.2127, 121.1639), "Santa Rosa": (14.2843, 121.0889), "Famy": (14.4730, 121.4842),
    "Kalayaan": (14.3313, 121.5484), "Liliw": (14.1364, 121.4399), "Los Banos": (14.1699, 121.2441),
    "Luisiana": (14.1908, 121.5256), "Lumban": (14.2956, 121.4962), "Mabitac": (14.4338, 121.4113),
    "Magdalena": (14.2041, 121.4342), "Majayjay": (14.1447, 121.4723), "Nagcarlan": (14.1490, 121.3885),
    "Paete": (14.3675, 121.5300), "Pagsanjan": (14.2624, 121.4570), "Pakil": (14.3800, 121.4765),
    "Pangil": (14.4074, 121.4856), "Pila": (14.2346, 121.3656), "Rizal": (14.0841, 121.4113),
    "San Pablo": (14.0642, 121.3233), "Santa Cruz": (14.2691, 121.4113), "Santa Maria": (14.5129, 121.4342),
    "Siniloan": (14.4383, 121.4856), "Victoria": (14.2028, 121.3370),
}


def read_index(index=INDEX):
    with open(index, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def extract_features(rows, img_dir=IMG_DIR, out=FEATURES):
    import torch
    from PIL import Image
    from torchvision.models import ResNet50_Weights, resnet50

    files = sorted({r["file"] for r in rows if r["file"]})
    known = {}
    if os.path.exists(out):                 # incremental: keep the features already computed
        z = np.load(out, allow_pickle=False)
        known = {f: (a, b) for f, a, b in zip(z["files"], z["features"], z["features_aug"])}
    todo = [f for f in files if f not in known]
    print(f"  {len(files)} pictures, {len(todo)} without features yet", flush=True)
    if not todo:
        return
    model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V1, progress=False)
    model.fc = torch.nn.Identity()          # no top layer; the pooled 2,048 values are the output
    model.eval()
    mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)

    def run(batch):
        x = torch.tensor(np.stack(batch), dtype=torch.float32).permute(0, 3, 1, 2) / 255.0
        with torch.no_grad():
            return model((x - mean) / std).numpy()

    for i in range(0, len(todo), 32):
        # RGB only, as their code passed it (pixels outside the fields keep the script's fill colour)
        batch = todo[i:i + 32]
        imgs = [np.asarray(Image.open(os.path.join(img_dir, f)).convert("RGBA"))[..., :3] for f in batch]
        for f, a, b in zip(batch, run(imgs), run([np.ascontiguousarray(np.fliplr(np.rot90(im))) for im in imgs])):
            known[f] = (a, b)
        print(f"  features {min(i + 32, len(todo))}/{len(todo)}", flush=True)
    names = sorted(known)
    np.savez_compressed(out, files=np.array(names), features=np.stack([known[f][0] for f in names]),
                        features_aug=np.stack([known[f][1] for f in names]))
    print(f"wrote {out}")


def fetch_temperature(rows):
    cities = sorted(COORDS)                 # every city, whatever has been downloaded so far
    out = []
    for city in cities:
        lat, lon = COORDS[city]
        query = urllib.parse.urlencode({"latitude": lat, "longitude": lon, "start_date": "2017-09-01",
                                        "end_date": END_DATE, "daily": "temperature_2m_mean",
                                        "timezone": "Asia/Singapore"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(f"{ARCHIVE_URL}?{query}", timeout=90) as resp:
                    daily = json.load(resp)["daily"]
                break
            except Exception as e:  # noqa: BLE001
                print(f"  {city}: {type(e).__name__}, retrying", flush=True)
                time.sleep(20 * (attempt + 1))
        else:
            raise SystemExit(f"could not fetch temperature for {city}")
        out += [(city, d, t) for d, t in zip(daily["time"], daily["temperature_2m_mean"]) if t is not None]
        print(f"  temperature {city}: {len(daily['time'])} days", flush=True)
        time.sleep(1.5)
    with open(TEMPERATURE, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["city", "date", "temp_mean_c"])
        w.writerows(out)
    print(f"wrote {TEMPERATURE}")


def temperature_is_current():
    if not os.path.exists(TEMPERATURE):
        return False
    with open(TEMPERATURE, encoding="utf-8") as fh:
        last = fh.readlines()[-1].split(",")[1]
    return last >= min(END_DATE, "2026-09-15") and last >= latest_phase_end()


def latest_phase_end():
    """End date (ISO) of the most recent growth phase that has ended, so its picture dates have a temperature."""
    import previous_study_images as psi
    today = dt.date.today() - dt.timedelta(days=7)
    ends = [e for y in (today.year - 1, today.year) for sem in (1, 2) for _, _, e in psi.phase_windows(y, sem) if e <= today]
    return max(ends).isoformat()


def main():
    ap = argparse.ArgumentParser(description="ResNet50 features of the phase pictures, and daily temperature.")
    ap.add_argument("--sensor", choices=["ndvi", "s1"], default="ndvi")
    ap.add_argument("--dir", default=OUT_DIR, help="Folder holding the index and the picture folder.")
    args = ap.parse_args()
    suffix = "_s1" if args.sensor == "s1" else ""
    index = os.path.join(args.dir, f"image_index{suffix}.csv")
    rows = read_index(index)
    print(f"index rows: {len(rows)} | with an image: {sum(1 for r in rows if r['file'])}")
    if not temperature_is_current():
        fetch_temperature(rows)
    extract_features(rows, os.path.join(args.dir, f"images{suffix}"), os.path.join(args.dir, f"image_features{suffix}.npz"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
