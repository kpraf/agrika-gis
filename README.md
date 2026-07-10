# Official AgriKA-GIS System

AI-powered rice yield forecasting and spatial (GIS) monitoring platform for Laguna, built on satellite imagery, weather data, and a CNN-LSTM prediction model.

## Tech Stack

- React 19 + Vite
- Tailwind CSS v4
- react-router-dom v7
- Leaflet + react-leaflet (interactive maps)
- Recharts (comparison charts)

## Getting Started

```bash
npm install
npm run dev
```

## Current Status

Frontend-only so far — there is no backend yet, and no real authentication. All 6 modules plus the public pages now have working UIs against mock/local data; everything below describes the current (stubbed) state so backend work can plug in against it.

| Page / Module | Route | Status |
|---|---|---|
| Home | `/` | Built |
| About | `/about` | Built |
| FAQ | `/faq` | Built |
| Contact | `/contact` | Built, form validates + persists via `localStorage`, **not wired to any API** (no email actually sent) |
| Portal Access (login) | `/portal-access` | UI built, **not wired to any API** |
| Module 2 — Real-Time & Historical Yield Monitoring | `/monitoring/:city` | Built, static/mock data, map uses free OpenStreetMap tiles |
| Module 3 — Spatial GIS Visualization | `/yield-map` (public), `/yield-map/:city` (guarded) | Built, static/mock data, map uses free OpenStreetMap tiles |
| Module 4 — Rice Yield Analytics & Comparison | `/analytics/:city` | Built, static/mock data, fully interactive comparison chart (Recharts) |
| Module 5 — Reports Generation & Data Import/Export | `/reports/:city` | Built, static/mock data, real CSV import/export and print-to-PDF |
| Module 6 — User Access Management & System Config | `/admin/users` | Built, static/mock data, full CRUD-lite user table (search, sort, filter, add/edit, bulk activate/deactivate/delete) |

## Access Control (important for backend integration)

Every module route except Home, About, and the public `/yield-map` overview sits behind a login wall. Right now that wall is a **hardcoded stub** in [`src/App.jsx`](src/App.jsx):

```js
function useAuth() {
  return {
    isAuthenticated: false, // always logged out for now
    role: null,
  };
}
```

Because `isAuthenticated` is always `false`, every guarded route currently redirects straight to `/portal-access`. That's expected — there's no real session yet, not a bug.

`RequireRole` (also in `App.jsx`) wraps each guarded route and checks the role against an allow-list, e.g.:

```jsx
<RequireRole allowedRoles={["agriculturist", "rice_technician"]}>
  <YieldMonitoring />
</RequireRole>
```

`administrator` always passes every guard (province-wide access), regardless of the route's allow-list.

### Roles

| Role | Access |
|---|---|
| `administrator` | Everything, all municipalities |
| `agriculturist` | Monitoring, Analytics, Reports — scoped to their own city |
| `rice_technician` | Monitoring, Reports — scoped to their own city |
| `guest` / `null` | Public pages + read-only `/yield-map` only |

### What the backend needs to provide

1. A login endpoint that accepts the email + password collected by the form in [`src/components/PortalAccess.jsx`](src/components/PortalAccess.jsx) (currently UI-only, not wired up) and returns a session/token plus the user's role.
2. A way for the frontend to check "am I logged in, and what's my role" on load/refresh — session cookie or token, whichever the backend prefers. `useAuth()` will be replaced with a real hook that calls this.
3. Once that exists, `useAuth()` in `App.jsx` swaps to the real implementation and every route above starts enforcing login for real — no other frontend changes should be needed.

Municipality-scoped routes (`/monitoring/:city`, `/analytics/:city`, `/reports/:city`) take the city as a URL param; for `agriculturist`/`rice_technician` roles the backend should also confirm that the logged-in user is actually assigned to that city (the frontend doesn't currently enforce this — it just reads the param).

### Module 5 data shape

[`ReportsExport.jsx`](src/components/reports/ReportsExport.jsx) works against an in-memory record shape of `{ municipality, year, season, yield, status }` — currently seeded with mock data and mutable client-side via CSV import. Once there's a real endpoint for yield records, swap `DEFAULT_RECORDS` for a fetch and the rest (filters, stats, chart, export) keeps working unchanged. Note the CSV parser was hand-written as a plain character-by-character state machine specifically to avoid regex-based parsing on user-uploaded files (some popular CSV/Excel libraries have known ReDoS vulnerabilities) — keep that in mind if this gets replaced with a library later.

### Module 6 data shape

[`UserAccessManagement.jsx`](src/components/admin/UserAccessManagement.jsx) works against `{ id, name, handle, email, role, municipality, status, lastActive }`, seeded locally and mutated client-side (add/edit/status-toggle/delete all currently just update React state, nothing persists on refresh). This is the one page where the backend contract matters most: it needs real user CRUD endpoints (create/list/update/delete) plus whatever enforces that `agriculturist`/`rice_technician` accounts are actually scoped to their assigned `municipality` server-side — this page only edits that field client-side, it doesn't enforce it.
