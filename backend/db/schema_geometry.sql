-- ============================================================
--  AgriKA-GIS — PostGIS geometry add-on
--  Run this ONCE PostGIS is installed (Stack Builder), before/at the
--  GeoJSON import. It enables PostGIS and adds the spatial columns that
--  the ERD calls for.
--
--  Safe to re-run.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- Barangay boundaries (from Laguna_Barangays.geojson)
ALTER TABLE barangays
    ADD COLUMN IF NOT EXISTS boundary_geometry geometry(MultiPolygon, 4326);
CREATE INDEX IF NOT EXISTS idx_barangays_boundary
    ON barangays USING GIST (boundary_geometry);

-- Municipality boundaries (from Laguna_Municipalities.geojson) —
-- not in the original ERD but needed to draw city outlines on the map.
ALTER TABLE municipalities
    ADD COLUMN IF NOT EXISTS boundary_geometry geometry(MultiPolygon, 4326);
CREATE INDEX IF NOT EXISTS idx_municipalities_boundary
    ON municipalities USING GIST (boundary_geometry);
