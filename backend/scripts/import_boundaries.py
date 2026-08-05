"""
One-time import of Laguna boundary GeoJSON (QGIS/PSA export) into PostGIS.

Loads:
  - 30 municipalities  -> municipalities.boundary_geometry
  - 682 barangays      -> barangays.boundary_geometry (linked to municipality by adm3_pcode)

Municipalities already seeded (by plain name) are UPDATED in place so their IDs
stay stable (demo users keep their municipality link); the rest are inserted.
The 5 placeholder seed barangays (and the sample predictions/yields/residuals that
referenced them) are cleared and replaced with the real 682.

Run once, from backend/:
    .\venv\Scripts\python.exe scripts\import_boundaries.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text  # noqa: E402
from app import create_app  # noqa: E402
from extensions import db  # noqa: E402

GEOJSON_DIR = r"C:\QGIS Projects"
MUNI_FILE = "Laguna_Municipalities.geojson"
BRGY_FILE = "Laguna_Barangays.geojson"

# Insert geometry as MultiPolygon in WGS84 (SRID 4326).
GEOM_SQL = "ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:g), 4326))"


def norm(name):
    """Normalise a municipality name for matching seed <-> official PSA names."""
    n = (name or "").strip().lower()
    if n.startswith("city of "):
        n = n[8:]
    return n.replace("\u00f1", "n").strip()  # n-tilde -> n


def load(path):
    with open(os.path.join(GEOJSON_DIR, path), encoding="utf-8") as fh:
        return json.load(fh)


def main():
    app = create_app()
    with app.app_context():
        s = db.session

        # --- 1. Ensure PostGIS + geometry columns exist (idempotent) ---
        s.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        s.execute(text("ALTER TABLE municipalities ADD COLUMN IF NOT EXISTS boundary_geometry geometry(MultiPolygon, 4326)"))
        s.execute(text("ALTER TABLE barangays ADD COLUMN IF NOT EXISTS boundary_geometry geometry(MultiPolygon, 4326)"))
        s.execute(text("CREATE INDEX IF NOT EXISTS idx_municipalities_boundary ON municipalities USING GIST (boundary_geometry)"))
        s.execute(text("CREATE INDEX IF NOT EXISTS idx_barangays_boundary ON barangays USING GIST (boundary_geometry)"))
        s.commit()
        print("PostGIS enabled, geometry columns ready.")

        # --- 2. Municipalities: update seeded rows in place, insert the rest ---
        existing = {
            norm(r.municipality_name): r.municipality_id
            for r in s.execute(text("SELECT municipality_id, municipality_name FROM municipalities"))
        }
        pcode_to_id = {}
        muni = load(MUNI_FILE)
        for f in muni["features"]:
            name = f["properties"]["name"]
            pcode = f["properties"]["adm3_pcode"]
            gj = json.dumps(f["geometry"])
            key = norm(name)
            if key in existing:
                mid = existing[key]
                s.execute(
                    text(f"UPDATE municipalities SET municipality_name = :n, boundary_geometry = {GEOM_SQL} WHERE municipality_id = :id"),
                    {"n": name, "g": gj, "id": mid},
                )
            else:
                mid = s.execute(
                    text(f"INSERT INTO municipalities (municipality_name, boundary_geometry) VALUES (:n, {GEOM_SQL}) RETURNING municipality_id"),
                    {"n": name, "g": gj},
                ).scalar()
                existing[key] = mid
            pcode_to_id[pcode] = mid
        s.commit()
        print(f"Municipalities: {len(muni['features'])} processed.")

        # --- 3. Clear placeholder barangays + dependent sample data ---
        s.execute(text("DELETE FROM residuals"))
        s.execute(text("DELETE FROM predictions"))
        s.execute(text("DELETE FROM yield_records"))
        s.execute(text("DELETE FROM barangays"))
        s.commit()

        # --- 4. Import barangays, linked to municipality via adm3_pcode ---
        brgy = load(BRGY_FILE)
        inserted, skipped = 0, 0
        for f in brgy["features"]:
            props = f["properties"]
            parent = props["adm3_pcode"]
            mid = pcode_to_id.get(parent)
            if mid is None:
                skipped += 1
                continue
            # Some features have a null 'name' — fall back to the English name, then pcode.
            bname = props.get("name") or props.get("adm4_en") or props.get("adm4_pcode") or "Unnamed"
            s.execute(
                text(f"INSERT INTO barangays (barangay_name, municipality_id, boundary_geometry) VALUES (:n, :m, {GEOM_SQL})"),
                {"n": bname, "m": mid, "g": json.dumps(f["geometry"])},
            )
            inserted += 1
        s.commit()

        # --- 5. Report ---
        mcount = s.execute(text("SELECT count(*) FROM municipalities")).scalar()
        mgeom = s.execute(text("SELECT count(*) FROM municipalities WHERE boundary_geometry IS NOT NULL")).scalar()
        bcount = s.execute(text("SELECT count(*) FROM barangays")).scalar()
        bgeom = s.execute(text("SELECT count(*) FROM barangays WHERE boundary_geometry IS NOT NULL")).scalar()
        gtype = s.execute(text("SELECT DISTINCT ST_GeometryType(boundary_geometry) FROM barangays")).scalar()
        print(f"municipalities: {mcount} (with geometry: {mgeom})")
        print(f"barangays: inserted {inserted}, skipped {skipped}")
        print(f"barangays total: {bcount} (with geometry: {bgeom})")
        print(f"geometry type: {gtype}")


if __name__ == "__main__":
    main()
