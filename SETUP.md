# AgriKA-GIS — Local Setup Guide

This guide gets the project running on a **Windows** laptop from scratch. Follow it top to
bottom the first time. It assumes no prior experience with databases or servers.

The app has two parts that both need to run:

- **Frontend** — the website you see in the browser (React + Vite), runs on `http://localhost:5173`
- **Backend** — the API + database it talks to (Flask + PostgreSQL), runs on `http://localhost:5000`

You'll open **two terminals** to run both at once.

---

## 1. Install the prerequisites (one time)

Download and install these, in order. Accept the default options unless noted.

| Tool | Version | Download | Notes |
|---|---|---|---|
| **Git** | latest | https://git-scm.com/download/win | To clone the repo |
| **Node.js** | 18 LTS or newer | https://nodejs.org | For the frontend |
| **Python** | 3.11–3.14 | https://www.python.org/downloads/ | ✅ **Tick "Add python.exe to PATH"** during install |
| **PostgreSQL** | 18 | https://www.postgresql.org/download/windows/ | ⚠️ **Write down the password** you set for the `postgres` user — you'll need it |
| **PostGIS** | 3.x | (installed via Stack Builder, see below) | Adds map/boundary support to PostgreSQL |

### Installing PostGIS (needed for the map boundaries)

1. After PostgreSQL finishes installing, it offers to launch **Stack Builder** — or open
   **"Application Stack Builder"** from the Start menu.
2. In the dropdown, pick **"PostgreSQL 18 (x64) on port 5432"** → **Next**.
3. Expand **"Spatial Extensions"**, tick **"PostGIS 3.x Bundle for PostgreSQL 18"** → **Next** → download.
4. Run the installer with defaults. If it asks to set environment variables, click **Yes**.
   If it asks "Create spatial database?", click **No**.

> **Check:** to confirm Python is installed, open a terminal and run `python --version`.
> For Node, run `node --version`.

---

## 2. Get the code

Open a terminal (PowerShell) in the folder where you keep projects, then:

```bash
git clone <the-repo-url> agrika-gis
cd agrika-gis
```

(Replace `<the-repo-url>` with the actual GitHub/repo link from your group.)

---

## 3. Set up the database (one time)

This creates the `agrika_gis` database, loads the tables, and saves the connection settings.

From the project root (`agrika-gis`), run:

```bash
powershell -ExecutionPolicy Bypass -File .\backend\db\setup_db.ps1
```

- It will ask for the **`postgres` password** you set during PostgreSQL install — type it and press Enter.
- When it finishes it prints **"Database is ready!"** and creates `backend/.env` (your local
  connection settings — this file is private and is not shared in git).

> If it says PostGIS isn't installed, go back to **step 1** and install it via Stack Builder, then re-run this.

---

## 4. Set up the backend (one time)

```bash
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

That creates an isolated Python environment and installs Flask, etc. (takes a minute or two).

Now load the real Laguna map boundaries into the database (30 municipalities + 682 barangays):

```bash
.\venv\Scripts\python.exe scripts\import_boundaries.py
```

Then create your own login account (pick a username, password, and role when prompted):

```bash
.\venv\Scripts\python.exe scripts\create_user.py
```

> For an admin who can see everything, choose the **administrator** role.
> Agriculturist / rice technician accounts are scoped to one municipality.

Stay in the `backend` folder for the next step.

---

## 5. Set up the frontend (one time)

Open a **second terminal** at the project root (`agrika-gis`) and run:

```bash
npm install
```

That downloads the frontend packages (takes a minute).

---

## 6. Run it (every time you work on the project)

You need **both** running at the same time, in **two separate terminals**.

**Terminal 1 — backend** (from the `backend` folder):

```bash
.\venv\Scripts\python.exe app.py
```

Leave it running. It serves the API on `http://localhost:5000`.

**Terminal 2 — frontend** (from the project root `agrika-gis`):

```bash
npm run dev
```

Leave it running too. It serves the site on `http://localhost:5173`.

Now open **http://localhost:5173** in your browser. Click **Portal Access** and log in with the
account you created in step 4.

To stop either server, click its terminal and press **Ctrl + C**.

---

## Quick reference (after the one-time setup)

```bash
# Terminal 1 (backend)
cd backend
.\venv\Scripts\python.exe app.py

# Terminal 2 (frontend, from project root)
npm run dev
```

Open http://localhost:5173

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Login says **"Can't reach the server"** | The backend (Terminal 1) isn't running. Start it. |
| `setup_db.ps1` says **connection failed** | Wrong `postgres` password. Re-run and re-enter it. |
| `setup_db.ps1` says **PostGIS not installed** | Install PostGIS via Stack Builder (step 1), then re-run. |
| `python` **not recognized** | Python wasn't added to PATH. Reinstall Python and tick "Add to PATH". |
| `npm` **not recognized** | Install Node.js (step 1) and reopen the terminal. |
| Map shows no boundaries | Run `scripts\import_boundaries.py` (step 4); make sure the backend is running. |
| Port 5000 or 5173 already in use | Close the old terminal running it, or restart your laptop. |

---

## Creating more accounts later

Anytime, from the `backend` folder (with the backend set up):

```bash
.\venv\Scripts\python.exe scripts\create_user.py
```

Admins can also add/edit/remove users from the **User Access Management** page inside the app
(the Settings icon in the sidebar).

---

## What's in the project

```
agrika-gis/
├─ src/                  # Frontend (React) — pages, components
├─ backend/              # Backend (Flask API + database scripts)
│  ├─ app.py             # API entry point
│  ├─ db/                # SQL schema + the Laguna GeoJSON boundaries
│  └─ scripts/           # setup helpers (import boundaries, create users)
├─ SETUP.md              # this file
└─ README.md             # project overview + module status
```

Your local secrets (`backend/.env`) and the Python environment (`backend/venv`) are **not** in
git on purpose — everyone generates their own by following this guide.
