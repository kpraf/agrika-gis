# AgriKA-GIS — Objectives & Statement of the Problem

> Source of truth: **AGRIKA-GIS v3** (the team's paper). This file mirrors that
> document so the code work can be based on it. If v3 changes, update this file.

## What the study is

AgriKA-GIS extends a **previous AgriKA system** (cited in v3 as **Ebron et al.,
2025** — a CNN-LSTM using Sentinel-2 + meteorological data, output at the
**municipality level**) into a Web-based spatial decision-support system that:

- integrates **Sentinel-1 SAR** with Sentinel-2 + meteorological + historical yield,
- predicts and visualizes rice yield at the **barangay level** (not municipality),
- adds **residual (prediction-error) maps**, seasonal visualization, municipality filtering,
- adds **role-based data management** for LGU agriculture offices,
- is scoped to **four cities: Biñan, Cabuyao, Calamba, Santa Rosa**.

## General Objective

To determine whether extending the existing AgriKA CNN-LSTM model through
Sentinel-1 SAR integration, barangay-level spatial analysis, and a Web-GIS
platform improves rice-yield prediction performance and spatial decision support
for LGU agriculture offices in Laguna.

## Specific Objectives (verbatim intent from v3)

1. **Extended CNN-LSTM model.** Develop and evaluate an extended CNN-LSTM that
   integrates **Sentinel-1 SAR** with **Sentinel-2 multispectral imagery,
   meteorological variables, and historical yield** for **barangay-level**
   prediction. Evaluate with **RMSE, MAE, R²** and **compare against the previous
   AgriKA model** to determine whether Sentinel-1 gives measurable improvement.

2. **Web-based spatial DSS.** Develop and evaluate a Web-GIS that visualizes
   predicted barangay-level yields, **residual maps** (predicted − observed),
   and seasonal productivity trends. Evaluate via **User Acceptance Testing (UAT)
   using the ISO/IEC 25010** software-quality model.

3. **Secure automated data pipeline.** Develop and evaluate a pipeline that
   automates acquisition, preprocessing, integration, and management of Sentinel-1,
   Sentinel-2, meteorological, and historical yield data into a centralized spatial
   database. Evaluate on reliability of acquisition/preprocessing/integration/delivery.

## Statement of the Problem (core)

Rice-yield monitoring in Laguna relies on slow manual reporting; the previous
AgriKA gives only **municipality-level** predictions (barangay variation is
invisible), relies on **Sentinel-2 only** (cloud-limited in the tropics), and lacks
barangay-level data management, spatial error visualization, and role-based access.
The study asks whether adding **Sentinel-1 SAR**, **barangay-level Web-GIS**,
**residual visualization**, and **role-based management** significantly improves
prediction performance and spatial decision support.

## Data & features (from v3)

| Source | Variables |
|---|---|
| Sentinel-2 | NDVI, EVI, **Green Ratio**, NDWI (vegetation indices) |
| Sentinel-1 | SAR — soil-moisture / ground-condition indicators (cloud-independent) |
| Open-Meteo | rainfall, temperature, **humidity** |
| PhilRice + City Agriculture Offices | historical rice yield (ground truth) |
| PSA shapefiles | barangay boundaries (for visualization) |

## Scope & key delimitations

- **Geographic scope: 4 cities only** — Biñan, Cabuyao, Calamba, Santa Rosa
  (chosen for consistency with the previous AgriKA study + data availability).
- Rice only; barangay-level visualization; residual maps; seasonal comparison;
  municipality-based filtering; role-based access.
- Soil datasets NOT used as inputs (not consistently available); remote-sensing
  proxies used instead.
- No IoT/UAV/irrigation automation; no advanced spatial analysis (hotspot,
  autocorrelation, interpolation); online-only; not a replacement for official surveys.

---

## STATUS — what we built this session vs what v3 requires

> ⚠️ Read this carefully — there are real scope gaps between the code work done so
> far and the paper. The work is reusable, but several things must be re-aligned.

| v3 requirement | What we built | Gap / action |
|---|---|---|
| **Barangay-level** prediction | **Municipality-level** model + predictions | 🔴 **MAJOR.** Model, labels, and app predictions are all municipality-level. Barangay yield ground-truth doesn't exist (PhilRice is municipality-level) — this needs a strategy (weak supervision / downscaling) and must be reconciled with the paper. |
| **4 cities** (Biñan, Cabuyao, Calamba, Santa Rosa) | **All 30 municipalities** | 🔴 Scope mismatch. Re-scope data + training + eval to the 4 cities (or justify province-wide). |
| Features: NDVI, **EVI, Green Ratio, NDWI**; SAR; rainfall, temp, **humidity** | NDVI + VV/VH + rainfall + temp | 🟠 Missing EVI, Green Ratio, NDWI, humidity. |
| Compare vs **previous AgriKA (Ebron et al., 2025)** | Ablation: S2-only vs S2+S1 (same architecture) | 🟠 Our ablation isolates SAR cleanly, but the paper asks to compare vs the *previous* model. **Also: the "previous paper" PDF you gave me is Galang/Lim/Melegrito/Pineda — the paper cites Ebron et al. 2025. Confirm which is the actual previous AgriKA.** |
| RMSE / MAE / R² + paired significance | ✅ Done (municipality-level) | 🟢 Method is right; must be re-run at barangay level / 4-city scope. |
| Residual maps (barangay) | Municipality residuals in `/api/yield/compare` | 🟠 Partial — need barangay-level residual maps. |
| Web-GIS barangay visualization | ✅ Boundaries + choropleth exist; barangay yield is synthetic | 🟠 Wire real barangay predictions once they exist. |
| Secure automated data pipeline (Obj 3) | ✅ Fetch scripts (weather, S1/S2), loaders | 🟢 Well aligned; formalize + evaluate reliability. |
| Role-based data management | ✅ Roles exist in the app | 🟢 Aligned. |
| UAT via **ISO/IEC 25010** | Not started | ⬜ Open. |

### Biggest thing to resolve first
The paper's **Objective 1 is barangay-level**, but there is **no barangay-level
yield ground truth**. This tension (raised earlier this session) is now central.
Decide the approach — e.g. train on municipality labels and predict at barangay
resolution using barangay features (weak supervision), or a defined downscaling —
and make sure the paper and the model agree. This blocks a true, paper-aligned
Objective 1 result.
