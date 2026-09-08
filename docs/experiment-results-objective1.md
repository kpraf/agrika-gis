# Objective 1 — Experiment Results (Sentinel-1 contribution)

**Question:** Does adding Sentinel-1 (SAR) to the yield model produce a real,
statistically significant improvement over a Sentinel-2-only model?

**Design (apples-to-apples ablation):** the previous study's final CNN-LSTM
("Test Four" / Model 4, Galang et al.) was recreated in PyTorch and run **twice**
on our data. The ONLY difference between runs is the feature set, so the measured
difference is Sentinel-1's contribution.

| Held constant | Value |
|---|---|
| Architecture | Recreated Test Four CNN-LSTM (2 Conv1D 64/128 k5, 2 LSTM 128/64, 2 Dense 64/32, Gaussian noise 0.01, Adam lr 4.5e-4, L2 1e-4) |
| Target | Real municipality seasonal yield (mt/ha) |
| Protocol | Leave-one-year-out CV (8 years, 2018–2025), pooled out-of-fold predictions |
| Test observations | Identical across both runs (paired) |

Two documented adaptations to our 6-step sequences: pooling omitted (would collapse
the temporal axis), and recurrent dropout approximated (PyTorch cuDNN LSTM limitation).

## Features (current)

Meteorological (rainfall, temperature, **humidity**) + Sentinel-2 **NDVI** in both
models; the enhanced model adds Sentinel-1 **VV/VH**. EVI and NDWI are implemented
in the fetch but **deferred** — the full 30-municipality re-fetch is blocked by the
CDSE processing-unit quota (only 10 cities, incl. the 4 target cities, have them).
Add once the quota resets.

## Results (with humidity)

### Models compared

| Model | Features | RMSE | MAE | R² |
|---|---|---|---|---|
| RandomForest baseline | S2+S1 | 0.486 | 0.387 | **0.202** |
| CNN-LSTM Original | rain, temp, humid, ndvi (S2) | 0.526 | 0.421 | 0.075 |
| **CNN-LSTM Enhanced** | **+ vv, vh (S2+S1)** | **0.503** | **0.395** | **0.152** |

Adding **humidity** lifted both models markedly (enhanced R² 0.085 → 0.152 vs the
earlier rain/temp/NDVI-only run). Adding Sentinel-1 improves on every metric on top
of that. The enhanced CNN-LSTM (0.152) now approaches the RandomForest floor (0.20).

### Paired significance test (Objective 1)

Paired on identical test observations; diff = |err_original| − |err_enhanced|
(positive ⇒ enhanced better).

| Statistic | Value |
|---|---|
| Paired samples | 462 |
| Mean abs error, Original | 0.4205 t/ha |
| Mean abs error, Enhanced | 0.3950 t/ha |
| Mean improvement | +0.0255 t/ha (−6.1% error) |
| Samples enhanced better | 254/462 (55.0%) |
| Shapiro–Wilk (normality of diffs) | W=0.990, p=0.003 → NOT normal |
| **Wilcoxon signed-rank (primary)** | **W=47153, p=0.028** ✅ |
| Paired t-test (corroborating) | t=2.40, p=0.017 ✅ |
| Effect size (Cohen's d, paired) | 0.11 (small) |

**Verdict: the Sentinel-1 improvement is statistically significant (p=0.028) and
not due to chance.** As humidity strengthens the base model, SAR's marginal effect
is slightly smaller than the earlier run but still significant under both tests.

## Citable summary

> With meteorological (rainfall, temperature, humidity) and Sentinel-2 NDVI inputs,
> adding Sentinel-1 SAR to the recreated CNN-LSTM significantly reduced mean absolute
> error from 0.421 to 0.395 t/ha (Wilcoxon signed-rank p=0.028; paired t-test
> t=2.40, p=0.017; Shapiro–Wilk W=0.990, p=0.003; Cohen's d=0.11), on identical
> leave-one-year-out test observations. Enhanced R²=0.152 vs original R²=0.075.

## Honest caveats (for the defense)

1. **Small effect.** Statistically significant, but ~7% error reduction (d=0.14).
   Do not oversell it.
2. **Deep model < simple baseline.** The CNN-LSTM (R² 0.085) underperforms a
   RandomForest (R² 0.20). On this dataset size, complexity did not pay off.
3. **Modest absolute performance.** Yields cluster tightly (4.2 ± 0.55 mt/ha), so
   there is little variance to explain; R² will look low regardless of method.

## Reproduce

```
python backend/scripts/baseline_model.py             # RandomForest / Ridge floor
python backend/scripts/cnn_lstm_model.py             # both CNN-LSTM configs -> OOF CSV
python backend/scripts/paired_significance_test.py   # Shapiro-Wilk + paired test
```
