import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "agrika-gis:session";

/**
 * TEMPORARY mock account store — replace with the Flask API once it exists.
 * These credentials ship in the client bundle, so they are demo-only and offer
 * zero real security. When the backend lands, only login() below changes
 * (to a fetch against the login endpoint); the rest of the app keeps working.
 *
 * city uses the same slug format as the /:city route params (e.g. "calamba",
 * "los-banos"). Administrators have city: null (province-wide).
 */
const MOCK_USERS = [
  {
    email: "kpraferosa28@gmail.com",
    password: "agrika2026",
    name: "Kester Praferosa",
    role: "administrator",
    city: null,
  },
  {
    email: "agriculturist.demo@agrika-gis.gov.ph",
    password: "agrika2026",
    name: "Demo Agriculturist",
    role: "agriculturist",
    city: "calamba",
  },
  {
    email: "technician.demo@agrika-gis.gov.ph",
    password: "agrika2026",
    name: "Demo Rice Technician",
    role: "rice_technician",
    city: "calamba",
  },
];

const AuthContext = createContext(null);

function readSession() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(readSession);

  useEffect(() => {
    if (user) localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    else localStorage.removeItem(STORAGE_KEY);
  }, [user]);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: !!user,
      role: user?.role ?? null,
      login: (email, password) => {
        const match = MOCK_USERS.find(
          (u) => u.email.toLowerCase() === email.trim().toLowerCase() && u.password === password
        );
        if (!match) return { ok: false, error: "Invalid email or password." };
        const session = { email: match.email, name: match.name, role: match.role, city: match.city };
        setUser(session);
        return { ok: true, user: session };
      },
      logout: () => setUser(null),
    }),
    [user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

/** Where a user lands right after login if they didn't come from a guarded page. */
export function roleHome(user) {
  if (!user) return "/portal-access";
  if (user.role === "administrator") return "/admin/users";
  return `/monitoring/${user.city}`;
}
