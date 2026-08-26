"""
Fills in a .docx template by finding literal placeholder tokens (like
"{{customer_name}}") and replacing them with confirmed values.
"""

import io
import re
import zipfile

PARAGRAPH_RE = re.compile(r"<w:p(?:\s[^>]*)?>.*?</w:p>", re.DOTALL)
PPR_RE = re.compile(r"<w:pPr>.*?</w:pPr>", re.DOTALL)
RPR_RE = re.compile(r"<w:rPr>.*?</w:rPr>", re.DOTALL)

PARA_TOKEN_RE = re.compile(
    r"<w:t(?:\s[^>]*)?>(.*?)</w:t>"
    r"|<w:t(?:\s[^>]*)?/>"
    r"|<w:br(?:\s[^>]*)?/>"
    r"|<w:tab(?:\s[^>]*)?/>",
    re.DOTALL,
)

TEXT_PART_RE = re.compile(r"^word/(document|header\d*|footer\d*)\.xml$")


class GenerationError(Exception):
    """Raised when generation can't proceed safely."""


def _xml_unescape(text: str) -> str:
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def _xml_escape(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _paragraph_text(paragraph_xml: str) -> str:
    parts = []
    for m in PARA_TOKEN_RE.finditer(paragraph_xml):
        token = m.group(0)
        if token.startswith("<w:br"):
            parts.append("\n")
        elif token.startswith("<w:tab"):
            parts.append("\t")
        else:
            parts.append(_xml_unescape(m.group(1) or ""))
    return "".join(parts)


def _text_to_runs_xml(text: str, rpr: str) -> str:
    segments = re.split(r"(\n|\t)", text)
    runs = []
    for seg in segments:
        if seg == "\n":
            runs.append(f"<w:r>{rpr}<w:br/></w:r>")
        elif seg == "\t":
            runs.append(f"<w:r>{rpr}<w:tab/></w:r>")
        elif seg == "":
            continue
        else:
            runs.append(f'<w:r>{rpr}<w:t xml:space="preserve">{_xml_escape(seg)}</w:t></w:r>')
    return "".join(runs) or f'<w:r>{rpr}<w:t xml:space="preserve"></w:t></w:r>'


def _rebuild_paragraph(paragraph_xml: str, new_text: str) -> str:
    ppr_match = PPR_RE.search(paragraph_xml)
    ppr = ppr_match.group(0) if ppr_match else ""

    search_start = ppr_match.end() if ppr_match else 0
    rpr_match = RPR_RE.search(paragraph_xml, search_start)
    rpr = rpr_match.group(0) if rpr_match else ""

    runs_xml = _text_to_runs_xml(new_text, rpr)
    return f"<w:p>{ppr}{runs_xml}</w:p>"


def _replace_in_xml(xml_text: str, placeholder_map: dict, occurrence_counts: dict) -> str:
    # Normalize keys so that whether they have curly braces or UI field names, they match template tokens
    normalized_map = {}
    for k, v in placeholder_map.items():
        if not k.startswith("{{"):
            formatted_key = "{{" + k.strip().lower().replace(" ", "_") + "}}"
        else:
            formatted_key = k
        normalized_map[formatted_key] = v
        occurrence_counts[formatted_key] = 0

    sorted_placeholders = sorted(normalized_map.keys(), key=len, reverse=True)

    def repl(match):
        paragraph_xml = match.group(0)
        text = _paragraph_text(paragraph_xml)
        if not text:
            return paragraph_xml

        new_text = text
        found_any = False
        for placeholder in sorted_placeholders:
            value = normalized_map[placeholder]
            count = new_text.count(placeholder)
            if count:
                occurrence_counts[placeholder] = occurrence_counts.get(placeholder, 0) + count
                new_text = new_text.replace(placeholder, value)
                found_any = True

        if not found_any:
            return paragraph_xml
        return _rebuild_paragraph(paragraph_xml, new_text)

    return PARAGRAPH_RE.sub(repl, xml_text)


def generate_docx(template_file_path: str, placeholder_map: dict) -> tuple[bytes, dict]:
    with open(template_file_path, "rb") as f:
        src_bytes = f.read()

    occurrence_counts = {}
    out_buffer = io.BytesIO()

    with zipfile.ZipFile(io.BytesIO(src_bytes), "r") as src_zip, zipfile.ZipFile(
        out_buffer, "w", zipfile.ZIP_DEFLATED
    ) as out_zip:
        for item in src_zip.infolist():
            data = src_zip.read(item.filename)
            if TEXT_PART_RE.match(item.filename):
                xml_text = data.decode("utf-8")
                xml_text = _replace_in_xml(xml_text, placeholder_map, occurrence_counts)
                data = xml_text.encode("utf-8")
            out_zip.writestr(item, data)

    return out_buffer.getvalue(), occurrence_counts