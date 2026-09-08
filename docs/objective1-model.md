# Objective 1 — Enhanced CNN-LSTM Model (plan & status)

> Reference for the prediction-model objective. Source of truth: **AGRIKA-GIS v3**.
> Full experiment numbers live in [experiment-results-objective1.md](experiment-results-objective1.md);
> this is the status/tracking view.

## What Objective 1 requires

> Develop and evaluate an extended CNN-LSTM integrating **Sentinel-1 SAR** with
> **Sentinel-2 multispectral, meteorological variables, and historical yield** for
> **barangay-level** prediction. Evaluate with **RMSE, MAE, R²** and **compare
> against the previous AgriKA model** to determine whether Sentinel-1 gives a
> measurable improvement.

Previous model confirmed = **Galang / Ebron et al. (2025)**, final metrics
RMSE 0.5545 / MAE 0.4324 / R² 0.3125 (on their redistributed "Adjusted Yield").

## What is done ✅

| Item | Status | Detail |
|---|---|---|
| Recreate previous CNN-LSTM | ✅ | PyTorch reimplementation of their Test Four (Conv1D 64/128, LSTM 128/64, Gaussian noise, etc.) |
| Integrate S1 SAR + S2 + meteo | ✅ | rain, temp, humidity, NDVI (+ VV/VH for enhanced) |
| Evaluate RMSE/MAE/R² | ✅ | leave-one-year-out CV (8 years) |
| Apples-to-apples comparison | ✅ | S2-only vs S2+S1, same data/target/splits (ablation isolates SAR) |
| Paired significance test | ✅ | Shapiro-Wilk → Wilcoxon; **SAR significant p=0.028** |
| Feature ablation | ✅ | humidity helped (R² 0.085→0.152); EVI/NDWI degraded, excluded |
| Baseline floor | ✅ | RandomForest R² 0.20 (context) |

**Final model:** rain + temp + humidity + NDVI (+ SAR). Enhanced **R² 0.152,
MAE 0.395**, SAR improvement significant.

## Gaps / open items

1. **🔴 Barangay-level.** Paper's Obj 1 is *barangay-level*; our model is
   **municipality-level**. Blocked by the absence of barangay-level yield ground
   truth (PhilRice is municipal). Needs a strategy (weak supervision / downscaling
   / barangay data from City Ag Offices) — parked for last per team decision.
2. **🟠 4-city scope.** Paper scopes to Biñan, Cabuyao, Calamba, Santa Rosa; we
   trained on all 30 municipalities (for sample size + Galang-comparison parity).
   Reconcile when barangay work starts.
3. **🟠 Comparison framing.** Our comparison is the S2-vs-S2+S1 ablation (required
   for the paired test — same target/observations). It re-derives the previous
   model's behavior on our data rather than citing its published numbers. Confirm
   this satisfies the adviser's "apples-to-apples" ask (it does per the paired-test
   requirement).
4. **🟢 Green Ratio.** Methodology names Green Ratio (B08/B03); we used NDVI (+ the
   ablated EVI/NDWI). Add if paper alignment wanted; ablation suggests low upside.

## Verdict

Objective 1 is **substantially complete at municipality level** with a
statistically significant SAR result. The remaining work is the **barangay-level
re-scope** (tied to the barangay ground-truth question), deferred to last.
