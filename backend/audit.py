"""
Audit trail tables (Objective 3, traceability).

    yield_import_log  one row per CSV import through the web app: who, when,
                      which city they were limited to, and how many rows changed.
    pipeline_runs     one row per run of the data pipeline (run_pipeline.py):
                      when, what started it, what each stage did.

Neither table is ever updated or deleted from by the application - rows are only
added (a pipeline run is the one exception: its own row is completed when it ends).

The DDL lives here so the web app, the pipeline and the one-off script
(scripts/add_pipeline_tables.py) all create exactly the same tables.
"""
from sqlalchemy import text

from extensions import db

IMPORT_LOG_DDL = """
CREATE TABLE IF NOT EXISTS yield_import_log (
    import_id          SERIAL PRIMARY KEY,
    imported_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    user_id            INTEGER      NOT NULL,
    username           VARCHAR(100) NOT NULL,
    role               VARCHAR(50)  NOT NULL,
    municipality_scope VARCHAR(100),
    level              VARCHAR(20)  NOT NULL,
    source             VARCHAR(120),
    rows_inserted      INTEGER      NOT NULL DEFAULT 0,
    rows_updated       INTEGER      NOT NULL DEFAULT 0,
    rows_skipped       INTEGER      NOT NULL DEFAULT 0
)
"""

PIPELINE_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id                   SERIAL PRIMARY KEY,
    started_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at              TIMESTAMPTZ,
    triggered_by             VARCHAR(20) NOT NULL,
    mode                     VARCHAR(20) NOT NULL,
    window_from              VARCHAR(7),
    window_to                VARCHAR(7),
    status                   VARCHAR(20) NOT NULL DEFAULT 'running',
    stages                   JSONB,
    weather_rows_new         INTEGER,
    weather_rows_refreshed   INTEGER,
    satellite_rows_new       INTEGER,
    satellite_rows_refreshed INTEGER,
    predictions_new          INTEGER,
    processing_units         DOUBLE PRECISION,
    cells_expected           INTEGER,
    weather_cells            INTEGER,
    satellite_cells          INTEGER,
    integrity_violations     INTEGER,
    db_encrypted             BOOLEAN,
    run_ref                  VARCHAR(255),
    notes                    TEXT
)
"""

# Columns added after the table first shipped. ADD COLUMN IF NOT EXISTS keeps an
# existing run log (and its rows) and brings it up to the current shape.
PIPELINE_RUNS_MIGRATIONS = [
    "ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS barangays INTEGER",
    "ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS barangay_rows_new INTEGER",
    "ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS barangay_rows_refreshed INTEGER",
    "ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS barangay_cells_expected INTEGER",
    "ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS barangay_cells INTEGER",
    "ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS barangay_predictions_new INTEGER",
]

_import_log_ready = False


def _create(ddl):
    # A short lock wait: if the table cannot be created promptly, fail the
    # request instead of hanging it.
    db.session.execute(text("SET LOCAL lock_timeout = '5s'"))
    db.session.execute(text(ddl))
    db.session.commit()


def ensure_import_log():
    """Create yield_import_log if this database does not have it yet.

    Checked once per process. Commits, so call it before the import starts
    writing. Raises if the table cannot be created - the caller must then refuse
    the import, because an import that cannot be logged is not allowed.
    """
    global _import_log_ready
    if _import_log_ready:
        return
    try:
        _create(IMPORT_LOG_DDL)
    except Exception:
        db.session.rollback()
        raise
    _import_log_ready = True


def ensure_pipeline_runs():
    db.session.execute(text("SET LOCAL lock_timeout = '5s'"))
    db.session.execute(text(PIPELINE_RUNS_DDL))
    for stmt in PIPELINE_RUNS_MIGRATIONS:
        db.session.execute(text(stmt))
    db.session.commit()


def log_import(user, role, scope_name, level, source, inserted, updated, skipped):
    """Add the audit row for an import, in the SAME transaction as the import.

    The caller commits: either the yields and their audit row are both stored,
    or neither is.
    """
    db.session.execute(
        text(
            "INSERT INTO yield_import_log (user_id, username, role, municipality_scope, level, "
            "source, rows_inserted, rows_updated, rows_skipped) "
            "VALUES (:uid, :uname, :role, :scope, :level, :src, :ins, :upd, :skip)"
        ),
        {"uid": user.user_id, "uname": user.username, "role": role, "scope": scope_name,
         "level": level, "src": (source or "")[:120], "ins": inserted, "upd": updated,
         "skip": skipped},
    )
