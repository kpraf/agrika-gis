# AgriKA-GIS — Progress Report Timetable

Single source of truth for the thesis progress-report schedule: **what is due when**,
**who owns it**, whether it is an **interface** deliverable (clicked through in the demo)
or a **backend** deliverable (reported as a milestone, evidence shown only if asked),
and which of the four Saturday progress reports it falls under.

> **Dates are confirmed from the team's Excel timetable; roles are from the CCIS Authors'
> Contribution Form.** Update this file whenever the schedule changes; treat it as the basis
> for every scope and deadline decision.
>
> _Last updated: 2026-09-19. Report 1 & 2 windows confirmed; Report 3 & 4 windows pending._

## Legend

- 🖥️ **Interface — demo it.** A screen the teacher clicks through.
- ⚙️ **Backend — report it.** A model/pipeline milestone; show results/logs only if asked.
- Status: `Done` · `In progress` · `Scheduled`

---

## Progress report schedule

**Five reports**, presented on Saturdays. All modules are delivered by Report 2 (Sep 24),
so Reports 3–5 are testing, integration, and — paced deliberately — manuscript work.

| Report | Coverage | Presented | Notes |
|---|---|---|---|
| **Report 1** | Aug 31 – **Sep 18, 2026** | _(confirm)_ | Extended from Sep 11 → Sep 18 |
| **Report 2** | **Sep 19 – 25, 2026** | _(confirm)_ | Module 3 finish + Modules 4 & 5 |
| **Report 3** | _(confirm)_ | _(confirm)_ | Testing / integration; light paper |
| **Report 4** | _(confirm)_ | _(confirm)_ | Testing; manuscript |
| **Report 5** | _(confirm)_ | _(confirm)_ | Finalization + defense prep |

> **Pacing note:** the paper is spread across all five reports on purpose — do **not** advance it
> too fast in the early reports. Report 1 = outlines, Report 2 = initial organizing/drafting,
> Reports 3–5 = drafting → finalizing.

---

## Team roles (from the Contribution Form)

| Member | Paper | Project ownership |
|---|---|---|
| **Argana, Ma. Ashlie Nicole C.** | Ch 5 **Lead** | Module 1 (Home & System Info) · Objective 1 model features (S1 SAR, S2 indices) |
| **Ilagan, Joshua Xantino P.** | Ch 4 **Co** | Module 4 (Analytics) · Module 5 (Reports) |
| **Madolora, Jean Christian O.** | Ch 5 **Co** | Module 2 (Yield Monitoring) · Objective 3 (Data Pipeline) |
| **Praferosa, Kester Shaan L.** | Ch 4 **Lead** | Module 3 (Spatial GIS) · Module 6 (User Access Management) |

---

## Deliverables & deadlines

### Objective 1 — Extended CNN-LSTM Prediction Model
**Owner:** Argana · **Type:** ⚙️ Backend

| Item | Target | Report | Status |
|---|---|---|---|
| Sentinel-1 SAR backscatter (VV/VH) + soil-moisture extraction | 9/7 | 1 | Done |
| Sentinel-2 vegetation indices (NDVI, EVI, Green Ratio) | 9/7 | 1 | Done |
| Extended CNN-LSTM architecture (S1 + S2 + meteorological + historical yield) | 9/8 | 1 | Done |
| Barangay-level model training & evaluation | 9/9 | 1 | In progress |

### Module 1 — Home & System Information
**Owner:** Argana · **Type:** 🖥️ Interface

| Item | Target | Report | Status |
|---|---|---|---|
| Landing / Home page | 8/24 | 1 | Done |
| About page | 8/24 | 1 | Done |
| FAQ page | 8/24 | 1 | Done |
| Contact page | 8/24 | 1 | Done |
| Portal Access | 8/24 | 1 | Done |

### Module 6 — User Access Management & System Configuration
**Owner:** Praferosa · **Type:** 🖥️ Interface

| Item | Target | Report | Status |
|---|---|---|---|
| User account creation & management | 8/26 | 1 | Done |
| Role-based access control (Administrator / Agriculturist / Rice Technician) | 8/26 | 1 | Done |
| Municipality-scoped data access | 8/26 | 1 | Done |
| Authentication (login / session handling) | 8/26 | 1 | Done |

### Objective 3 — Secure Automated Data Pipeline
**Owner:** Madolora · **Type:** ⚙️ Backend

| Item | Target | Report | Status |
|---|---|---|---|
| Automated Sentinel-1 / Sentinel-2 acquisition (Sentinel Hub API) | 9/10 | 1 | Done |
| Open-Meteo weather data sync | 9/10 | 1 | Done |
| Image preprocessing (clipping, co-registration, masking, indices) | 9/11 | 1 | Done |
| Secure integration into spatial database | 9/11 | 1 | Done |

### Module 2 — Real-Time & Historical Yield Monitoring
**Owner:** Madolora · **Type:** 🖥️ Interface

| Item | Target | Report | Status |
|---|---|---|---|
| Current-season yield monitoring view (by municipality) | 9/14 | 1 | Done |
| Historical yield records view | 9/15 | 1 | Done |
| Season-over-season / time-series comparison | 9/15 | 1 | Done |

### Module 3 — Spatial GIS Visualization & Analysis
**Owner:** Praferosa · **Type:** 🖥️ Interface

| Item | Target | Report | Status |
|---|---|---|---|
| Interactive Laguna map w/ municipality & barangay boundaries (PostGIS) | 9/17 | 1 | Done |
| Yield heatmap layer | 9/17 | 1 | Done |
| Residual (over-/under-prediction) map layer | 9/18 | 1 | Done |
| Clean-map / satellite basemap toggle | 9/18 | 1 | Done |
| City / barangay / year / season filters | 9/21 | 2 | In progress |
| Drill-down from municipality to barangay view | 9/21 | 2 | In progress |

### Module 4 — Rice Yield Analytics & Comparison
**Owner:** Ilagan · **Type:** 🖥️ Interface

| Item | Target | Report | Status |
|---|---|---|---|
| Charts comparing yield across municipalities & seasons | 9/22 | 2 | Scheduled |
| Predicted-vs-recorded yield comparison | 9/22 | 2 | Scheduled |
| Summary statistics tables | 9/22 | 2 | Scheduled |

### Module 5 — Reports Generation & Data Import/Export
**Owner:** Ilagan · **Type:** 🖥️ Interface

| Item | Target | Report | Status |
|---|---|---|---|
| PDF report export | 9/24 | 2 | Scheduled |
| Excel report export | 9/24 | 2 | Scheduled |
| CSV report export | 9/24 | 2 | Scheduled |
| CSV data import | 9/24 | 2 | Scheduled |

---

## Demo build scope (`report-1-scope` branch)

The demo branch shows only the modules whose deadlines have landed for the current report,
so the interface the teacher clicks matches the timetable.

| Through | Demo shows (🖥️) | Reported as milestone (⚙️) | Held out |
|---|---|---|---|
| **Sep 18 (Report 1)** | Modules 1, 2, 3, 6 | Objective 1, Objective 3 | Module 4 (9/22), Module 5 (9/24) |
| **Sep 25 (Report 2)** | Modules 1–6 (adds Module 3 filters + drill-down, Modules 4 & 5) | — | — |
