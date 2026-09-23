// Thin client for the AgriKA-GIS Flask API.
// Base URL can be overridden with VITE_API_URL; defaults to the local Flask dev server.
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000/api";

const TOKEN_KEY = "agrika-gis:token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

/**
 * Lightweight health check — returns true if the API answers /health OK.
 * Deliberately bypasses request()/the slow overlay so it can be polled quietly
 * (e.g. the login page waiting for a free-tier backend to wake up).
 */
export async function pingHealth(timeoutMs = 8000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: ctrl.signal });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

// --- "server waking up" signal -----------------------------------------------
// Free hosting (Render) sleeps the API after idle, so the first request can take
// 30-60s. We flag any request that stays pending past a threshold so the UI can
// show a "waking the server" overlay, and clear it once the request resolves.
const SLOW_MS = 2500;
const slowListeners = new Set();
let slowCount = 0;

const emitSlow = () => {
  const active = slowCount > 0;
  slowListeners.forEach((cb) => cb(active));
};

/** Subscribe to server-slow state. cb(active). Returns an unsubscribe fn. */
export function onServerSlow(cb) {
  slowListeners.add(cb);
  return () => slowListeners.delete(cb);
}

// --- GET response cache (module-level, per session) --------------------------
// The reference data this app reads — municipality/barangay boundaries,
// per-year/season yields, feature metrics, meta — is static within a session,
// yet every screen refetches it on mount (React Router remounts re-run the
// effects). We memoise GET responses by URL: concurrent callers share one
// in-flight promise (dedupe), and later callers reuse the resolved value until
// the cache is cleared. Any mutating request (POST/PUT/DELETE) clears the cache
// so lists can't go stale, and clearApiCache() is called on login/logout.
//
// Note: cached responses are shared by reference — callers must treat them as
// read-only (don't mutate the returned object in place).
const getCache = new Map();

/** Drop every cached GET response. Call on auth changes (login/logout). */
export function clearApiCache() {
  getCache.clear();
}

// The actual network call, plus the "server waking up" slow signal.
async function performRequest(path, { method, body, auth }) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let markedSlow = false;
  const slowTimer = setTimeout(() => {
    markedSlow = true;
    slowCount += 1;
    emitSlow();
  }, SLOW_MS);

  try {
    let res;
    try {
      res = await fetch(`${API_BASE}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch {
      // Network / server-down
      throw new Error("Can't reach the server. Is the backend running?");
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || `Request failed (${res.status}).`);
    }
    return data;
  } finally {
    clearTimeout(slowTimer);
    if (markedSlow) {
      slowCount -= 1;
      emitSlow();
    }
  }
}

async function request(path, { method = "GET", body, auth = false, cache } = {}) {
  // Cache GETs by default; never cache mutations. Pass `cache: false` to opt out.
  const shouldCache = (cache ?? true) && method === "GET";
  // Auth'd and anonymous reads of the same path are kept under separate keys.
  const key = shouldCache ? `${auth ? "auth:" : ""}${path}` : null;

  if (key && getCache.has(key)) return getCache.get(key);

  const pending = performRequest(path, { method, body, auth });

  if (key) {
    // Store the promise so concurrent callers dedupe; evict on failure so a
    // later call can retry instead of caching the rejection.
    getCache.set(key, pending);
    pending.catch(() => getCache.delete(key));
  } else if (method !== "GET") {
    // A successful mutation may have changed server state → drop cached reads.
    pending.then(() => getCache.clear(), () => {});
  }

  return pending;
}

export const authApi = {
  login: (username, password) =>
    request("/auth/login", { method: "POST", body: { username, password } }),
  me: () => request("/auth/me", { auth: true }),
  logout: () => request("/auth/logout", { method: "POST", auth: true }),
};

export const boundariesApi = {
  municipalities: () => request("/boundaries/municipalities"),
  barangays: (municipalityId) =>
    request(`/boundaries/barangays${municipalityId ? `?municipality_id=${municipalityId}` : ""}`),
  barangayIndex: () => request("/boundaries/barangays/index"),
};

export const yieldApi = {
  meta: () => request("/yield/meta"),
  municipalities: (year, season) =>
    request(`/yield/municipalities?year=${year}&season=${encodeURIComponent(season)}`),
  // Real per-barangay observed yields for a municipality (from barangay_yield).
  barangays: (municipalityId, year, season) =>
    request(
      `/yield/barangays?municipality_id=${municipalityId}&year=${year}&season=${encodeURIComponent(season)}`
    ),
  // Municipalities that have any per-barangay data (Analytics barangay picker).
  barangayMunicipalities: () => request("/yield/barangays/municipalities"),
  // Flat list of every observed barangay yield for one municipality (Reports).
  barangayRecords: (municipalityId) =>
    request(`/yield/barangays/records?municipality_id=${municipalityId}`),
  // Year-over-year yield per barangay of one municipality, for a season.
  barangaySeries: (municipalityId, season) =>
    request(
      `/yield/barangays/series?municipality_id=${municipalityId}&season=${encodeURIComponent(season)}`
    ),
  trend: (season, municipalityId) =>
    request(
      `/yield/trend?season=${encodeURIComponent(season)}${
        municipalityId ? `&municipality_id=${municipalityId}` : ""
      }`
    ),
  records: () => request("/yield/records"),
  // Import observed yields from a CSV (admin/agriculturist/technician).
  // level = "municipality" | "barangay". Server validates + upserts; returns a report.
  importCsv: (csvText, level, source) =>
    request("/yield/import", { method: "POST", body: { csv: csvText, level, source }, auth: true }),
  predictionsMeta: () => request("/yield/predictions/meta"),
  compare: (year, season) =>
    request(`/yield/compare?year=${year}&season=${encodeURIComponent(season)}`),
};

// Remote-sensing / meteorological features (NDVI, rainfall, etc.) for the map's
// Environment view — per-municipality seasonal averages from the feature tables.
export const featuresApi = {
  meta: () => request("/features/meta"),
  municipalities: (year, season, metric) =>
    request(
      `/features/municipalities?metric=${encodeURIComponent(metric)}&year=${year}&season=${encodeURIComponent(season)}`
    ),
};

export const usersApi = {
  list: () => request("/users", { auth: true }),
  meta: () => request("/meta", { auth: true }),
  create: (payload) => request("/users", { method: "POST", body: payload, auth: true }),
  update: (id, payload) => request(`/users/${id}`, { method: "PUT", body: payload, auth: true }),
  remove: (id) => request(`/users/${id}`, { method: "DELETE", auth: true }),
};
