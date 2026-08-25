import { createContext, useContext, useEffect, useState } from "react";
import * as authApi from "../api/authApi";

const STORAGE_KEY = "procurement_token";
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    const cleanToken = saved?.trim();

    if (!cleanToken) {
      localStorage.removeItem(STORAGE_KEY);
      setStatus("anonymous");
      return;
    }

    authApi
      .me(cleanToken)
      .then((data) => {
        setToken(cleanToken);
        setUser(data.user);
        localStorage.setItem(STORAGE_KEY, cleanToken);
        setStatus("authenticated");
      })
      .catch(() => {
        localStorage.removeItem(STORAGE_KEY);
        setToken(null);
        setUser(null);
        setStatus("anonymous");
      });
  }, []);

  const handleAuthResponse = (data) => {
    const cleanToken = (data.token || "").trim();

    if (!cleanToken) {
      throw new Error(
        "Login succeeded but no authentication token was returned."
      );
    }

    localStorage.setItem(STORAGE_KEY, cleanToken);
    setToken(cleanToken);
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
    <AuthContext.Provider
      value={{
        user,
        token,
        status,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);

  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }

  return ctx;
}