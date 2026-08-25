import { createContext, useContext, useEffect, useState } from "react";
import * as authApi from "../api/authApi";

const STORAGE_KEY = "procurement_token";
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  // "loading" | "authenticated" | "anonymous"
  const [status, setStatus] = useState("loading");

  // On first load, see if a token was saved from a previous session and
  // check it's still valid before trusting it.
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) {
      setStatus("anonymous");
      return;
    }
    authApi
      .me(saved)
      .then((data) => {
        setToken(saved);
        setUser(data.user);
        setStatus("authenticated");
      })
      .catch(() => {
        localStorage.removeItem(STORAGE_KEY);
        setStatus("anonymous");
      });
  }, []);

  const handleAuthResponse = (data) => {
    localStorage.setItem(STORAGE_KEY, data.token);
    setToken(data.token);
    setUser(data.user);
    setStatus("authenticated");
  };

  const login = async (email, password) => {
    const data = await authApi.login(email, password);
    handleAuthResponse(data);
  };

  const register = async (email, password) => {
    const data = await authApi.register(email, password);
    handleAuthResponse(data);
  };

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
    setUser(null);
    setStatus("anonymous");
  };

  return (
    <AuthContext.Provider value={{ user, token, status, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
