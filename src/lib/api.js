// Thin client for the AgriKA-GIS Flask API.
// Base URL can be overridden with VITE_API_URL; defaults to the local Flask dev server.
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:5000/api";

const TOKEN_KEY = "agrika-gis:token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

async function request(path, { method = "GET", body, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

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
};

export const yieldApi = {
  meta: () => request("/yield/meta"),
  municipalities: (year, season) =>
    request(`/yield/municipalities?year=${year}&season=${encodeURIComponent(season)}`),
};

export const usersApi = {
  list: () => request("/users", { auth: true }),
  meta: () => request("/meta", { auth: true }),
  create: (payload) => request("/users", { method: "POST", body: payload, auth: true }),
  update: (id, payload) => request(`/users/${id}`, { method: "PUT", body: payload, auth: true }),
  remove: (id) => request(`/users/${id}`, { method: "DELETE", auth: true }),
};
