// Talks to the Python backend in /solgulf-backend (see that folder's README
// to run it). For local development this defaults to localhost:8000. For a
// deployed build, set VITE_API_BASE in your hosting platform's environment
// variables (e.g. Vercel) to your deployed backend's real URL — nothing
// else in the app needs to change.

export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
  } catch (err) {
    throw new Error(
      "Can't reach the backend. Is it running? (python app.py in /solgulf-backend)"
    );
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Something went wrong. Please try again.");
  }
  return data;
}
