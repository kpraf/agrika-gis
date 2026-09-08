# Previous Paper — Results & Discussion (summary)

Source: **Galang, Lim, Melegrito, Pineda (BSCS)** thesis, "Optimized CNN-LSTM model
for rice yield" — Results & Discussion chapter (PDF pages 100–170).
Summarized for reference while building the AgriKA-GIS model.

## Phase 1: Dataset Creation

**Data sources (same stack we use):**
- PhilRice — rice yield (t/ha), 2018–2024, 29/30 municipalities (San Pedro excluded, no rice fields)
- SentinelHub — Sentinel-2 L2A → NDVI images per growth phase (no Sentinel-1/SAR used)
- OpenMeteo — temperature, rainfall, humidity

**Season/phase structure:** two seasons — Dry (Sep 16–Mar 15), Wet (Mar 16–Sep 15) —
each split into 3 growth phases (Vegetative, Reproductive, Ripening). Phase-splitting
expanded data to **1,131 records**.

**Feature engineering:**
- Image features: ResNet50 (ImageNet, no top, global avg pool) → **2048-dim vector per NDVI image** (CNN spatial input)
- Green Ratio: from NDVI images via RGB color-masking; used to redistribute each season's
  total yield across the 3 phases → **"Adjusted Yield"** (target variable)
- Label-encoded municipality; date → day/month/year; mean-imputation for cloud-missing images;
  augmentation (rotate/flip, val/test only)
- Feature selection (correlation matrix) kept: City/Municipality, Temperature, Green Ratio,
  Day, Month, Image Features → Adjusted Yield. Dropped Season, Phase (redundant with Day/Month), Year (low corr).
- Final dataset: 1,131 rows × 7 cols, split chronologically (train 2018 S2→2023 S2 = 957 rows).

## Phase 2: CNN-LSTM Modeling — four trials

| Model | Key change | Test RMSE | Test MAE | Test R² | Val R² |
|---|---|---|---|---|---|
| 1 Baseline | 1 Conv(32) + 1 LSTM(32) | 0.8897 | 0.6634 | −0.9836 | −0.9836 |
| 2 | Conv→64, batch/layer norm, LeakyReLU | 0.6313 | 0.4927 | 0.2152 | −0.0730 |
| 3 | Deeper (CNN 128/256, stacked LSTM) | 0.6881 | 0.5141 | 0.0919 | 0.5141 |
| 4 FINAL | Simplified + Gaussian noise (σ=0.01), LR decay | 0.6512 | 0.5143 | 0.1649 | 0.3125 |

**Final = Model 4**, chosen for stability across both test and validation.
Baseline → Final (validation): RMSE 0.9419 → 0.5545, MAE 0.7054 → 0.4324, R² −0.9836 → 0.3125.

## Benchmarking

| Metric | Nevavuori 2019 (CNN) | Sun 2019 (CNN-LSTM soybean) | Their model |
|---|---|---|---|
| RMSE | – | 0.3899 | 0.5545 |
| MAE | 0.5338 | – | 0.4324 |
| R² | – | 0.74 | 0.3125 |

## Confidence Test (10 unseen samples)

Bands by abs error (t/ha): ≤0.25 Very Accurate · 0.26–0.50 Acceptable · 0.51–0.75 Moderate ·
0.76–1.00 High · >1.00 Very High. Errors 0.18–1.02 t/ha; 3 Very Accurate, 3 Acceptable, 2 High,
1 Very High. Confidence-test R² = 0.354.

## Phase 3–4: Web app + testing

Web app: About Us, Yield Prediction, Real-Time Yield Data (maps/tables/graphs). Functional
testing (manual pass/fail) + usability testing with city agriculturists (Biñan, Santa Rosa,
Cabuyao, Calamba, Los Baños). UAT (4-pt Likert): navigation 3.50, design 3.33, charts 3.33.

## Implications for our build

1. **Low bar to clear** — their final model reached only R² ≈ 0.31 (val) / 0.16 (test). Rice-yield
   prediction from this data is genuinely hard; modest early numbers are expected.
2. **Different features** — they used 2048-dim ResNet50 vectors from NDVI images and **no SAR**.
   We use aggregated NDVI + Sentinel-1 VV/VH statistics — simpler, and SAR is a potential edge.
3. **Different target** — theirs was "Adjusted Yield" (real yield redistributed across phases by
   green ratio), so their RMSE/MAE are on a ~1/3 scale (mean ~1.2 t/ha) and NOT directly comparable
   to ours (real seasonal yield, ~3–6 mt/ha). **R² is the fair cross-comparison.**
