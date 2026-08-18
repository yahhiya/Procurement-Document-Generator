import { request } from "./client";

export function register(email, password) {
  return request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function login(email, password) {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function me(token) {
  return request("/api/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function setupStatus() {
  return request("/api/auth/setup-status");
}
