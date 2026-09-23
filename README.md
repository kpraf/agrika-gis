# AgriKA-GIS

AgriKA-GIS is a web-based rice yield forecasting and spatial (GIS) monitoring platform for the
province of Laguna. It combines satellite imagery, weather data, and a CNN-LSTM deep-learning
model to estimate rice yields, and presents them on interactive maps and dashboards for local
government units and agriculturists.

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
│  ├─ auth.py / users.py / boundaries.py / yields.py / features.py   # API routes
│  ├─ models.py               # Database models
│  ├─ db/                     # SQL schema, seed data, real yield CSVs, GeoJSON boundaries
│  └─ scripts/                # Setup + data-loading helpers (DB, boundaries, yields, users)
└─ README.md                  # this file
```

## Data

Administrative boundaries (province, 30 municipalities/cities, 682 barangays) are official
Philippine Statistics Authority (PSA) data, prepared in QGIS and stored as PostGIS geometry.
Historical municipality-level yields come from the Ricelytics dataset; barangay-level yields for
Biñan, Cabuyao, and Santa Rosa come from local agriculture office records. Both are shipped as
CSVs in `backend/db/` and loaded by the scripts in **Step 6** below — a fresh database is empty
until you run them.

---

# Local Setup Guide

This gets the project running on a **Windows** laptop from scratch, with the real yield and
boundary data loaded (not just placeholder rows). Follow it top to bottom the first time — it
assumes no prior experience with databases or servers.

The app has two parts that both need to run at once, in **two separate terminals**:

- **Frontend** — the website you see in the browser (React + Vite) → `http://localhost:5173`
- **Backend** — the API + database it talks to (Flask + PostgreSQL) → `http://localhost:5000`

## Step 1 — Install the prerequisites (one time)

Download and install these, in order. Accept the default options unless noted.

| Tool | Version | Download | Notes |
|---|---|---|---|
| **Git** | latest | https://git-scm.com/download/win | To clone the repo |
| **Node.js** | 18 LTS or newer | https://nodejs.org | For the frontend |
| **Python** | 3.11–3.14 | https://www.python.org/downloads/ | ✅ **Tick "Add python.exe to PATH"** during install |
| **PostgreSQL** | 18 | https://www.postgresql.org/download/windows/ | ⚠️ **Write down the password** you set for the `postgres` user — you'll need it |
| **PostGIS** | 3.x | via Stack Builder, see below | Adds map/boundary support to PostgreSQL — required for the real 682-barangay map |

**Installing PostGIS:**
1. After PostgreSQL finishes installing, it offers to launch **Stack Builder** — or open
   **"Application Stack Builder"** from the Start menu.
2. In the dropdown, pick **"PostgreSQL 18 (x64) on port 5432"** → **Next**.
3. Expand **"Spatial Extensions"**, tick **"PostGIS 3.x Bundle for PostgreSQL 18"** → **Next** → download.
4. Run the installer with defaults. If it asks to set environment variables, click **Yes**.
   If it asks "Create spatial database?", click **No**.

**Check the installs:**
```bash
python --version
node --version
git --version
```

## Step 2 — Get the code

```bash
git clone <the-repo-url> agrika-gis
cd agrika-gis
```

(Replace `<the-repo-url>` with the actual GitHub link for this project.)

## Step 3 — Set up the database (one time)

This creates the `agrika_gis` database and loads the schema. From the project root, run:

```bash
powershell -ExecutionPolicy Bypass -File .\backend\db\setup_db.ps1
```

- It asks for the **`postgres` password** you set during PostgreSQL install.
- When it finishes it prints **"Database is ready!"** and writes `backend/.env` (your local
  connection settings — private, not committed to git).
- If it says PostGIS isn't installed, go back to **Step 1** and install it via Stack Builder,
  then re-run this script.

## Step 4 — Set up the backend Python environment (one time)

```bash
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
cd ..
```

That creates an isolated Python environment and installs Flask, SQLAlchemy, GeoAlchemy2, etc.
(takes a minute or two).

## Step 5 — Load the real map boundaries (one time)

From the `backend` folder, load the official Laguna boundaries (30 municipalities + 682
barangays) into PostGIS:

```bash
cd backend
.\venv\Scripts\python.exe scripts\import_boundaries.py
```

This also clears the handful of placeholder sample rows from `setup_db.ps1`'s seed data, so the
next step is what actually populates real yields.

## Step 6 — Load the real yield & prediction data (one time)

Still from the `backend` folder, with the venv active, run these in order:

```bash
# Historical municipality-level yields (Ricelytics dataset)
.\venv\Scripts\python.exe scripts\load_municipality_yield.py --csv db\ricelytics_laguna_yield.csv

# CNN-LSTM model predictions (powers the Predicted / residual overlay)
.\venv\Scripts\python.exe scripts\load_municipality_predictions.py --csv db\cnn_lstm_predictions_for_app.csv --model-version cnn-lstm-v1

# Barangay-level observed yields, one file per municipality that has data so far
.\venv\Scripts\python.exe scripts\load_barangay_yield.py --csv db\barangay_yield_city-of-binan.csv
.\venv\Scripts\python.exe scripts\load_barangay_yield.py --csv db\barangay_yield_city-of-cabuyao.csv
.\venv\Scripts\python.exe scripts\load_barangay_yield.py --csv db\barangay_yield_city-of-santa-rosa.csv
```

Optional — monthly weather/satellite features (NDVI, EVI, NDWI, rainfall, temperature, humidity)
that back the Analytics overlays:

```bash
.\venv\Scripts\python.exe scripts\load_feature_tables.py
```

All of these are idempotent (safe to re-run — they upsert rather than duplicate), so if you pull
updated CSVs later you can just re-run the relevant command.

## Step 7 — Create your login account (one time)

```bash
.\venv\Scripts\python.exe scripts\create_user.py
```

Pick a username, password, and role when prompted.
- For an admin who can see everything, choose **administrator**.
- **Agriculturist** / **rice_technician** accounts are scoped to one municipality.

You can create more accounts later the same way, or from **User Access Management** in the app
once you're logged in as an admin.

## Step 8 — Set up the frontend (one time)

Open a **second terminal** at the project root (`agrika-gis`) and run:

```bash
npm install
```

Then create your local frontend env file:

```bash
copy .env.example .env
```

`.env` works as-is for local dev. The one optional setting is `VITE_CARTO_API_KEY` — without it
the map still works, just with a small "API key required" watermark on the base tiles. Get a
free key (up to 5,000,000 tile requests/month) at https://carto.com/basemaps and paste it into
`.env` if you want the watermark gone.

## Step 9 — Run it (every time you work on the project)

You need **both** servers running at once, in **two separate terminals**.

**Terminal 1 — backend** (from the `backend` folder):
```bash
.\venv\Scripts\python.exe app.py
```
Leave it running. It serves the API on `http://localhost:5000`.

**Terminal 2 — frontend** (from the project root):
```bash
npm run dev
```
Leave it running too. It serves the site on `http://localhost:5173`.

Open **http://localhost:5173**, click **Portal Access**, and log in with the account you created
in Step 7. The map and dashboards should now show the real Laguna boundaries and yield data.

### Quick reference (after the one-time setup above)

```bash
# Terminal 1 (backend)
cd backend
.\venv\Scripts\python.exe app.py

# Terminal 2 (frontend, from project root)
npm run dev
```

To stop either server, click its terminal and press **Ctrl + C**.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Login says **"Can't reach the server"** | The backend (Terminal 1) isn't running. Start it. |
| `setup_db.ps1` says **connection failed** | Wrong `postgres` password. Re-run and re-enter it. |
| `setup_db.ps1` says **PostGIS not installed** | Install PostGIS via Stack Builder (Step 1), then re-run. |
| `python` **not recognized** | Python wasn't added to PATH. Reinstall Python and tick "Add to PATH". |
| `npm` **not recognized** | Install Node.js (Step 1) and reopen the terminal. |
| Map shows no boundaries, or only 10 municipalities / 5 barangays | You haven't run `import_boundaries.py` yet (Step 5) — you're still looking at the placeholder seed data. |
| Monitoring/Analytics pages are empty | Run the data-loading commands in Step 6; make sure the backend is running. |
| Map has an "API key required" watermark | Cosmetic only. Add a free `VITE_CARTO_API_KEY` in `.env` (Step 8) to remove it. |
| Port 5000 or 5173 already in use | Close the old terminal running it, or restart your laptop. |

Your local secrets (`backend/.env`, `.env`) and the Python environment (`backend/venv`) are
**not** in git on purpose — everyone generates their own by following this guide.

## Team

Developed as an undergraduate thesis project. See the **About** page in the app for the
research team and collaborators.
