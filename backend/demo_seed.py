"""
Demo mode assets.

Everything the "Try Interactive Demo" button needs, self-contained:

  * a real, openable .docx contract template (~3-4 pages, plain-language
    "Standard Service Agreement") with bracket placeholder tokens like
    {{company_name}}, built the same way templates_store._minimal_docx_bytes
    builds the MSA seed template — no python-docx dependency required.
  * the confirmed field list for that template (18 fields), in the exact
    shape db.update_template_fields()/llm.py expect.
  * a pre-staged sample value for every field, so the demo's "extraction"
    step never calls out to an LLM. It's pure lookup, which is what keeps
    the demo free, instant, and off the real API quota.

The template row this creates is saved with status="inactive" so it never
shows up in the normal template picker (UploadStep's dropdown only lists
active templates) — real users generating real documents never see it.
It's still a completely ordinary row, found by ID, so the existing
POST /api/documents/generate handler runs against it unmodified and
produces a real .docx via docx_generator.py.
"""

import io
import zipfile

import db
import templates_store

DEMO_TEMPLATE_NAME = "Demo Sample Contract"

# ---------------------------------------------------------------------------
# Field definitions. `key` drives the review-screen label lookup and the
# sample-value lookup below; `placeholder` is the literal token
# docx_generator.py searches for and replaces in the .docx XML.
# ---------------------------------------------------------------------------
DEMO_FIELDS = [
    {"key": "company_name", "label": "Vendor Company Name", "type": "text", "required": True, "placeholder": "{{company_name}}"},
    {"key": "company_address", "label": "Vendor Address", "type": "text", "required": True, "placeholder": "{{company_address}}"},
    {"key": "client_name", "label": "Client Name", "type": "text", "required": True, "placeholder": "{{client_name}}"},
    {"key": "client_address", "label": "Client Address", "type": "text", "required": True, "placeholder": "{{client_address}}"},
    {"key": "project_name", "label": "Project Name", "type": "text", "required": True, "placeholder": "{{project_name}}"},
    {"key": "project_description", "label": "Project Description", "type": "paragraph", "required": True, "placeholder": "{{project_description}}"},
    {"key": "deliverables", "label": "Key Deliverables", "type": "paragraph", "required": True, "placeholder": "{{deliverables}}"},
    {"key": "contract_value", "label": "Total Contract Value", "type": "currency", "required": True, "placeholder": "{{contract_value}}"},
    {"key": "payment_schedule", "label": "Payment Schedule", "type": "paragraph", "required": True, "placeholder": "{{payment_schedule}}"},
    {"key": "payment_terms_days", "label": "Payment Terms (Net Days)", "type": "number", "required": True, "placeholder": "{{payment_terms_days}}"},
    {"key": "effective_date", "label": "Effective Date", "type": "date", "required": True, "placeholder": "{{effective_date}}"},
    {"key": "start_date", "label": "Start Date", "type": "date", "required": True, "placeholder": "{{start_date}}"},
    {"key": "end_date", "label": "End Date", "type": "date", "required": True, "placeholder": "{{end_date}}"},
    {"key": "governing_law", "label": "Governing Law", "type": "text", "required": True, "placeholder": "{{governing_law}}"},
    {"key": "termination_notice_days", "label": "Termination Notice (Days)", "type": "number", "required": True, "placeholder": "{{termination_notice_days}}"},
    {"key": "vendor_signatory_name", "label": "Vendor Signatory Name", "type": "text", "required": True, "placeholder": "{{vendor_signatory_name}}"},
    {"key": "vendor_signatory_title", "label": "Vendor Signatory Title", "type": "text", "required": True, "placeholder": "{{vendor_signatory_title}}"},
    {"key": "client_signatory_name", "label": "Client Signatory Name", "type": "text", "required": True, "placeholder": "{{client_signatory_name}}"},
    {"key": "client_signatory_title", "label": "Client Signatory Title", "type": "text", "required": False, "placeholder": "{{client_signatory_title}}"},
]

# One realistic sample value per field key, above. This is what the demo
# "extraction" step returns instantly, in place of a real LLM call.
DEMO_SAMPLE_VALUES = {
    "company_name": "Northwind Marine Services LLC",
    "company_address": "4400 Harbor Point Blvd, Suite 210, Norfolk, VA 23510",
    "client_name": "Atlas Offshore Energy Corp",
    "client_address": "1200 Bayfront Drive, Houston, TX 77002",
    "project_name": "Subsea Cable Inspection & Maintenance — Phase 2",
    "project_description": "Provision of ROV-based inspection, cathodic protection surveys, and "
    "routine maintenance for the client's subsea export cable network across "
    "the designated offshore lease blocks, including quarterly reporting.",
    "deliverables": "Inspection reports, cathodic protection survey data, video "
    "documentation, and a final maintenance summary delivered at the close of "
    "each quarterly cycle.",
    "contract_value": "1,485,000.00",
    "payment_schedule": "30% due on contract execution, 40% due at Phase 2 midpoint "
    "inspection sign-off, 30% due on final deliverable acceptance.",
    "payment_terms_days": "30",
    "effective_date": "September 1, 2026",
    "start_date": "September 15, 2026",
    "end_date": "September 14, 2027",
    "governing_law": "State of Texas",
    "termination_notice_days": "45",
    "vendor_signatory_name": "Dana Whitfield",
    "vendor_signatory_title": "VP, Client Delivery",
    "client_signatory_name": "Marcus Ridley",
    "client_signatory_title": "Director of Procurement",
}


def _esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _heading(text: str) -> str:
    return (
        '<w:p><w:pPr><w:spacing w:before="240" w:after="120"/></w:pPr>'
        f'<w:r><w:rPr><w:b/><w:sz w:val="26"/></w:rPr><w:t xml:space="preserve">{_esc(text)}</w:t></w:r></w:p>'
    )


def _para(text: str) -> str:
    return (
        '<w:p><w:pPr><w:spacing w:after="160"/></w:pPr>'
        f'<w:r><w:t xml:space="preserve">{_esc(text)}</w:t></w:r></w:p>'
    )


def _page_break() -> str:
    return "<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>"


def _build_demo_docx_bytes() -> bytes:
    """A plain-language, multi-page Standard Service Agreement with bracket
    placeholder tokens, built with the standard library only (same approach
    templates_store._minimal_docx_bytes uses for the MSA seed file)."""

    body_parts = [
        '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
        '<w:r><w:rPr><w:b/><w:sz w:val="36"/></w:rPr>'
        '<w:t>STANDARD SERVICE AGREEMENT</w:t></w:r></w:p>',
        _para(
            "This Standard Service Agreement (\"Agreement\") is entered into as of "
            "{{effective_date}}, by and between {{company_name}}, located at "
            "{{company_address}} (\"Vendor\"), and {{client_name}}, located at "
            "{{client_address}} (\"Client\")."
        ),
        _heading("1. Project"),
        _para("Project name: {{project_name}}"),
        _para("Description: {{project_description}}"),
        _heading("2. Deliverables"),
        _para("{{deliverables}}"),
        _heading("3. Term"),
        _para(
            "This Agreement begins on {{start_date}} and continues through "
            "{{end_date}}, unless terminated earlier under Section 6."
        ),
        _page_break(),
        _heading("4. Compensation"),
        _para("Total contract value: {{contract_value}}"),
        _para("Payment schedule: {{payment_schedule}}"),
        _para("Invoices are payable within {{payment_terms_days}} days of receipt."),
        _heading("5. Governing Law"),
        _para("This Agreement is governed by the laws of {{governing_law}}."),
        _heading("6. Termination"),
        _para(
            "Either party may terminate this Agreement for convenience with "
            "{{termination_notice_days}} days' written notice to the other party."
        ),
        _heading("7. General"),
        _para(
            "This Agreement constitutes the entire understanding between the "
            "parties with respect to its subject matter and supersedes all "
            "prior discussions or agreements, whether written or oral."
        ),
        _page_break(),
        _heading("Signatures"),
        _para("For Vendor:"),
        _para("Name: {{vendor_signatory_name}}"),
        _para("Title: {{vendor_signatory_title}}"),
        _para(""),
        _para("For Client:"),
        _para("Name: {{client_signatory_name}}"),
        _para("Title: {{client_signatory_title}}"),
    ]

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
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>" + "".join(body_parts) + "</w:body></w:document>"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def get_or_create_demo_template():
    """Returns the demo template's DB row, creating it (file + row +
    confirmed fields) on first call. Idempotent — safe to call on every
    request that needs it."""
    conn = db.get_connection()
    row = conn.execute(
        "SELECT * FROM templates WHERE name = ? LIMIT 1", (DEMO_TEMPLATE_NAME,)
    ).fetchone()
    conn.close()
    if row:
        return row

    file_bytes = _build_demo_docx_bytes()
    file_path = templates_store.save_template_file("demo_sample_contract.docx", file_bytes)
    template_id = db.create_template(
        name=DEMO_TEMPLATE_NAME,
        document_type="Service Agreement",
        description="Built-in sample contract used by the Try Demo flow. Not shown "
        "in the normal template picker.",
        file_path=file_path,
        original_filename="demo_sample_contract.docx",
        status="inactive",  # excluded from GET /api/templates (active_only)
    )
    db.update_template_fields(template_id, __import__("json").dumps(DEMO_FIELDS), "confirmed")
    return db.get_template_by_id(template_id)


def get_demo_sample_fields(template_row):
    """Builds the same {key,label,type,required,value,needs_verification}
    shape handle_extract_document() returns, but filled from the pre-staged
    DEMO_SAMPLE_VALUES dict instead of an LLM call."""
    import json

    fields = json.loads(template_row["fields_json"])
    return [
        {
            "key": f["key"],
            "label": f["label"],
            "type": f["type"],
            "required": f.get("required", False),
            "value": DEMO_SAMPLE_VALUES.get(f["key"]),
            "needs_verification": False,
        }
        for f in fields
    ]
