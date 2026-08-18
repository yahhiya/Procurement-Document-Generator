# Deploying the frontend (Vercel)

1. Deploy the backend first (see solgulf-backend/README.md) — you need its
   real URL before this step.
2. Push this code to GitHub (already set up).
3. Go to [vercel.com](https://vercel.com), sign up/in with GitHub, click
   **Add New** → **Project**, and import this repo.
4. When it asks for the project settings:
   - **Root Directory**: set this to `frontend` (important — the repo has
     other folders too, Vercel needs to know this is the one to build)
   - Framework preset should auto-detect as **Vite**
5. Before clicking deploy, add an environment variable:
   - **Name**: `VITE_API_BASE`
   - **Value**: your backend's real URL from Render (e.g.
     `https://solgulf-backend.onrender.com`) — no trailing slash
6. Click **Deploy**. Vercel gives you a real URL like
   `https://your-project.vercel.app`.
7. Go back to Render, open your backend service's environment variables,
   and update `FRONTEND_ORIGIN` to this exact Vercel URL. Save — Render
   redeploys automatically to pick it up.

From now on, every `git push` redeploys both automatically — no manual
steps on either side.

## If something doesn't connect after deploying

Open your deployed site, open browser DevTools → Network tab, and try
logging in. If requests fail:
- Check `VITE_API_BASE` on Vercel matches your Render URL exactly (no
  trailing slash, correct `https://`).
- Check `FRONTEND_ORIGIN` on Render matches your Vercel URL exactly — a
  mismatch here causes CORS errors, visible in the browser console as
  something mentioning "Access-Control-Allow-Origin".
