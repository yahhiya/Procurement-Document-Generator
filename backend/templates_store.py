"""
Template file storage.

Uploaded .docx template files are saved on disk under template_files/, and
the templates table (see db.py) stores metadata plus a reference to that
file. This mirrors how the users table + auth.py are split — storage details
live here, HTTP handling lives in app.py.
"""

import re
import time
import zipfile
from pathlib import Path

import db

TEMPLATE_DIR = Path(__file__).parent / "template_files"
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(original_filename: str) -> str:
    name = SAFE_NAME_RE.sub("_", original_filename.strip()) or "template.docx"
    if not name.lower().endswith(".docx"):
        name += ".docx"
    return name


def save_template_file(original_filename: str, file_bytes: bytes) -> str:
    """Writes the uploaded file to disk with a collision-proof name and
    returns the path (relative to this folder) to store in the database."""
    TEMPLATE_DIR.mkdir(exist_ok=True)
    safe_name = _safe_filename(original_filename)
    stored_name = f"{int(time.time() * 1000)}_{safe_name}"
    path = TEMPLATE_DIR / stored_name
    path.write_bytes(file_bytes)
    return str(path.relative_to(Path(__file__).parent))


def _minimal_docx_bytes(title: str, body_text: str) -> bytes:
    """Builds a minimal-but-valid .docx file from scratch using only the
    standard library — no python-docx dependency required. Used once, to
    seed the first MSA template with a real, openable placeholder file."""
    import io

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )

    def esc(t):
        return (
            t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:r><w:rPr><w:b/><w:sz w:val="32"/></w:rPr><w:t>{esc(title)}</w:t></w:r></w:p>
<w:p><w:r><w:t>{esc(body_text)}</w:t></w:r></w:p>
</w:body>
</w:document>"""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def delete_template_file(relative_file_path: str):
    """Best-effort removal of a template's file from disk. Never raises —
    if the file's already gone for some reason, that's fine, the goal is
    just for it not to linger."""
    path = Path(__file__).parent / relative_file_path
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def seed_initial_template_if_empty():
    """Called once at startup. If the templates table is empty, creates the
    first real template — Master Services Agreement — with an actual
    openable (if minimal) .docx file, so the system isn't demoing with a
    template that doesn't really exist anywhere."""
    if db.count_templates() > 0:
        return

    placeholder_bytes = _minimal_docx_bytes(
        "Master Services Agreement — Template",
        "Placeholder template file. Replace this by uploading the real "
        "approved MSA template from Manage Templates.",
    )
    file_path = save_template_file("MSA_template.docx", placeholder_bytes)
    db.create_template(
        name="Master Services Agreement (MSA)",
        document_type="MSA",
        description="Standard master services agreement for offshore and marine service contracts.",
        file_path=file_path,
        original_filename="MSA_template.docx",
        status="active",
    )
