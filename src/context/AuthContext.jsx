import React, { createContext, useContext, useEffect, useState } from "react";
import { authApi, getToken, setToken, clearToken } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On load, if we have a token, restore the session by asking the API who we are.
  useEffect(() => {
    let active = true;
    async function restore() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const { user } = await authApi.me();
        if (active) setUser(user);
      } catch {
        clearToken(); // token invalid/expired
      } finally {
        if (active) setLoading(false);
      }
    }
    restore();
    return () => {
      active = false;
    };
  }, []);

  const login = async (username, password) => {
    const { token, user } = await authApi.login(username, password);
    setToken(token);
    setUser(user);
    return user;
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch {
      // ignore — we clear locally regardless
    }
    clearToken();
    setUser(null);
  };

  const value = {
    user,
    isAuthenticated: !!user,
    role: user?.role ?? null,
    municipality: user?.municipality ?? null,
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
