# Barangay-level baseline (Option B)

**Question:** Can we predict yield at the **barangay** level from the same
environmental features that drive the municipality model?

**Short answer: not with the data we have.** Under a realistic
leave-one-year-out evaluation the barangay baseline is **worse than predicting
the mean** (negative R²). This is a legitimate, defensible result — it justifies
keeping the deployed model at municipality level and sets honest expectations for
a future barangay CNN-LSTM (Option C).

## Data

| | Value |
|---|---|
| Ground-truth labels | `barangay_yield` — **156** observed barangay-season yields |
| Barangays | **23** (12 City of Santa Rosa + 11 City of Cabuyao) |
| Municipalities | **2** of 30 (only these have collected barangay data) |
| Years / seasons | Santa Rosa 2020–2025; Cabuyao Dry 2021, Wet 2023, Dry 2024, Wet 2024, Dry 2025 |
| Features | Same as the municipality model: rain, temp, humidity (Open-Meteo ERA5) + NDVI, VV, VH (Sentinel-2/1 via CDSE), 6 monthly steps per season |
| Feature scope | Fetched **only for the 23 yield-bearing barangays** (per-barangay polygon stats), not all 682 |
| Satellite coverage | all 156 samples have some NDVI; 146/156 have full 6/6 SAR |

Method mirrors the municipality baseline exactly: PSA-semester alignment
(Dry → Jan–Jun, Wet → Jul–Dec), mean-imputed satellite gaps, RandomForest / Ridge,
**leave-one-year-out** GroupKFold, pooled out-of-fold metrics.

## Results (RandomForest, leave-one-year-out)

| Model | Features | RMSE | MAE | R² |
|---|---|---|---|---|
| Mean (naive floor) | — | 0.638 | 0.448 | −0.141 |
| Ridge | sensors only | 0.644 | 0.453 | −0.164 |
| RandomForest | sensors only | 0.705 | 0.536 | −0.392 |
| RandomForest | sensors + season + municipality | 0.707 | 0.536 | −0.401 |
| RandomForest | sensors + season + **barangay identity** | 0.704 | 0.532 | −0.390 |

Every model is **below the naive mean floor**. Adding municipality or per-barangay
identity does not help.

## Why it fails — diagnostics

Three cross-validation schemes on the same RandomForest (rain/temp/humid/ndvi/vv/vh):

| Evaluation | What it tests | R² | MAE |
|---|---|---|---|
| Leave-one-**year**-out | forecast an unseen season (the real use case) | **−0.392** | 0.536 |
| Leave-one-**barangay**-out | an unseen barangay within seen years (spatial) | **+0.042** | 0.369 |
| Leave-one-**municipality**-out | transfer Santa Rosa ↔ Cabuyao | −0.230 | 0.500 |

- **Year-to-year level shifts dominate and are not predicted by the features.**
  Season means swing a lot (Dry ≈ 5.0 vs Wet 2024 ≈ 3.97), so a model trained on
  other years mis-levels the held-out year.
- There is only a **whisper of spatial signal** (leave-one-barangay-out R² ≈ +0.04):
  the features can barely distinguish barangays within a known year, and not
  usefully.
- **Santa Rosa and Cabuyao do not transfer** to each other.

Per (year, season) target means, showing the level shifts:

```
2021 Dry 5.04 / Wet 5.03    2022 Dry 5.08 / Wet 4.30
2023 Dry 4.67 / Wet 4.44    2024 Dry 4.60 / Wet 3.97
2025 Dry 4.52 / Wet 4.43
```

## Interpretation

156 samples across 5 years in 2 municipalities is too thin, and barangay yields
are noisier than municipality aggregates. The environmental features that give the
municipality model R² ≈ 0.15–0.20 (462 samples, 30 municipalities, 8 years) carry
essentially no predictive signal at barangay scale under temporal CV. Aggregation
to municipality **helps** — a point in the thesis' favour, not against it.

## Implication for Option C (barangay CNN-LSTM)

A CNN-LSTM needs **more** data than a RandomForest, and the RandomForest already
underperforms the mean here. A barangay CNN-LSTM on the current data would almost
certainly also fail, and would be hard to defend. Recommended before attempting C:

1. **Collect more barangay data** — more municipalities (Biñan, Calamba) and more
   seasons per barangay, to break the 2-municipality / 5-year ceiling.
2. Until then, present **barangay as observed-only** (real collected yields shown
   on the map / monitoring / analytics), with this baseline as the documented
   evidence that the model appropriately stays at municipality level.

## Reproduce

```bash
# features (only the 23 yield-bearing barangays)
python backend/scripts/fetch_weather_openmeteo.py  --level barangay --start 2020 --end 2025 \
    --geojson db/geojson/Laguna_Barangays_yield.geojson --out db/weather_barangay_sr_cabuyao_monthly.csv --resume --sleep 3
python backend/scripts/fetch_satellite_cdse.py     --level barangay --start 2020 --end 2025 \
    --geojson db/geojson/Laguna_Barangays_yield.geojson --out db/satellite_barangay_sr_cabuyao_monthly.csv --resume
# training rows + baseline
python backend/scripts/build_training_rows_barangay.py
python backend/scripts/baseline_model.py --wide db/training_features_barangay_wide.csv \
    --id-col municipality --prefixes rain,temp,humid,ndvi,vv,vh
```
