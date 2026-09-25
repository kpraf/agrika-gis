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

// --- Research-locale showcase -------------------------------------------------
// For the dean showcase, the public views are scoped to the FOUR study cities —
// Calamba (1), Cabuyao (2), Santa Rosa (3) and Biñan (4), the only municipalities
// with barangay-level ground truth. Every other Laguna municipality is hidden
// from the map, the dropdowns and the analytics. Set this to null to restore the
// full province (nothing else needs to change).
export const RESEARCH_LOCALE_MUNICIPALITY_IDS = new Set([1, 2, 3, 4]);

const inLocale = (id) =>
  RESEARCH_LOCALE_MUNICIPALITY_IDS == null || RESEARCH_LOCALE_MUNICIPALITY_IDS.has(id);

const round3 = (n) => Math.round(n * 1000) / 1000;
const mean = (xs) => (xs.length ? round3(xs.reduce((a, b) => a + b, 0) / xs.length) : null);

// Keep only research-locale features in a boundaries FeatureCollection (this also
// reframes the map, since it fits to whatever boundaries come back).
function localeBoundaries(fc) {
  if (RESEARCH_LOCALE_MUNICIPALITY_IDS == null || !fc?.features) return fc;
  return { ...fc, features: fc.features.filter((f) => inLocale(f.properties?.municipality_id)) };
}

// Keep only research-locale rows in a { records, stats } yield payload and
// recompute the province-level stats over what's left, so the "N municipalities /
// average" readouts match what the map actually shows.
function localeYield(resp, valueKey) {
  if (RESEARCH_LOCALE_MUNICIPALITY_IDS == null || !resp?.records) return resp;
  const records = resp.records.filter((r) => inLocale(r.municipality_id));
  const vals = records.map((r) => r[valueKey]).filter((v) => v != null);
  return {
    ...resp,
    records,
    stats: {
      ...resp.stats,
      count: records.length,
      min: vals.length ? round3(Math.min(...vals)) : null,
      max: vals.length ? round3(Math.max(...vals)) : null,
      avg: mean(vals),
    },
  };
}

// Same idea for the observed-vs-predicted compare payload (different stat keys).
function localeCompare(resp) {
  if (RESEARCH_LOCALE_MUNICIPALITY_IDS == null || !resp?.records) return resp;
  const records = resp.records.filter((r) => inLocale(r.municipality_id));
  const obs = records.map((r) => r.observed).filter((v) => v != null);
  const pred = records.map((r) => r.predicted).filter((v) => v != null);
  const absRes = records.map((r) => r.residual).filter((v) => v != null).map(Math.abs);
  return {
    ...resp,
    records,
    stats: {
      ...resp.stats,
      count: records.length,
      count_predicted: pred.length,
      observed_avg: mean(obs),
      predicted_avg: mean(pred),
      mae: mean(absRes),
    },
  };
}

export const authApi = {
  login: (username, password) =>
    request("/auth/login", { method: "POST", body: { username, password } }),
  me: () => request("/auth/me", { auth: true }),
  logout: () => request("/auth/logout", { method: "POST", auth: true }),
};

export const boundariesApi = {
  municipalities: () => request("/boundaries/municipalities").then(localeBoundaries),
  barangays: (municipalityId) =>
    request(`/boundaries/barangays${municipalityId ? `?municipality_id=${municipalityId}` : ""}`),
  barangayIndex: () => request("/boundaries/barangays/index"),
};

export const yieldApi = {
  meta: () => request("/yield/meta"),
  municipalities: (year, season) =>
    request(`/yield/municipalities?year=${year}&season=${encodeURIComponent(season)}`).then(
      (r) => localeYield(r, "yield")
    ),
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
  // Observed vs predicted (+ residual) per barangay on drill-in.
  barangaysCompare: (municipalityId, year, season) =>
    request(
      `/yield/barangays/compare?municipality_id=${municipalityId}&year=${year}&season=${encodeURIComponent(season)}`
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
    request(`/yield/compare?year=${year}&season=${encodeURIComponent(season)}`).then(localeCompare),
};

// Remote-sensing / meteorological features (NDVI, rainfall, etc.) for the map's
// Environment view — per-municipality seasonal averages from the feature tables.
export const featuresApi = {
  meta: () => request("/features/meta"),
  municipalities: (year, season, metric) =>
    request(
      `/features/municipalities?metric=${encodeURIComponent(metric)}&year=${year}&season=${encodeURIComponent(season)}`
    ),
  // Per-barangay seasonal metric for a municipality (Environment drill-in);
  // only barangays with an observed yield that season are returned.
  barangays: (municipalityId, year, season, metric) =>
    request(
      `/features/barangays?municipality_id=${municipalityId}&metric=${encodeURIComponent(metric)}&year=${year}&season=${encodeURIComponent(season)}`
    ),
};

export const usersApi = {
  list: () => request("/users", { auth: true }),
  meta: () => request("/meta", { auth: true }),
  create: (payload) => request("/users", { method: "POST", body: payload, auth: true }),
  update: (id, payload) => request(`/users/${id}`, { method: "PUT", body: payload, auth: true }),
  remove: (id) => request(`/users/${id}`, { method: "DELETE", auth: true }),
};
