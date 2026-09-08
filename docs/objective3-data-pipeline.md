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

1. **🔴 Centralized spatial database.** Weather & satellite features live in **CSVs**,
   not the PostGIS DB. Only boundaries, yield, and predictions are in the DB. The
   paper explicitly says integrate *into a centralized spatial database*.
   → Add `weather_monthly` + `satellite_monthly` tables and loaders.

2. **🟠 Automated pipeline (single orchestrator).** The steps are separate manual
   scripts. → One entry point that runs acquire → preprocess → integrate → load,
   with logging and clear success/failure reporting.

3. **🟠 Reliability evaluation.** None yet. The objective is *evaluated* on reliable
   acquire/preprocess/integrate/deliver. → A QA/validation report.

4. **🟢 Minor: Green Ratio vs NDWI.** Methodology names Green Ratio (B08/B03); we
   fetched NDWI (which the ablation showed didn't help). Add Green Ratio if the
   paper alignment is wanted; low priority.

## Proposed build order (when we start)

**Step 1 — DB integration (foundational, start here).**
- Schema: `weather_monthly(municipality_id, year, month, rainfall_mm, temp_mean_c, humidity_mean_pct, ...)` and `satellite_monthly(municipality_id, year, month, ndvi_mean, evi_mean, vv_mean, vh_mean, s2_valid_px, s1_valid_px, ...)`, FK to `municipalities`.
- Loaders: CSV → tables (idempotent upsert, name-folding match like the predictions loader).
- Result: the "centralized spatial database" the paper describes.

**Step 2 — Pipeline orchestrator.**
- `run_pipeline.py`: acquire (weather, satellite) → preprocess → merge → load to DB → build training data, with a run log and per-stage status. `--skip-fetch` to re-integrate without re-hitting the APIs.

**Step 3 — Reliability evaluation.**
- Metrics: acquisition success rate (areas fetched / attempted), data completeness (% of expected area-month cells present), integrity checks (value ranges, no NaN/Inf leaking through, name-join coverage), gap accounting (S2 cloud gaps, S1 2022 dip), and delivery check (training rows produced vs labels).
- Output: a `pipeline_reliability_report` (printed + saved), to cite in the Objective 3 evaluation.

## Evaluation framing for the paper

The pipeline's reliability can be reported as: **X% acquisition success**, **Y% area-month
completeness** (with documented, expected gaps for tropical S2 cloud cover and the 2022
Sentinel-1 dip), **0 integrity violations** (all values in range, no non-finite values
delivered), and **100% of yield labels matched** to feature rows. These are concrete,
defensible reliability figures for a developmental-research pipeline evaluation.
