"""
A tiny SQLite database — one file on disk (app.db), no separate database
server to install or run. Fine for a small internal tool; can be swapped for
a bigger database later without changing how the rest of the app calls it.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "app.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            document_type TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            file_path TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            fields_json TEXT NOT NULL DEFAULT '[]',
            fields_status TEXT NOT NULL DEFAULT 'none',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()


def count_users() -> int:
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    conn.close()
    return n


def get_user_by_email(email: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row


def get_user_by_id(user_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def create_user(email: str, salt: str, password_hash: str, role: str) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO users (email, salt, password_hash, role) VALUES (?, ?, ?, ?)",
        (email, salt, password_hash, role),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def list_users():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, email, role, created_at FROM users ORDER BY created_at"
    ).fetchall()
    conn.close()
    return rows


# ---- templates ------------------------------------------------------------


def count_templates() -> int:
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) AS n FROM templates").fetchone()["n"]
    conn.close()
    return n


def create_template(name, document_type, description, file_path, original_filename, status="active") -> int:
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO templates (name, document_type, description, file_path, original_filename, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, document_type, description, file_path, original_filename, status),
    )
    conn.commit()
    template_id = cur.lastrowid
    conn.close()
    return template_id


def list_templates(active_only: bool = False):
    conn = get_connection()
    if active_only:
        rows = conn.execute(
            "SELECT * FROM templates WHERE status = 'active' ORDER BY name"
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM templates ORDER BY created_at").fetchall()
    conn.close()
    return rows


def get_template_by_id(template_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,)).fetchone()
    conn.close()
    return row


def update_template_status(template_id: int, status: str) -> bool:
    conn = get_connection()
    cur = conn.execute(
        "UPDATE templates SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, template_id),
    )
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def update_template_fields(template_id: int, fields_json: str, fields_status: str) -> bool:
    conn = get_connection()
    cur = conn.execute(
        "UPDATE templates SET fields_json = ?, fields_status = ?, updated_at = datetime('now') WHERE id = ?",
        (fields_json, fields_status, template_id),
    )
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def delete_template(template_id: int) -> bool:
    conn = get_connection()
    cur = conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def count_admins() -> int:
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) AS n FROM users WHERE role = 'admin'").fetchone()["n"]
    conn.close()
    return n


def get_primary_admin_id():
    """The earliest-created admin account — the one that bootstrapped this
    workspace. Returns None if somehow there are no admins at all."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM users WHERE role = 'admin' ORDER BY id ASC LIMIT 1"
    ).fetchone()
    conn.close()
    return row["id"] if row else None


def delete_user(user_id: int) -> bool:
    conn = get_connection()
    cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted
