# AgriKA-GIS

AgriKA-GIS is a web-based rice yield forecasting and spatial (GIS) monitoring platform for the
province of Laguna. It combines satellite imagery, weather data, and a CNN-LSTM deep-learning
model to estimate rice yields, and presents them on interactive maps and dashboards for local
government units and agriculturists.

> **`report-1-scope` branch — Week 1 progress build (Aug 31 – Sept 11, 2026).**
> This branch is deliberately limited to the modules reported in Progress Report 1:
> **Module 1 — Home & System Information** (Landing, About, FAQ, Contact, Portal Access),
> **Module 6 — User Access Management & System Configuration**, and the backend
> **CNN-LSTM model features** and **automated data pipeline**. The Monitoring, Spatial GIS,
> Analytics, and Reports modules are scheduled for the succeeding reports and are not part of
> this build. See the full-system feature list below for the complete planned scope.

## Features

**Public site** (no login needed)
- Landing, About, FAQ, and Contact pages
- Public **Yield Map** — a read-only interactive map of Laguna's rice-producing areas

**Portal** (login required)
- **Yield Monitoring** — real-time and historical rice yield views by municipality
- **Spatial GIS Visualization** — interactive Laguna map with real municipality and barangay
  boundaries (from PostGIS); click a municipality to drill into its barangays, switch between
  a clean map and satellite imagery, toggle layers
- **Rice Yield Analytics & Comparison** — compare yields across municipalities and seasons
- **Reports & Data Import/Export** — generate reports, import CSV data, export to CSV/PDF
- **User Access Management** — admins create and manage portal accounts and roles

## Tech Stack

**Frontend:** React 19 + Vite · Tailwind CSS v4 · react-router-dom · Leaflet / react-leaflet
(maps) · Recharts (charts)

**Backend:** Flask (Python) · PostgreSQL 18 + PostGIS · SQLAlchemy · JWT authentication

## Getting Started

See **[SETUP.md](SETUP.md)** for the full, step-by-step setup (installing prerequisites, setting
up the database, and running the app). In short, once everything is installed:

```bash
# Backend — terminal 1
cd backend && .\venv\Scripts\python.exe app.py    # http://localhost:5000

# Frontend — terminal 2 (from the project root)
npm run dev                                        # http://localhost:5173
```

Then open **http://localhost:5173** and sign in through **Portal Access**.

## Roles & Access

There are three portal roles. The general public does not log in — they browse the public pages
and the read-only yield map.

| Role | Access |
|---|---|
| **Administrator** (provincial) | Full access to every module, all municipalities |
| **Agriculturist** | Monitoring, Analytics, and Reports — scoped to their assigned municipality |
| **Rice Technician** | Monitoring and Reports — scoped to their assigned municipality |
| **Public** (not logged in) | Public pages + read-only yield map only |

## Project Structure

```
agrika-gis/
├─ src/                       # Frontend (React)
│  ├─ components/             # Pages and UI components
│  ├─ context/                # Auth context
│  └─ lib/                    # API client
├─ backend/                   # Backend (Flask API)
│  ├─ app.py                  # API entry point
│  ├─ auth.py / users.py / boundaries.py   # API routes
│  ├─ models.py               # Database models
│  ├─ db/                     # SQL schema, seed data, and Laguna GeoJSON boundaries
│  └─ scripts/                # Setup helpers (DB, boundary import, user creation)
├─ SETUP.md                   # Local setup guide
└─ README.md
```

## Data

Administrative boundaries (province, 30 municipalities/cities, 682 barangays) are official
Philippine Statistics Authority (PSA) data, prepared in QGIS and stored as PostGIS geometry.

## Team

Developed as an undergraduate thesis project. See the **About** page in the app for the
research team and collaborators.
