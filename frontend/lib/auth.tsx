"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type Role = "admin" | "user";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

const TOKEN_KEY = "contractiq_token";
const AuthContext = createContext<AuthState | null>(null);

let currentToken: string | null = null;
/** Read by the API client so every request carries the bearer token. */
export function getToken() {
  return currentToken;
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as any)?.detail || `Request failed (${res.status})`);
  return data as T;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const apply = useCallback((tok: string, usr: AuthUser) => {
    currentToken = tok;
    setToken(tok);
    setUser(usr);
    try { localStorage.setItem(TOKEN_KEY, tok); } catch {}
  }, []);

  const logout = useCallback(() => {
    currentToken = null;
    setToken(null);
    setUser(null);
    try { localStorage.removeItem(TOKEN_KEY); } catch {}
  }, []);

  // Restore a saved session on first load.
  useEffect(() => {
    let tok: string | null = null;
    try { tok = localStorage.getItem(TOKEN_KEY); } catch {}
    if (!tok) { setLoading(false); return; }
    currentToken = tok;
    fetch("/api/auth/me", { headers: { Authorization: `Bearer ${tok}` } })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((u: AuthUser) => { setToken(tok); setUser(u); })
      .catch(() => logout())
      .finally(() => setLoading(false));
  }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await postJson<{ access_token: string; user: AuthUser }>("/api/auth/login", { email, password });
    apply(data.access_token, data.user);
  }, [apply]);

  const signup = useCallback(async (email: string, password: string, fullName: string) => {
    const data = await postJson<{ access_token: string; user: AuthUser }>("/api/auth/signup", {
      email, password, full_name: fullName,
    });
    apply(data.access_token, data.user);
  }, [apply]);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
