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

## Results

### Models compared

| Model | Features | RMSE | MAE | R² |
|---|---|---|---|---|
| RandomForest baseline | S2+S1 | 0.486 | 0.387 | **0.202** |
| CNN-LSTM Original | S2 only (rain, temp, ndvi) | 0.564 | 0.450 | −0.065 |
| **CNN-LSTM Enhanced** | **S2 + S1 (+ vv, vh)** | **0.523** | **0.418** | **0.085** |

Adding Sentinel-1 improved the CNN-LSTM on every metric. Note the deep model still
trails the simple RandomForest baseline (R² 0.20) — expected on 462 samples.

### Paired significance test (Objective 1)

Paired on identical test observations; diff = |err_original| − |err_enhanced|
(positive ⇒ enhanced better).

| Statistic | Value |
|---|---|
| Paired samples | 462 |
| Mean abs error, Original | 0.4502 t/ha |
| Mean abs error, Enhanced | 0.4176 t/ha |
| Mean improvement | +0.0326 t/ha (−7.2% error) |
| Samples enhanced better | 248/462 (53.7%) |
| Shapiro–Wilk (normality of diffs) | W=0.994, p=0.087 → normal |
| **Paired t-test (primary)** | **t=3.00, p=0.0028** ✅ |
| Wilcoxon signed-rank (corroborating) | W=46290, p=0.012 ✅ |
| Effect size (Cohen's d, paired) | 0.14 (small) |

**Verdict: the Sentinel-1 improvement is statistically significant (p=0.003) and
not due to chance.** The effect is small but real.

## Citable summary

> Adding Sentinel-1 SAR to the recreated CNN-LSTM significantly reduced mean
> absolute error from 0.450 to 0.418 t/ha (paired t-test t=3.00, p=0.003;
> Shapiro–Wilk W=0.994, p=0.087 confirming normality; Wilcoxon p=0.012; Cohen's
> d=0.14), evaluated on identical leave-one-year-out test observations.

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
