# Objective 3 — Secure Automated Data Pipeline (status)

> Reference for the data-pipeline objective. Source of truth for the wording:
> **AGRIKA-GIS v3** (Objective 3 + the Data Gathering Tools methodology).
> Last updated 2026-10-11.

## What Objective 3 requires

> Develop and evaluate a **secure automated data pipeline** for **acquiring,
> processing, integrating, and managing** Sentinel-1, Sentinel-2, meteorological,
> and historical yield data **into a centralized spatial database** — evaluated on
> its ability to **reliably acquire, preprocess, integrate, and deliver** the data
> required for prediction and spatial visualization.

Two words in that sentence need their own evidence: **automated** and **secure**.

## Data sources

Acquisition follows the previous AgriKA study (Ebron et al., 2025): Sentinel-2
through the Sentinel Hub services and weather from Open-Meteo. This study adds
Sentinel-1 through the same Sentinel Hub Statistical API.

| Source | Variables | Automated? |
|---|---|---|
| Sentinel-2 (Copernicus Data Space, Sentinel Hub Statistical API) | NDVI, EVI, NDWI | Yes, weekly |
| Sentinel-1 SAR (same API) | VV/VH backscatter | Yes, weekly |
| Open-Meteo archive API | rainfall, temperature, relative humidity | Yes, weekly |
| PhilRice (Ricelytics) + City Agriculture Offices | municipal and barangay yield | **No** — no API exists; uploaded through the Import page |
| PSA shapefiles | boundaries | One-time load |

## "Automated": how it runs

`.github/workflows/data-pipeline.yml` starts `backend/scripts/run_pipeline.py
--incremental` **every Monday at 02:00 Philippine time** (and on demand from the
Actions tab). Weekly is the shortest interval in which every source has something
new: Open-Meteo updates daily with a five-day lag, Sentinel-2 revisits every five
days, Sentinel-1 every six to twelve.

**Two levels.** Every run covers the 30 municipalities. At barangay level it covers
only the barangays that have at least one **reported** yield on record (estimates
do not count) — 42 today: Calamba 12, Santa Rosa 12, Cabuyao 11, Biñan 7. The list
is read from the database at the start of each run, so a barangay joins the
schedule as soon as its first yield is imported, and a barangay with no rice costs
nothing.

Each run:

| # | Stage | What it does |
|---|---|---|
| 1–2 | acquire weather, satellite | municipalities: the month in progress plus the previous one |
| 3 | select barangays | those with a reported yield; boundaries from PostGIS |
| 4–5 | acquire barangay weather, satellite | the same window for those barangays |
| 6 | ensure DB tables | creates the feature tables if missing |
| 7 | load window to DB | idempotent upsert on (area, year, month), both levels |
| 8 | update CSV copies | merges the window into the `db/*.csv` copies |
| 9 | verify window | area-months present; every value inside its physical range |
| 10 | predict season | once a season's six months are complete, trains on all earlier seasons and stores the municipality and barangay forecasts (`predict_season.py`) |

The previous month is re-fetched on purpose: late scenes and archive corrections
land after the month ends, and the upsert makes repeating it free of duplicates.
Dry season (Jan–Jun) is predicted on the first run after about 6 July; Wet season
(Jul–Dec) on the first run after about 6 January.

`--skip-fetch` with `--incremental` loads the CSV copies already in the repository
instead of fetching. It costs no Copernicus units and is how a second database
(Supabase) is brought up to date with what was already fetched.

**Proof of automation:** every run adds a row to the `pipeline_runs` table — start
and end time, what started it (`schedule`, `manual`, `local`), the window, each
stage's result and duration, rows added and refreshed, area-months verified,
integrity violations, predictions added, Copernicus units spent, and whether the
database connection was encrypted. Print it with
`python backend/scripts/pipeline_runs_report.py` (`--prod` for Supabase).

### Runs so far (local database, 2026-10-11)

| Run | Level | Window | Feature rows new / refreshed | Verified | Violations | Predictions | Units | Minutes |
|---|---|---|---|---|---|---|---|---|
| 1 | municipality | 2025-12 | 30 / 30 | 60 of 60 | 0 | 0 | 274.0 | 6.1 |
| 2 | municipality | 2026-07 to 2026-10 | 240 / 0 | 240 of 240 | 0 | 29 municipal (Dry 2026) | 1,096.2 | 6.0 |
| 3 | municipality | 2026-08 to 2026-10 | 0 / 180 | 180 of 180 | 0 | 0 (already stored) | 822.1 | 5.2 |
| 4 | barangay (42) | 2025-12 to 2026-10 | 882 / 42 | 924 of 924 | 0 | 42 barangay (Dry 2026) | 145.0 | 6.9 |
| 5 | both, no fetch | 2025-12 to 2026-10 | 0 / 14,243 | 1,584 of 1,584 | 0 | 0 (already stored) | 0 | 0.1 |

Runs 3 and 5 repeated data that was already loaded: nothing new, no duplicates.
All five were started by hand on a laptop, with their months given explicitly. The
scheduled runs begin once the workflow is on `main` and the three repository
secrets are set (see DEPLOY.md, section 4).

### Copernicus quota (free tier: 30,000 processing units a month)

Measured, not estimated — the API reports the cost of every request and the fetch
adds it up.

| | Units |
|---|---|
| One month of data, 30 municipalities | 274 |
| One month of data, 42 barangays | 13 |
| One weekly run (two months, both levels) | about 575 |
| A month of weekly runs | about 2,500 (8% of the free quota) |

A run stops fetching at 3,000 units for municipalities and 500 for barangays.
Spent on 2026-10-11 while building and backfilling: 2,337.

### Bug found and fixed while building this

The first full fetch asked for `2018-01-01` to `2025-12-31`. The API treats the
last month as one second short of a whole interval and silently drops it, so
**December 2025 had no satellite row for any municipality** — the "99.0%
satellite acquisition" in the first evaluation was this, not missing imagery. The
request now ends on the first instant of the following month. After the backfill,
satellite acquisition for 2018–2025 is 2,880 of 2,880.

## "Secure": what it means here, and the proof

The data is public and not personal, so secrecy of the data is not the concern.
"Secure" is defined with the ISO/IEC 25010 security sub-characteristics (the same
model the UAT uses):

| Property | ISO/IEC 25010 | Control |
|---|---|---|
| Credential confidentiality | Confidentiality | Secrets only in git-ignored `.env` files, Render environment variables and GitHub encrypted secrets; no default signing secret in the code |
| Protected transport | Confidentiality, Integrity | Every external call is HTTPS; a non-local database connection requires TLS |
| Controlled write access | Authenticity, Integrity | Imports need a signed login token; role and city are read from the database on every request; non-administrators are limited to their own city |
| Data integrity | Integrity | Row validation with reasons; parameterized SQL only; unique keys with upsert; per-run range check |
| Traceability | Accountability, Non-repudiation | `yield_import_log` (who imported what, when); `pipeline_runs` (every run) |

`python backend/scripts/security_tests.py` runs **24 test cases** against the real
code and the local database (temporary accounts, removed afterwards). Result on
2026-10-11: **24 of 24 passed**. The report is saved to
`backend/db/security_test_report.txt`.

## Reliability evaluation (`pipeline_reliability.py`, 2018–2025)

Scope: 30 municipalities × 8 years × 12 months = **2,880 expected area-months**.

| Check | First evaluation | After the December fix |
|---|---|---|
| Acquisition | weather 2,880 (100%); satellite 2,850 (99.0%) | weather 2,880 (100%); **satellite 2,880 (100%)** |
| Completeness | optical 89.9%; SAR 99.0% | optical **90.9%** (2,619); SAR **100%** |
| Integrity | 0 violations (4 EVI outliers; EVI not in the final model) | unchanged |
| Integration | 29 of 29 label municipalities; 462 training rows | unchanged |
| Gap accounting | 261 optical gaps, 183 in the wet season; 1.0% absent | 261 optical gaps, 183 in the wet season; **0 absent** |

## First forecasts produced by the pipeline (Dry 2026)

Trained on the 462 observed municipality-seasons of 2018–2025 and never shown 2026.

- **29 municipalities.** Against the Ricelytics yields for that season: **MAE 0.602,
  RMSE 0.700 mt/ha**. That is weaker than the leave-one-year-out result in Chapter 4
  (MAE 0.395): the model over-predicts, mean 4.81 against an observed 4.23. It is one
  season; report it as it is.
- **42 barangays**, 3.51 to 5.18 mt/ha. Not scored: no barangay yield for 2026 has
  been reported yet. The map shows them as forecasts without a residual; the
  residual appears when the yield is imported.

Note: the December 2025 satellite values now exist in the database, so these
forecasts were trained with them. The training CSVs behind the Chapter 4 results
(`training_features_*.csv`) were left as they were, so those results still
reproduce.

## Limits (state these in Scope and Delimitations)

- Yield records are entered by hand; the sources publish no API.
- Barangay level covers only barangays with a reported yield (42 today), by design.
- Read access to the data is public by design; the controls protect writing.
- The pipeline writes with the database owner's account, not a restricted one.
- The scheduler is GitHub Actions: start times can slip by several minutes, and
  GitHub pauses schedules after 60 days without a commit.
- The Green Ratio named in the methodology is still not computed (NDWI is).

## Scripts

| Script | Role |
|---|---|
| `run_pipeline.py` | orchestrator: `--incremental` (scheduled), `--levels`, `--skip-fetch`, full rebuild |
| `fetch_weather_openmeteo.py`, `fetch_satellite_cdse.py` | acquisition; `--from-month/--to-month` windows; quota tracking |
| `load_feature_tables.py`, `load_barangay_feature_tables.py` | upsert into the monthly feature tables |
| `predict_season.py` | forecast a completed season from the database, both levels |
| `pipeline_runs_report.py` | print the run log |
| `pipeline_reliability.py` | reliability evaluation (Table 27) |
| `security_tests.py` | the 24 security test cases |
| `add_pipeline_tables.py`, `backend/audit.py` | the two audit tables |
