"""
Procurement Document Generator — accounts + template management backend.

Accounts endpoints:
  POST /api/auth/register   Create an account. Only works when the system has
                             zero accounts — that one call bootstraps the
                             first admin. After that, registration is closed;
                             an admin must create further accounts via
                             /api/admin/users.
  POST /api/auth/login      Exchange email + password for a session token.
  GET  /api/auth/me         Look up the currently logged-in user from their
                             token (sent as "Authorization: Bearer <token>").
  GET  /api/auth/setup-status  Public. Tells the frontend whether the system
                             still needs its first admin account created.
  GET  /api/admin/users     List all accounts. Admin only.
  POST /api/admin/users     Create a new account with a chosen role. Admin
                             only — this is how an admin adds teammates.

Template endpoints:
  GET   /api/templates              Active templates only. Any logged-in
                                     user — this feeds the document workflow's
                                     template picker.
  GET   /api/admin/templates        All templates (active + inactive) with
                                     full detail. Admin only.
  POST  /api/admin/templates        Upload a new .docx template. Admin only.
                                     Body: {name, document_type, description,
                                     filename, file_base64}.
  PATCH /api/admin/templates/<id>   Activate or deactivate a template. Admin
                                     only. Body: {status: "active"|"inactive"}.
  POST  /api/admin/templates/<id>/discover-fields
                                     Ask Claude to read the template's file
                                     and propose its variable fields. Admin
                                     only. Requires ANTHROPIC_API_KEY.
  GET   /api/admin/templates/<id>/fields
                                     Get a template's current field list and
                                     status (none/discovered/confirmed).
  PATCH /api/admin/templates/<id>/fields
                                     Save an edited field list and mark it
                                     confirmed. Body: {fields: [...]}.

Document workflow:
  POST /api/documents/extract       Any logged-in user. Body: {template_id,
                                     filename, file_base64}. Reads the
                                     uploaded requirements document, asks AI
                                     to find a value for each of the
                                     template's confirmed fields, and returns
                                     them — "not found" fields come back as
                                     null, never guessed.
  POST /api/documents/generate      Any logged-in user. Body: {template_id,
                                     values: {key: value}}. Fills the
                                     template's placeholder tokens with the
                                     confirmed values and returns the
                                     completed .docx file directly as the
                                     response body (not JSON).

Run it with:  python app.py
It starts on http://localhost:8000
"""

import base64
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import auth
import db
import demo_seed
import docx_generator
import docx_reader
import llm
import templates_store

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
VALID_ROLES = {"admin", "user"}
VALID_TEMPLATE_STATUSES = {"active", "inactive"}
TEMPLATE_ID_RE = re.compile(r"^/api/admin/templates/(\d+)$")
TEMPLATE_DISCOVER_RE = re.compile(r"^/api/admin/templates/(\d+)/discover-fields$")
TEMPLATE_FIELDS_RE = re.compile(r"^/api/admin/templates/(\d+)/fields$")
USER_ID_RE = re.compile(r"^/api/admin/users/(\d+)$")


class Handler(BaseHTTPRequestHandler):
    # ---- low-level plumbing -------------------------------------------------

    def _set_cors(self):
        self.send_header("Access-Control-Allow-Origin", FRONTEND_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._set_cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, status, file_bytes, filename, content_type):
        self.send_response(status)
        self._set_cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(file_bytes)))
        # So the frontend's fetch() can read the filename we chose, since
        # by default JS can only see a small allow-list of response headers.
        self.send_header("Access-Control-Expose-Headers", "Content-Disposition")
        self.end_headers()
        self.wfile.write(file_bytes)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _current_user(self):
        """Returns the decoded token payload, or None if missing/invalid."""
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return None
        token = header[len("Bearer "):]
        try:
            return auth.decode_token(token)
        except Exception:
            return None

    def _require_admin(self):
        """Returns the token payload if the caller is an admin, else None
        (and has already sent the appropriate error response)."""
        payload = self._current_user()
        if not payload:
            self._send_json(401, {"error": "Not authenticated"})
            return None
        if payload.get("role") != "admin":
            self._send_json(403, {"error": "Admin access required"})
            return None
        return payload

    def _require_auth(self):
        """Returns the token payload for any logged-in user, else None (and
        has already sent the appropriate error response)."""
        payload = self._current_user()
        if not payload:
            self._send_json(401, {"error": "Not authenticated"})
            return None
        return payload

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/auth/register":
            return self.handle_register()
        if self.path == "/api/auth/login":
            return self.handle_login()
        if self.path == "/api/admin/users":
            return self.handle_admin_create_user()
        if self.path == "/api/admin/templates":
            return self.handle_admin_create_template()
        if self.path == "/api/documents/extract":
            return self.handle_extract_document()
        if self.path == "/api/documents/generate":
            return self.handle_generate_document()
        match = TEMPLATE_DISCOVER_RE.match(self.path)
        if match:
            return self.handle_admin_discover_fields(int(match.group(1)))
        self._send_json(404, {"error": "Not found"})

    def do_GET(self):
        if self.path == "/api/auth/me":
            return self.handle_me()
        if self.path == "/api/auth/setup-status":
            return self.handle_setup_status()
        if self.path == "/api/admin/users":
            return self.handle_admin_list_users()
        if self.path == "/api/templates":
            return self.handle_list_templates()
        if self.path == "/api/admin/templates":
            return self.handle_admin_list_templates()
        if self.path == "/api/health":
            return self._send_json(200, {"status": "ok"})
        if self.path == "/api/demo/sample":
            return self.handle_demo_sample()
        match = TEMPLATE_FIELDS_RE.match(self.path)
        if match:
            return self.handle_get_template_fields(int(match.group(1)))
        self._send_json(404, {"error": "Not found"})

    def do_PATCH(self):
        match = TEMPLATE_FIELDS_RE.match(self.path)
        if match:
            return self.handle_admin_save_fields(int(match.group(1)))
        match = TEMPLATE_ID_RE.match(self.path)
        if match:
            return self.handle_admin_update_template(int(match.group(1)))
        self._send_json(404, {"error": "Not found"})

    def do_DELETE(self):
        match = TEMPLATE_ID_RE.match(self.path)
        if match:
            return self.handle_admin_delete_template(int(match.group(1)))
        match = USER_ID_RE.match(self.path)
        if match:
            return self.handle_admin_delete_user(int(match.group(1)))
        self._send_json(404, {"error": "Not found"})

    # ---- route handlers -------------------------------------------------

    def handle_register(self):
        # Public self sign-up is intentionally closed once the workspace has
        # an admin. This endpoint only ever creates ONE account: the very
        # first admin, on a completely empty database. Every account after
        # that must be created by an admin via /api/admin/users.
        if db.count_users() > 0:
            return self._send_json(
                403,
                {"error": "Public registration is disabled. Ask an admin to create your account."},
            )

        data = self._read_json()
        if data is None:
            return self._send_json(400, {"error": "Invalid JSON body"})

        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not EMAIL_RE.match(email):
            return self._send_json(400, {"error": "Enter a valid email address"})
        if len(password) < 8:
            return self._send_json(400, {"error": "Password must be at least 8 characters"})

        salt, pwd_hash = auth.hash_password(password)
        user_id = db.create_user(email, salt, pwd_hash, "admin")
        token = auth.create_token(user_id, email, "admin")
        return self._send_json(
            201, {"token": token, "user": {"id": user_id, "email": email, "role": "admin"}}
        )

    def handle_login(self):
        data = self._read_json()
        if data is None:
            return self._send_json(400, {"error": "Invalid JSON body"})

        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        row = db.get_user_by_email(email)
        if not row or not auth.verify_password(password, row["salt"], row["password_hash"]):
            return self._send_json(401, {"error": "Incorrect email or password"})

        token = auth.create_token(row["id"], row["email"], row["role"])
        return self._send_json(
            200,
            {"token": token, "user": {"id": row["id"], "email": row["email"], "role": row["role"]}},
        )

    def handle_me(self):
        payload = self._current_user()
        if not payload:
            return self._send_json(401, {"error": "Not authenticated"})
        row = db.get_user_by_id(payload["sub"])
        if not row:
            return self._send_json(401, {"error": "Not authenticated"})
        return self._send_json(
            200, {"user": {"id": row["id"], "email": row["email"], "role": row["role"]}}
        )

    def handle_setup_status(self):
        return self._send_json(200, {"needs_setup": db.count_users() == 0})

    def handle_admin_list_users(self):
        if not self._require_admin():
            return
        rows = db.list_users()
        users = [
            {"id": r["id"], "email": r["email"], "role": r["role"], "created_at": r["created_at"]}
            for r in rows
        ]
        return self._send_json(200, {"users": users})

    def handle_admin_create_user(self):
        if not self._require_admin():
            return

        data = self._read_json()
        if data is None:
            return self._send_json(400, {"error": "Invalid JSON body"})

        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        role = data.get("role") or "user"

        if not EMAIL_RE.match(email):
            return self._send_json(400, {"error": "Enter a valid email address"})
        if len(password) < 8:
            return self._send_json(400, {"error": "Password must be at least 8 characters"})
        if role not in VALID_ROLES:
            return self._send_json(400, {"error": "Role must be 'admin' or 'user'"})
        if db.get_user_by_email(email):
            return self._send_json(409, {"error": "An account with this email already exists"})

        salt, pwd_hash = auth.hash_password(password)
        user_id = db.create_user(email, salt, pwd_hash, role)
        return self._send_json(
            201, {"user": {"id": user_id, "email": email, "role": role}}
        )

    def handle_admin_delete_user(self, user_id):
        requester = self._require_admin()
        if not requester:
            return

        target = db.get_user_by_id(user_id)
        if not target:
            return self._send_json(404, {"error": "Account not found"})

        primary_admin_id = db.get_primary_admin_id()

        # The primary (first-ever) admin bootstrapped this workspace and can
        # never be removed — otherwise a bad actor (or a mistake) could
        # permanently lock everyone out with no way back in.
        if target["id"] == primary_admin_id:
            return self._send_json(
                400, {"error": "The primary admin account can't be removed."}
            )

        if target["role"] == "admin":
            # Never allow the workspace to end up with zero admins.
            if db.count_admins() <= 1:
                return self._send_json(
                    400, {"error": "Can't remove the last remaining admin."}
                )
            # Only the primary admin may remove another admin — a regular
            # admin can't remove peers or escalate by picking each other off.
            if requester["sub"] != primary_admin_id:
                return self._send_json(
                    403, {"error": "Only the primary admin can remove another admin."}
                )

        db.delete_user(user_id)
        return self._send_json(200, {"deleted": True})

    def handle_extract_document(self):
        if not self._require_auth():
            return

        data = self._read_json()
        if data is None:
            return self._send_json(400, {"error": "Invalid JSON body"})

        template_id = data.get("template_id")
        filename = (data.get("filename") or "").strip()
        file_base64 = data.get("file_base64") or ""

        if not isinstance(template_id, int):
            return self._send_json(400, {"error": "A template must be selected"})
        if not filename:
            return self._send_json(400, {"error": "No file was uploaded"})
        if not file_base64:
            return self._send_json(400, {"error": "No file was uploaded"})

        template = db.get_template_by_id(template_id)
        if not template:
            return self._send_json(404, {"error": "Template not found"})

        try:
            fields = json.loads(template["fields_json"])
        except json.JSONDecodeError:
            fields = []
        if not fields:
            return self._send_json(
                400,
                {
                    "error": "This template has no fields configured yet. "
                    "Ask an admin to set them up under Manage Templates."
                },
            )

        try:
            file_bytes = base64.b64decode(file_base64)
        except Exception:
            return self._send_json(400, {"error": "Uploaded file could not be read"})
        if len(file_bytes) == 0:
            return self._send_json(400, {"error": "Uploaded file is empty"})

        lower_name = filename.lower()
        try:
            if lower_name.endswith(".docx"):
                document_text = docx_reader.extract_text_from_bytes(file_bytes)
            elif lower_name.endswith(".txt"):
                document_text = docx_reader.extract_text_from_plain_bytes(file_bytes)
            else:
                return self._send_json(
                    400, {"error": "Only DOCX and TXT files are supported"}
                )
        except ValueError as e:
            return self._send_json(400, {"error": str(e)})

        try:
            values = llm.extract_field_values(fields, document_text)
        except llm.FieldDiscoveryError as e:
            return self._send_json(502, {"error": str(e)})

        result_fields = [
            {
                "key": f["key"],
                "label": f["label"],
                "type": f["type"],
                "required": f.get("required", False),
                "value": values.get(f["key"]),
                "needs_verification": values.get(f["key"]) is None,
            }
            for f in fields
        ]

        return self._send_json(
            200,
            {
                "template": {"id": template["id"], "name": template["name"]},
                "fields": result_fields,
            },
        )

    def handle_generate_document(self):
        if not self._require_auth():
            return

        data = self._read_json()
        if data is None:
            return self._send_json(400, {"error": "Invalid JSON body"})

        template_id = data.get("template_id")
        values = data.get("values")

        if not isinstance(template_id, int):
            return self._send_json(400, {"error": "A template must be selected"})
        if not isinstance(values, dict):
            return self._send_json(400, {"error": "Field values are required"})

        template = db.get_template_by_id(template_id)
        if not template:
            return self._send_json(404, {"error": "Template not found"})

        try:
            fields = json.loads(template["fields_json"])
        except json.JSONDecodeError:
            fields = []
        if not fields:
            return self._send_json(
                400,
                {
                    "error": "This template has no fields configured yet. "
                    "Ask an admin to set them up under Manage Templates."
                },
            )

        # Every required field needs a real value before we generate anything.
        missing_labels = []
        value_by_key = {}
        for f in fields:
            raw = values.get(f["key"])
            value_str = str(raw).strip() if raw is not None else ""
            value_by_key[f["key"]] = value_str
            if f.get("required") and not value_str:
                missing_labels.append(f["label"])
        if missing_labels:
            return self._send_json(
                400,
                {
                    "error": "Missing a value for: " + ", ".join(missing_labels)
                    + ". Resolve these on the review screen before generating."
                },
            )

        # Blank optional fields still get "replaced" — with an empty string —
        # so no bracket placeholder is ever left sitting in the final file.
        #
        # Each field gets more than one candidate token to look for, not
        # just whatever's stored in fields_json. Field discovery (llm.py)
        # can end up with a placeholder that doesn't actually match the
        # document — e.g. a curly-brace template where discovery reported
        # a bracket-style guess instead of copying the real token — and
        # that shouldn't mean every generation fails until an admin
        # manually fixes 100+ field rows. Trying the field's own key in
        # both this app's default "{{key}}" convention and a "[KEY]"
        # convention covers the two most common template authoring styles
        # even when the stored placeholder is wrong.
        placeholder_map = {}
        for f in fields:
            value = value_by_key[f["key"]]
            for candidate in {
                llm.derive_placeholder(f),
                "{{" + f["key"] + "}}",
                f"[{f['key'].upper()}]",
            }:
                placeholder_map[candidate] = value

        def _field_resolved(f, occurrence_counts):
            return any(
                occurrence_counts.get(candidate, 0) > 0
                for candidate in (
                    llm.derive_placeholder(f),
                    "{{" + f["key"] + "}}",
                    f"[{f['key'].upper()}]",
                )
            )

        file_path = os.path.join(os.path.dirname(__file__), template["file_path"])
        try:
            output_bytes, occurrence_counts = docx_generator.generate_docx(file_path, placeholder_map)
        except FileNotFoundError:
            return self._send_json(
                500, {"error": "This template's file is missing on the server."}
            )
        except Exception as e:
            return self._send_json(500, {"error": f"Couldn't generate the document: {e}"})

        # If a field actually had a value to insert, but its placeholder was
        # never found anywhere in the template, that value has nowhere to
        # go — the field/template mapping is wrong. Fail loudly rather than
        # silently ship a document missing content the user confirmed.
        unresolved = [
            f["label"]
            for f in fields
            if value_by_key[f["key"]] and not _field_resolved(f, occurrence_counts)
        ]
        if unresolved:
            return self._send_json(
                400,
                {
                    "error": "Couldn't find where to insert: " + ", ".join(unresolved)
                    + ". Check these fields' placeholder tokens under Manage Templates \u2192 Fields."
                },
            )

        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", template["name"]).strip("_") or "document"
        filename = f"{safe_name}_Generated.docx"
        return self._send_file(
            200,
            output_bytes,
            filename,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def handle_demo_sample(self):
        """Any logged-in user. Powers the 'Try Interactive Demo' button:
        returns a built-in demo template's id plus pre-staged field values,
        so the frontend can skip the real /api/documents/extract call (and
        the LLM request behind it) entirely. Generation afterwards still
        goes through the real /api/documents/generate endpoint untouched."""
        if not self._require_auth():
            return

        template = demo_seed.get_or_create_demo_template()
        fields = demo_seed.get_demo_sample_fields(template)

        # Swap the literal {{key}} tokens for readable [Field Label] text —
        # a CV reviewer clicking to preview the template wants to see what
        # a blank contract looks like, not the app's internal token syntax.
        preview_text = demo_seed.get_template_preview_text(template)
        for f in fields:
            preview_text = preview_text.replace("{{" + f["key"] + "}}", f"[{f['label']}]")

        return self._send_json(
            200,
            {
                "template": {
                    "id": template["id"],
                    "name": template["name"],
                    "preview_text": preview_text,
                },
                "requirements_document": {
                    "name": demo_seed.SAMPLE_REQUIREMENTS_FILENAME,
                    "preview_text": demo_seed.SAMPLE_REQUIREMENTS_TEXT,
                },
                "fields": fields,
            },
        )

    # ---- template handlers -------------------------------------------------

    def handle_list_templates(self):
        """Any logged-in user. Powers the document workflow's template
        picker — active templates only, and only the fields that screen
        actually needs."""
        if not self._require_auth():
            return
        rows = db.list_templates(active_only=True)
        templates = [
            {
                "id": r["id"],
                "name": r["name"],
                "document_type": r["document_type"],
                "description": r["description"],
            }
            for r in rows
        ]
        return self._send_json(200, {"templates": templates})

    def handle_admin_list_templates(self):
        """Admin only. Full detail, active and inactive both, for the
        Manage Templates screen."""
        if not self._require_admin():
            return
        rows = db.list_templates(active_only=False)
        templates = [
            {
                "id": r["id"],
                "name": r["name"],
                "document_type": r["document_type"],
                "description": r["description"],
                "original_filename": r["original_filename"],
                "status": r["status"],
                "fields_status": r["fields_status"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]
        return self._send_json(200, {"templates": templates})

    def handle_admin_create_template(self):
        if not self._require_admin():
            return

        data = self._read_json()
        if data is None:
            return self._send_json(400, {"error": "Invalid JSON body"})

        name = (data.get("name") or "").strip()
        document_type = (data.get("document_type") or "").strip()
        description = (data.get("description") or "").strip()
        filename = (data.get("filename") or "").strip()
        file_base64 = data.get("file_base64") or ""

        if not name:
            return self._send_json(400, {"error": "Template name is required"})
        if not document_type:
            return self._send_json(400, {"error": "Document type is required"})
        if not filename.lower().endswith(".docx"):
            return self._send_json(400, {"error": "Only .docx files are supported"})
        if not file_base64:
            return self._send_json(400, {"error": "No file was uploaded"})

        try:
            file_bytes = base64.b64decode(file_base64)
        except Exception:
            return self._send_json(400, {"error": "Uploaded file could not be read"})

        if len(file_bytes) == 0:
            return self._send_json(400, {"error": "Uploaded file is empty"})

        file_path = templates_store.save_template_file(filename, file_bytes)
        template_id = db.create_template(
            name=name,
            document_type=document_type,
            description=description,
            file_path=file_path,
            original_filename=filename,
            status="active",
        )
        return self._send_json(
            201,
            {
                "template": {
                    "id": template_id,
                    "name": name,
                    "document_type": document_type,
                    "description": description,
                    "status": "active",
                }
            },
        )

    def handle_admin_update_template(self, template_id):
        if not self._require_admin():
            return

        row = db.get_template_by_id(template_id)
        if not row:
            return self._send_json(404, {"error": "Template not found"})

        data = self._read_json()
        if data is None:
            return self._send_json(400, {"error": "Invalid JSON body"})

        status = data.get("status")
        if status not in VALID_TEMPLATE_STATUSES:
            return self._send_json(
                400, {"error": "Status must be 'active' or 'inactive'"}
            )

        db.update_template_status(template_id, status)
        updated = db.get_template_by_id(template_id)
        return self._send_json(
            200,
            {
                "template": {
                    "id": updated["id"],
                    "name": updated["name"],
                    "document_type": updated["document_type"],
                    "description": updated["description"],
                    "status": updated["status"],
                    "updated_at": updated["updated_at"],
                }
            },
        )

    def handle_admin_delete_template(self, template_id):
        if not self._require_admin():
            return

        row = db.get_template_by_id(template_id)
        if not row:
            return self._send_json(404, {"error": "Template not found"})

        db.delete_template(template_id)
        templates_store.delete_template_file(row["file_path"])
        return self._send_json(200, {"deleted": True})

    def handle_admin_discover_fields(self, template_id):
        if not self._require_admin():
            return

        row = db.get_template_by_id(template_id)
        if not row:
            return self._send_json(404, {"error": "Template not found"})

        file_path = os.path.join(os.path.dirname(__file__), row["file_path"])
        try:
            document_text = docx_reader.extract_text(file_path)
        except (ValueError, FileNotFoundError) as e:
            return self._send_json(500, {"error": f"Couldn't read the template file: {e}"})

        try:
            fields = llm.discover_fields(row["name"], row["document_type"], document_text)
        except llm.FieldDiscoveryError as e:
            return self._send_json(502, {"error": str(e)})

        db.update_template_fields(template_id, json.dumps(fields), "discovered")
        return self._send_json(200, {"fields": fields, "fields_status": "discovered"})

    def handle_get_template_fields(self, template_id):
        if not self._require_admin():
            return

        row = db.get_template_by_id(template_id)
        if not row:
            return self._send_json(404, {"error": "Template not found"})

        try:
            fields = json.loads(row["fields_json"])
        except json.JSONDecodeError:
            fields = []
        return self._send_json(200, {"fields": fields, "fields_status": row["fields_status"]})

    def handle_admin_save_fields(self, template_id):
        if not self._require_admin():
            return

        row = db.get_template_by_id(template_id)
        if not row:
            return self._send_json(404, {"error": "Template not found"})

        data = self._read_json()
        if data is None:
            return self._send_json(400, {"error": "Invalid JSON body"})

        fields = data.get("fields")
        if not isinstance(fields, list) or len(fields) == 0:
            return self._send_json(400, {"error": "At least one field is required"})

        cleaned = []
        seen_keys = set()
        for item in fields:
            if not isinstance(item, dict):
                return self._send_json(400, {"error": "Each field must be an object"})
            key = (item.get("key") or "").strip()
            label = (item.get("label") or "").strip()
            field_type = item.get("type")
            if not key or not label:
                return self._send_json(400, {"error": "Every field needs a key and a label"})
            if field_type not in llm.VALID_FIELD_TYPES:
                return self._send_json(400, {"error": f"Invalid field type: {field_type}"})
            if key in seen_keys:
                return self._send_json(400, {"error": f"Duplicate field key: {key}"})
            seen_keys.add(key)
            raw_placeholder = item.get("placeholder")
            placeholder = (
                raw_placeholder.strip()
                if isinstance(raw_placeholder, str) and raw_placeholder.strip()
                else None
            )
            cleaned.append(
                {
                    "key": key,
                    "label": label,
                    "type": field_type,
                    "required": bool(item.get("required", False)),
                    "placeholder": placeholder,
                }
            )

        db.update_template_fields(template_id, json.dumps(cleaned), "confirmed")
        return self._send_json(200, {"fields": cleaned, "fields_status": "confirmed"})

    def log_message(self, format, *args):  # quieter default logging
        print("%s - %s" % (self.address_string(), format % args))


def load_dotenv():
    """Reads KEY=VALUE lines from a .env file next to this script, if one
    exists, and sets them as environment variables. No dependency needed —
    just a few lines of stdlib. Existing environment variables always win,
    so this never overrides something you set another way."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def main():
    load_dotenv()
    db.init_db()
    port = int(os.environ.get("PORT", 8000))

    if not os.environ.get("SECRET_KEY"):
        print("=" * 70)
        print("WARNING: SECRET_KEY is not set — using the insecure default.")
        print("Anyone who knows this default value could forge login tokens.")
        print("This is fine for local testing, but set a real SECRET_KEY")
        print("environment variable before deploying this anywhere real.")
        print("=" * 70)

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Backend running on http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
