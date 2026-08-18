import { request } from "./client";

export function listUsers(token) {
  return request("/api/admin/users", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function createUser(token, { email, password, role }) {
  return request("/api/admin/users", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ email, password, role }),
  });
}

// ---- templates --------------------------------------------------------

// All templates (active + inactive) with full detail — Manage Templates screen.
export function listAllTemplates(token) {
  return request("/api/admin/templates", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function uploadTemplate(token, { name, documentType, description, filename, fileBase64 }) {
  return request("/api/admin/templates", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      name,
      document_type: documentType,
      description,
      filename,
      file_base64: fileBase64,
    }),
  });
}

export function setTemplateStatus(token, templateId, status) {
  return request(`/api/admin/templates/${templateId}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ status }),
  });
}

export function deleteTemplate(token, templateId) {
  return request(`/api/admin/templates/${templateId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function deleteUser(token, userId) {
  return request(`/api/admin/users/${userId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function discoverTemplateFields(token, templateId) {
  return request(`/api/admin/templates/${templateId}/discover-fields`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function getTemplateFields(token, templateId) {
  return request(`/api/admin/templates/${templateId}/fields`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function saveTemplateFields(token, templateId, fields) {
  return request(`/api/admin/templates/${templateId}/fields`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ fields }),
  });
}
