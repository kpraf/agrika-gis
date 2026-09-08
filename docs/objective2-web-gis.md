# Objective 2 — Web-GIS Decision-Support System (plan & status)

> Reference for the Web-GIS DSS objective. Source of truth: **AGRIKA-GIS v3**.

## What Objective 2 requires

> Develop and evaluate a **Web-based spatial decision-support system** that
> visualizes predicted **barangay-level** yields, **residual maps** (predicted −
> observed), and **seasonal productivity trends**. Evaluate via **User Acceptance
> Testing (UAT) using the ISO/IEC 25010** software-quality model.

Paper's six system modules: Home & System Info; Real-Time & Historical Yield
Monitoring; Spatial GIS Visualization; Rice Yield Analytics & Comparison; Reports
& Data Import/Export; User Access Management. Plus role-based access.

## What is done ✅

| Item | Status | Where |
|---|---|---|
| Web-GIS platform | ✅ | React 19 + Vite + Leaflet; PostGIS boundaries |
| All 6 modules scaffolded | ✅ | `Home`, `monitoring/`, `gis/`, `analytics/`, `reports/`, `admin/` |
| Municipality + barangay boundaries | ✅ | PSA data in PostGIS; choropleth + drill-in |
| Observed **and Predicted** layers | ✅ | `SpatialGIS.jsx` toggle; predictions from the final model |
| Seasonal + municipality + year filters | ✅ | yield map controls |
| Observed-vs-predicted + **residual** | ✅ | `/api/yield/compare` (observed, predicted, residual); residual handled in `SpatialGIS.jsx` |
| Role-based access | ✅ | admin / agriculturist / rice_technician (RequireRole routes) |
| Map/satellite basemap toggle | ✅ | yield map |

## Gaps / open items

1. **⚠️ Barangay-level yield is synthetic.** The barangay drill-in currently
   jitters the municipality value (placeholder), because no real barangay-level
   predictions exist yet. Tied directly to the Objective 1 barangay gap — wire
   real barangay predictions once they exist.
2. **🟠 Residual maps are municipality-level.** Residual is computed and shown at
   municipality granularity; the paper wants **barangay-level residual maps**.
   Depends on barangay predictions.
3. **⬜ UAT (ISO/IEC 25010) — NOT started.** The paper's Obj 2 evaluation:
   - Respondents: **26** agricultural personnel (24 city + 2 provincial), total enumeration.
   - Instrument: 4-point Likert, adapted from the previous AgriKA study.
   - Six quality characteristics: **functional suitability, performance efficiency,
     usability, reliability, security, maintainability.**
   - Deliverable: UAT questionnaire + results analysis (compare to previous AgriKA's
     Cronbach's α 0.8442).
4. **🟢 Module polish.** Some modules note "Needs land-use data" / "Needs land-parcel
   data" (Land Parcels view, Land use layer) — data not yet wired.

## What's left, roughly in order

1. **Barangay predictions → app** (blocked on Obj 1 barangay work) → real barangay
   heatmaps + barangay-level residual maps.
2. **UAT instrument** — build the ISO/IEC 25010 questionnaire (6 characteristics,
   4-point Likert) and the results-analysis plan; run with the 26 respondents.
3. **Fill remaining data-dependent views** (land use / land parcels) or mark them
   out of scope.

## Verdict

The Web-GIS platform and its modules are **built and wired to the real model** at
municipality level. The two headline paper features still outstanding are
**barangay-level visualization/residual maps** (blocked on Obj 1 barangay work)
and the **ISO/IEC 25010 UAT** (not yet started).
