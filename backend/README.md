#  Procurement Document Generator — Accounts Backend

A small Python backend that handles sign-up, login, and admin/user roles for
the procurement app. No framework to learn — just Python's built-in web
server plus one small library (PyJWT) for login tokens.

## What it does

- Stores accounts (email + securely hashed password + role) in a single
  file, `app.db` — created automatically the first time you run it.
- The **first account ever created becomes admin automatically.** Every
  account after that is a normal "user" — an admin has to create further
  admin accounts (see below).
- Gives out a signed token on login, which the frontend stores and sends
  back on every request to prove who's logged in.

## Setup (do this once)

1. Open a terminal **in this folder** (`backend`).
2. Create and activate a virtual environment (keeps this project's packages
   separate from everything else on your machine):

   ```
   python -m venv venv
   ```

   Windows:
   ```
   venv\Scripts\activate
   ```
   Mac/Linux:
   ```
   source venv/bin/activate
   ```

3. Install the one dependency:

   ```
   pip install -r requirements.txt
   ```

## Running it

```
python app.py
```

You should see:
```
Backend running on http://localhost:8000
```

Leave this terminal open and running — it needs to stay open the same way
the frontend's `npm run dev` does. You'll run the frontend (`npm run dev`)
in a **separate** terminal at the same time; they run side by side.

## Trying it out

1. With the backend running, start the frontend as usual (`npm run dev` in
   the `frontend` folder) and open it in your browser.
2. You'll land on a sign-in screen. Click "Don't have an account? Create
   one" and register with any email and an 8+ character password — this
   first account becomes the admin.
3. Sign out and register a second account with a different email — this one
   will be a normal "user" (you can see the "User" badge in the header vs.
   "Admin" for the first one).

## Where accounts are stored

Everything lives in `app.db`, a single file created in this folder. If you
ever want to wipe all accounts and start over, stop the server and delete
that file — it'll be recreated empty next time you run `python app.py`.

## API reference (for when we build more features)

| Method | Path                       | Auth required | What it does                                       |
|--------|----------------------------|----------------|-----------------------------------------------------|
| POST   | /api/auth/register         | No             | Create the first admin account (once)                |
| POST   | /api/auth/login            | No             | Log in, get a token                                  |
| GET    | /api/auth/me                | Yes            | Look up the logged-in user                           |
| GET    | /api/auth/setup-status      | No             | Whether the workspace still needs its first admin    |
| GET    | /api/admin/users            | Yes (admin)    | List all accounts                                    |
| POST   | /api/admin/users            | Yes (admin)    | Create an account with a chosen role                 |
| GET    | /api/templates               | Yes            | Active templates only — feeds the document picker    |
| GET    | /api/admin/templates          | Yes (admin)    | All templates (active + inactive), full detail       |
| POST   | /api/admin/templates          | Yes (admin)    | Upload a new .docx template                          |
| PATCH  | /api/admin/templates/&lt;id&gt; | Yes (admin)  | Activate or deactivate a template                    |
| POST   | /api/admin/templates/&lt;id&gt;/discover-fields | Yes (admin) | Ask AI to propose the template's fields |
| GET    | /api/admin/templates/&lt;id&gt;/fields | Yes (admin)    | Get a template's current field list         |
| PATCH  | /api/admin/templates/&lt;id&gt;/fields | Yes (admin)    | Save an edited, confirmed field list        |

## About templates

The very first time you run the backend, it automatically creates one real
template — **Master Services Agreement (MSA)** — with a genuinely valid
(if minimal placeholder) `.docx` file, so the system isn't demoing with
something that doesn't actually exist. Replace that placeholder with your
real approved MSA template from the **Manage Templates** screen once you
have it (deactivate the placeholder, upload the real one).

Uploaded template files are stored in `template_files/` in this folder —
created automatically on first upload.

## AI field discovery (needs a Gemini API key)

From **Manage Templates**, an admin can click "Discover fields" on any
template. This reads the template's text and asks Google's Gemini AI to
identify which pieces of information change from contract to contract
(vendor name, contract value, dates, etc.) — so you don't have to define
that list by hand for every template.

**One-time setup:**

1. Go to [Google AI Studio](https://aistudio.google.com/apikey) and create
   a free API key (no credit card needed for the free tier).
2. In this folder, create a file literally named `.env` (just that, no
   other name before the dot) containing one line:
   ```
   GEMINI_API_KEY=your-key-here
   ```
3. Restart the backend (`python app.py`) if it was already running, so it
   picks up the new `.env` file.

Don't commit `.env` to git or share it — it's your private key. This calls
the free tier, so be aware Google's free-tier terms allow prompts sent to
it to be used to improve their models — worth knowing before uploading
genuinely confidential templates. If that becomes a concern, Gemini's paid
tier (or Anthropic's API) don't train on your data — ask for help swapping
the network call in `llm.py` if you switch later; it's isolated to one
function specifically so that's a small change.

## Deploying this for real (not just your laptop)

This backend is set up to deploy to [Render](https://render.com) for free,
using the `render.yaml` file in this folder.

1. Push this code to GitHub (you've already got that set up).
2. Go to [dashboard.render.com](https://dashboard.render.com), sign up/in,
   click **New** → **Blueprint**, and connect your GitHub repo.
3. Render reads `render.yaml` automatically and sets up the service. It'll
   ask you to fill in two values it can't guess:
   - `GEMINI_API_KEY` — your real key
   - `FRONTEND_ORIGIN` — leave a placeholder for now (e.g.
     `https://placeholder.com`); come back and update it once your frontend
     is deployed and you know its real address (see the frontend README).
   `SECRET_KEY` is generated automatically for you — you don't need to set it.
4. Click deploy. Render gives you a public URL like
   `https://solgulf-backend.onrender.com` — that's your backend's real
   address. You'll need it when deploying the frontend.

**Important limitation on the free tier:** Render's free web service disk is
wiped on every redeploy — meaning `app.db` (all your accounts and
templates) resets every time you push a code update. This is fine while
testing, but worth knowing before real people rely on it. Fixing this
properly means either a small paid persistent disk or switching to a
hosted database — a bigger change, ask for help with it if/when this
becomes a real problem.

Every time you `git push` after this, Render automatically redeploys —
no manual steps.

