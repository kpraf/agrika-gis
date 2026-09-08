# Open Questions for the Adviser

Decisions that are the adviser's/panel's to make, gathered so nothing is lost.
Most block the barangay-level extension (Objectives 1 & 2); the rest are framing
confirmations.

## 1. Barangay-level data & scope (the main blocker)

**Context.** Barangay-level yield ground truth does not exist in PhilRice (municipal
only). The paper's plan is to collect it **manually from the 4 City Agriculture
Offices** (Biñan, Cabuyao, Calamba, Santa Rosa) "whenever available." Table 2 lists
~30 active rice-producing barangays across the 4 cities (Biñan ~5, Calamba ~11,
Cabuyao ~11, Santa Rosa active) — **not all 682 barangays**. Manual collection will
be slow, and realistically may not cover 8 years of history per barangay.

**Questions:**
1. **How much barangay yield data can the 4 City Ag Offices realistically provide** —
   how many seasons / years, for how many barangays?
2. If the barangay data is **sparse** (e.g. only recent seasons), is **barangay-level
   evaluation** (apply the model at barangay resolution, validate against whatever
   barangay yield is collected) acceptable — instead of full barangay-level *training*?
3. Is a **municipality-trained model applied at barangay resolution** (using
   barangay-level satellite/weather features) defensible as "barangay-level
   prediction" for Objective 1?
4. Is limiting the barangay work to the **4 cities' active rice barangays** (~30)
   consistent with the objective, or is province-wide barangay coverage expected?

## 2. Objective 1 comparison framing (apples-to-apples)

**Context.** A panelist asked for an apples-to-apples comparison, not a comparison
against the previous model's *published* numbers. We recreated the previous CNN-LSTM
and ran a controlled ablation (S2-only vs S2+S1) on the same data/target/observations,
with a paired significance test (Wilcoxon p=0.028). This re-derives the previous
model's behavior on our data rather than citing its printed metrics.

**Question:**
5. Does this controlled-ablation + paired-test approach satisfy the panelist's
   "apples-to-apples" requirement, or do they expect the original model's *exact
   published pipeline* (Adjusted Yield, ResNet features) reproduced?

## 3. Previous-study citation

**Context.** The paper cites the previous AgriKA as **Ebron et al. (2025)**, but the
actual source document is **Galang, Lim, Melegrito, Pineda**. The metrics match
exactly (RMSE 0.5545 / MAE 0.4324 / R² 0.3125), so it is the same work.

**Question:**
6. Confirm the correct citation for the previous AgriKA study (Ebron vs Galang et al.).

## 4. Forecasting claim

**Context.** The paper's title/framing promises "yield **forecasting**," but the
demonstrated method is historical validation (predicting past seasons with known
yield). A true forward forecast (before harvest) is not yet implemented.

**Question:**
7. Which forecasting claim to commit to — the defensible **nowcast** ("estimate
   available before the manual report is filed") or a stronger **before-harvest**
   forecast (which would require a partial-season model)? Avoid over-claiming.

---

*Status of the code side (for reference): Objective 1 municipality-level model is
complete with a statistically significant SAR result; Objective 3 data pipeline is
complete; Objective 2 platform is built and wired. Barangay-level work and the
ISO/IEC 25010 UAT are the remaining pieces.*
