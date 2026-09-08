# Objective 3 — Secure Automated Data Pipeline (plan & status)

> Reference for the data-pipeline objective. Source of truth: **AGRIKA-GIS v3**
> (Objective 3 + the Data Gathering Tools methodology). To be tackled after the
> current work; this captures the plan so we can pick it up cleanly.

## What Objective 3 requires

> Develop and evaluate a **secure automated data pipeline** for **acquiring,
> processing, integrating, and managing** Sentinel-1, Sentinel-2, meteorological,
> and historical yield data **into a centralized spatial database** — evaluated on
> its ability to **reliably acquire, preprocess, integrate, and deliver** the data
> required for prediction and spatial visualization.

## Data sources (from the methodology)

| Source | Variables the paper names | Notes |
|---|---|---|
| Sentinel-2 (Copernicus/CDSE) | NDVI, EVI, **Green Ratio (NIR/Green = B08/B03)** | Paper's methodology says **Green Ratio**, not NDWI. We currently fetch NDWI. |
| Sentinel-1 SAR (CDSE) | VV/VH backscatter (soil-moisture proxy) | Have it. |
| Open-Meteo API | rainfall, temperature, **relative humidity** | Have all three. |
| PhilRice (+ City Ag Offices) | municipal yield; **barangay "whenever available"** | Barangay ground truth may not exist. |
| PSA shapefiles | barangay boundaries | Have them (PostGIS). |

## What is already built ✅

| Pipeline stage | Status | Where |
|---|---|---|
| **Acquire** | ✅ | `fetch_weather_openmeteo.py`, `fetch_satellite_cdse.py` (resume-capable) |
| **Preprocess** | ✅ | cloud/SCL masking, monthly aggregation, SAR dB conversion, finite-guards, UTM reprojection, gap handling |
| **Integrate** | ✅ | `build_training_rows.py` (merge weather+satellite, PSA-semester season alignment) |
| **Deliver to model** | ✅ | `training_features_{wide,sequences}.csv` |
| **Predictions → DB → app** | ✅ | `export_cnn_lstm_predictions.py` → `load_municipality_predictions.py` → `municipality_predictions` table |
| **Secure credentials** | ✅ | gitignored `.env`, env-var loading, no secrets in code |

So acquisition + preprocessing + integration logic is essentially done.

## Gaps to fully satisfy Objective 3

1. **✅ DONE — Centralized spatial database.** `weather_monthly` (2,880 rows) and
   `satellite_monthly` (2,850 rows) PostGIS tables added (schema.sql +
   `add_feature_tables.py`), loaded from the fetch CSVs by `load_feature_tables.py`
   (idempotent upsert, diacritics-folded name match, 0 skipped). Features now live
   in the DB alongside boundaries, yield, and predictions.

2. **✅ DONE — Automated pipeline (single orchestrator).** `run_pipeline.py` runs
   acquire → ensure-tables → load-to-DB → build-training as ordered stages, with
   per-stage banners, timing, stop-on-failure (or `--continue-on-error`), and a
   `--skip-fetch` flag to re-integrate/reload without hitting the APIs. Writes a
   machine-readable `db/pipeline_last_run.json` summary.

3. **✅ DONE — Reliability evaluation.** `pipeline_reliability.py` queries the DB +
   training set and reports acquisition, completeness, integrity, integration, and
   gap accounting (saved to `pipeline_reliability_report.txt`). Headline results
   below.

4. **🟢 Minor: Green Ratio vs NDWI.** Methodology names Green Ratio (B08/B03); we
   fetched NDWI (which the ablation showed didn't help). Add Green Ratio if the
   paper alignment is wanted; low priority.

## Proposed build order (when we start)

**Step 1 — DB integration (foundational). ✅ DONE.**
- Schema: `weather_monthly` and `satellite_monthly` (FK to `municipalities`, UNIQUE
  on municipality/year/month) in `schema.sql` + `add_feature_tables.py`.
- Loader: `load_feature_tables.py` — CSV → tables, idempotent ON CONFLICT upsert,
  diacritics-folded name match. Loaded 2,880 weather + 2,850 satellite rows, 0 skipped.
- Result: the "centralized spatial database" the paper describes.

**Step 2 — Pipeline orchestrator. ✅ DONE.**
- `run_pipeline.py`: acquire weather → acquire satellite → ensure DB tables →
  load features to DB → build training set, as ordered stages with per-stage
  timing/status, stop-on-failure, `--skip-fetch`, and a `pipeline_last_run.json`
  summary. Verified end-to-end with `--skip-fetch`.

**Step 3 — Reliability evaluation. ✅ DONE.**
- `pipeline_reliability.py`: acquisition, completeness, integrity, integration, and
  gap-accounting checks against the DB + training set; saves `pipeline_reliability_report.txt`.

## Evaluation results (citable, from pipeline_reliability.py)

Scope: 30 municipalities × 8 years × 12 months = **2,880 expected area-months** (2018-2025).

| Check | Result |
|---|---|
| **Acquisition** | weather 2,880/2,880 (100%); satellite 2,850/2,880 (99.0%); 30/30 municipalities |
| **Completeness** | weather features 100%; NDVI/EVI/NDWI 89.9%; VV/VH 99.0% |
| **Integrity** | **0 violations** — all values in physical range, no non-finite values (4 EVI outliers noted; EVI excluded from final model) |
| **Integration** | **29/29** yield-label municipalities matched to features (100%); **462** training rows delivered |
| **Gap accounting** | S2 cloud gaps concentrated in wet season (183/261); S1 SAR complete where acquired; 1.0% area-months fully absent |

**Verdict: 0 integrity violations, weather complete, satellite gaps documented and
expected** (tropical optical cloud cover). A defensible reliability result for a
developmental-research pipeline evaluation.
