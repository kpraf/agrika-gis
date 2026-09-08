# AgriKA-GIS — Objectives & Statement of the Problem

> ⚠️ **DRAFT — verify against your approved proposal.** This was reconstructed from
> the work done this session and your consolidated revision list. It is a working
> reference, NOT your official approved objectives. Paste your real objectives/SOP
> over this, or correct anything that doesn't match what your panel signed off on.

## Project overview

AgriKA-GIS is a web-based rice-yield forecasting and GIS monitoring platform for
the province of Laguna. It **enhances a previous study's** Sentinel-2-only CNN-LSTM
yield model by **integrating Sentinel-1 (SAR)** alongside Sentinel-2, and presents
results on interactive maps and dashboards for local government units and
agriculturists.

## General Objective

To develop an enhanced web-based rice-yield forecasting and spatial monitoring
system for Laguna that improves upon the previous CNN-LSTM model by integrating
Sentinel-1 SAR data, and to evaluate the enhancement through a controlled,
apples-to-apples comparison.

## Specific Objectives

1. **Enhance and evaluate the model (core contribution).**
   Recreate the previous study's CNN-LSTM and integrate Sentinel-1 SAR features
   alongside Sentinel-2, then determine whether the enhancement produces a
   statistically significant improvement in prediction accuracy (RMSE, MAE, R²)
   over the Sentinel-2-only model — evaluated on the **same** data, target, and
   test observations, with a paired significance test (Shapiro-Wilk → paired
   t-test / Wilcoxon).

2. **Spatial (GIS) visualization.**
   Visualize observed and predicted rice yield across Laguna's municipalities
   (and barangays) using real PSA administrative boundaries and interactive maps.

3. **Web application integration.**
   Integrate the enhanced model into a web platform providing yield monitoring,
   observed-vs-predicted comparison, analytics, and reporting for authorized users.

4. **Usability and functional evaluation.**
   Evaluate the system's functionality and usability with agriculturists through
   functional testing and user-acceptance testing.

## Statement of the Problem

**General problem.** How can the previous AgriKA rice-yield forecasting model be
enhanced with Sentinel-1 SAR and integrated into a GIS-based web platform to
support rice-yield monitoring and forecasting in Laguna?

**Specific questions.**

1. Does integrating Sentinel-1 SAR with Sentinel-2 **significantly improve** the
   CNN-LSTM's yield-prediction accuracy (RMSE, MAE, R²) compared to the
   Sentinel-2-only model, when both are trained and tested on identical data,
   target, and observations?
2. How can observed and predicted yields be **spatially represented** across
   Laguna's municipalities and barangays?
3. How can the enhanced model be **integrated into a web application** for
   monitoring, comparison, analytics, and reporting?
4. How **usable and functional** is the system when evaluated by agriculturists?

## Scope and Delimitations

**In scope**
- Province of Laguna: 30 municipalities/cities, 682 barangays (PSA boundaries).
- Period: 2018–2025, two cropping seasons (Dry / Wet).
- Data: PhilRice/Ricelytics yield (municipality-level), Open-Meteo weather
  (ERA5), Sentinel-1 + Sentinel-2 via Copernicus (CDSE).
- Model: recreated previous-study CNN-LSTM (Test Four), enhanced with SAR.
- Evaluation: leave-one-year-out CV; paired significance test for Objective 1.

**Delimitations**
- Yield labels are **municipality-level**; barangay-level values are a synthetic
  downscale (no barangay ground-truth exists).
- San Pedro is excluded from yield (no rice fields), though it has weather/satellite.
- Rice only; Laguna only; no real-time field-sensor or IoT data.
- Predictions are historical/seasonal (2018–2025); live future forecasting is a
  separate deployment step (a final trained model + inference pipeline).

## How this maps to what has been built (status)

| Objective | Status |
|---|---|
| 1 — SAR enhancement + significance | ✅ Done. SAR significantly improved MAE 0.450→0.418 (paired t-test p=0.003). See [experiment-results-objective1.md](experiment-results-objective1.md). |
| 2 — GIS visualization | ✅ Largely built (municipality/barangay maps, choropleth). Barangay yield still synthetic. |
| 3 — Web integration | 🔶 Partial. Observed-vs-predicted comparison now live with real CNN-LSTM predictions. Live future forecasting not yet wired. |
| 4 — Usability evaluation | ⬜ Not started (functional + UAT with agriculturists). |
