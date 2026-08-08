-- ============================================================
--  AgriKA-GIS — PostgreSQL schema (core tables)
--  Built directly from the project ERD.
--  Target: PostgreSQL 18
--
--  NOTE: barangays.boundary_geometry (the PostGIS geometry column) is
--  NOT created here — it's added by schema_geometry.sql once PostGIS is
--  installed (see the GeoJSON import step). Everything else, including
--  login, works without PostGIS.
--
--  Load order: this file creates the tables. Run seed.sql afterwards.
-- ============================================================

-- Drop in reverse-dependency order so the script is re-runnable during dev.
DROP TABLE IF EXISTS residuals                  CASCADE;
DROP TABLE IF EXISTS predictions                CASCADE;
DROP TABLE IF EXISTS municipality_predictions   CASCADE;
DROP TABLE IF EXISTS yield_records              CASCADE;
DROP TABLE IF EXISTS municipality_yield_records CASCADE;
DROP TABLE IF EXISTS barangays      CASCADE;
DROP TABLE IF EXISTS seasons        CASCADE;
DROP TABLE IF EXISTS users          CASCADE;
DROP TABLE IF EXISTS municipalities CASCADE;
DROP TABLE IF EXISTS roles          CASCADE;

-- ------------------------------------------------------------
--  ROLES  (administrator | agriculturist | rice_technician)
-- ------------------------------------------------------------
CREATE TABLE roles (
    role_id   SERIAL PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE
);

-- ------------------------------------------------------------
--  MUNICIPALITIES
-- ------------------------------------------------------------
CREATE TABLE municipalities (
    municipality_id   SERIAL PRIMARY KEY,
    municipality_name VARCHAR(100) NOT NULL UNIQUE
);

-- ------------------------------------------------------------
--  USERS
--  municipality_id is nullable: the provincial administrator
--  is not scoped to a single municipality.
-- ------------------------------------------------------------
CREATE TABLE users (
    user_id         SERIAL PRIMARY KEY,
    username        VARCHAR(100) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(150),
    status          VARCHAR(20) NOT NULL DEFAULT 'Active',
    role_id         INTEGER NOT NULL REFERENCES roles(role_id),
    municipality_id INTEGER     REFERENCES municipalities(municipality_id)
);

-- ------------------------------------------------------------
--  BARANGAYS
--  boundary_geometry (PostGIS) is added later by schema_geometry.sql.
-- ------------------------------------------------------------
CREATE TABLE barangays (
    barangay_id       SERIAL PRIMARY KEY,
    barangay_name     VARCHAR(100) NOT NULL,
    municipality_id   INTEGER NOT NULL REFERENCES municipalities(municipality_id)
);

-- ------------------------------------------------------------
--  SEASONS  (season_type = 'Wet' | 'Dry', plus the year)
-- ------------------------------------------------------------
CREATE TABLE seasons (
    season_id   SERIAL PRIMARY KEY,
    season_type VARCHAR(20) NOT NULL,
    year        INTEGER NOT NULL,
    UNIQUE (season_type, year)
);

-- ------------------------------------------------------------
--  PREDICTIONS  (CNN-LSTM model output, per barangay per season)
-- ------------------------------------------------------------
CREATE TABLE predictions (
    prediction_id   SERIAL PRIMARY KEY,
    predicted_yield DOUBLE PRECISION NOT NULL,
    barangay_id     INTEGER NOT NULL REFERENCES barangays(barangay_id),
    season_id       INTEGER NOT NULL REFERENCES seasons(season_id)
);

-- ------------------------------------------------------------
--  YIELD_RECORDS  (actual observed yields, per barangay per season)
-- ------------------------------------------------------------
CREATE TABLE yield_records (
    yield_id       SERIAL PRIMARY KEY,
    observed_yield DOUBLE PRECISION NOT NULL,
    barangay_id    INTEGER NOT NULL REFERENCES barangays(barangay_id),
    season_id      INTEGER NOT NULL REFERENCES seasons(season_id)
);

-- ------------------------------------------------------------
--  MUNICIPALITY_YIELD_RECORDS  (observed average yield, per municipality
--  per season). Our real historical data (PRiSM / Ricelytics) is only
--  available at municipality level, not barangay level, so it lands here.
--  observed_yield is in mt/ha. source names where the value came from and
--  is_proxy flags values Ricelytics appears to have backfilled (identical
--  yields shared across low-rice cities) so the UI can caveat them.
-- ------------------------------------------------------------
CREATE TABLE municipality_yield_records (
    muni_yield_id   SERIAL PRIMARY KEY,
    observed_yield  DOUBLE PRECISION NOT NULL,
    municipality_id INTEGER NOT NULL REFERENCES municipalities(municipality_id),
    season_id       INTEGER NOT NULL REFERENCES seasons(season_id),
    source          VARCHAR(50),
    is_proxy        BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (municipality_id, season_id)
);

-- ------------------------------------------------------------
--  MUNICIPALITY_PREDICTIONS  (CNN-LSTM predicted average yield, per
--  municipality per season). Mirrors municipality_yield_records because the
--  model is trained/served at municipality level. predicted_yield is in mt/ha.
--  model_version tags the run so several model outputs can coexist; the
--  residual (observed - predicted) is computed on the fly against the observed
--  table rather than stored.
-- ------------------------------------------------------------
CREATE TABLE municipality_predictions (
    muni_pred_id    SERIAL PRIMARY KEY,
    predicted_yield DOUBLE PRECISION NOT NULL,
    municipality_id INTEGER NOT NULL REFERENCES municipalities(municipality_id),
    season_id       INTEGER NOT NULL REFERENCES seasons(season_id),
    model_version   VARCHAR(50) NOT NULL DEFAULT 'cnn-lstm',
    generated_at    TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (municipality_id, season_id, model_version)
);

-- ------------------------------------------------------------
--  RESIDUALS  (observed - predicted; ties a prediction to its actual)
-- ------------------------------------------------------------
CREATE TABLE residuals (
    residual_id    SERIAL PRIMARY KEY,
    residual_value DOUBLE PRECISION NOT NULL,
    prediction_id  INTEGER NOT NULL REFERENCES predictions(prediction_id),
    yield_id       INTEGER NOT NULL REFERENCES yield_records(yield_id)
);

-- Helpful lookup indexes on the foreign keys used most in queries.
CREATE INDEX idx_users_role            ON users(role_id);
CREATE INDEX idx_users_municipality    ON users(municipality_id);
CREATE INDEX idx_barangays_municipality ON barangays(municipality_id);
CREATE INDEX idx_predictions_barangay  ON predictions(barangay_id);
CREATE INDEX idx_predictions_season    ON predictions(season_id);
CREATE INDEX idx_yield_barangay        ON yield_records(barangay_id);
CREATE INDEX idx_yield_season          ON yield_records(season_id);
CREATE INDEX idx_muni_yield_muni       ON municipality_yield_records(municipality_id);
CREATE INDEX idx_muni_yield_season     ON municipality_yield_records(season_id);
CREATE INDEX idx_muni_pred_muni        ON municipality_predictions(municipality_id);
CREATE INDEX idx_muni_pred_season      ON municipality_predictions(season_id);
