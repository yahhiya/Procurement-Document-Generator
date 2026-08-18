import { request } from "./client";

// Active templates only — for the document workflow's template picker.
export function listTemplates(token) {
  return request("/api/templates", {
    headers: { Authorization: `Bearer ${token}` },
  });
}
