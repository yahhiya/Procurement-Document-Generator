import { API_BASE, request } from "./client";

export function extractDocument(token, { templateId, filename, fileBase64 }) {
  return request("/api/documents/extract", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      template_id: templateId,
      filename,
      file_base64: fileBase64,
    }),
  });
}

// Generation returns the actual .docx file as the response body, not JSON —
// so this doesn't go through the shared JSON-only request() helper.
export async function generateDocument(token, { templateId, values }) {
  let response;
  try {
    response = await fetch(`${API_BASE}/api/documents/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ template_id: templateId, values }),
    });
  } catch (err) {
    throw new Error(
      "Can't reach the backend. Is it running? (python app.py in /solgulf-backend)"
    );
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || "Something went wrong. Please try again.");
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="([^"]+)"/);
  const filename = match ? match[1] : "document.docx";
  return { blob, filename };
}
