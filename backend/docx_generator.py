"""
Fills in a .docx template by finding literal placeholder tokens (like
"[VENDOR_NAME]") and replacing them with confirmed values.

Deliberately avoids parsing + fully re-serializing the whole XML tree with
ElementTree — that risks subtly rewriting namespace prefixes or formatting
across the ENTIRE document, even parts with nothing to do with our fields.
Instead this works directly on the raw XML text with regexes scoped to one
paragraph at a time: a paragraph with no placeholder in it is copied through
completely untouched (byte-for-byte), and only a paragraph that actually
contains a placeholder gets rebuilt — and even then, only that paragraph's
XML changes. Every other file in the .docx archive is copied verbatim.
"""

import io
import re
import zipfile

# One whole paragraph element, including any newlines inside it.
PARAGRAPH_RE = re.compile(r"<w:p(?:\s[^>]*)?>.*?</w:p>", re.DOTALL)
# A paragraph's own formatting block, if present — kept as-is when rebuilding.
PPR_RE = re.compile(r"<w:pPr>.*?</w:pPr>", re.DOTALL)
# A run's character formatting, if present.
RPR_RE = re.compile(r"<w:rPr>.*?</w:rPr>", re.DOTALL)
# Every inline content token within a chunk, IN DOCUMENT ORDER: text runs
# (a Word paragraph's visible text is often split across several of these,
# even mid-word, due to spellcheck/formatting boundaries Word inserts
# invisibly), plus line breaks and tabs — Word represents a manual line
# break *within* one paragraph (Shift+Enter) as a <w:br/> element sitting
# between runs, and a tab the same way with <w:tab/>. Both must be tracked
# in order, or lines that were visually separate collapse into one.
PARA_TOKEN_RE = re.compile(
    r"<w:t(?:\s[^>]*)?>(.*?)</w:t>"
    r"|<w:t(?:\s[^>]*)?/>"
    r"|<w:br(?:\s[^>]*)?/>"
    r"|<w:tab(?:\s[^>]*)?/>",
    re.DOTALL,
)

# Which parts of the archive can contain body text worth scanning.
TEXT_PART_RE = re.compile(r"^word/(document|header\d*|footer\d*)\.xml$")


class GenerationError(Exception):
    """Raised when generation can't proceed safely — e.g. a confirmed value
    has nowhere to go because its placeholder isn't actually in the
    template. Message is safe to show the user."""


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
    """Turns text (possibly containing \\n for line breaks and \\t for tabs,
    from _paragraph_text above) back into a sequence of <w:r> runs — each
    line-break/tab gets its own run per the OOXML spec, and each text
    segment between them gets a properly escaped <w:t>."""
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
    """Replaces a paragraph's many runs with fresh ones built from the
    substituted text — the only way to guarantee correctness when the
    original placeholder may have been split across runs. Keeps the
    paragraph's own formatting (pPr) and the first run's character
    formatting (rPr) so the result doesn't look visually out of place, and
    rebuilds any line breaks/tabs that were part of the original text."""
    ppr_match = PPR_RE.search(paragraph_xml)
    ppr = ppr_match.group(0) if ppr_match else ""

    # Search for a run's rPr *after* the pPr block, so we don't accidentally
    # grab the paragraph mark's own rPr (a different thing living inside pPr).
    search_start = ppr_match.end() if ppr_match else 0
    rpr_match = RPR_RE.search(paragraph_xml, search_start)
    rpr = rpr_match.group(0) if rpr_match else ""

    runs_xml = _text_to_runs_xml(new_text, rpr)
    return f"<w:p>{ppr}{runs_xml}</w:p>"


def _replace_in_xml(xml_text: str, placeholder_map: dict, occurrence_counts: dict) -> str:
    def repl(match):
        paragraph_xml = match.group(0)
        text = _paragraph_text(paragraph_xml)
        if not text:
            return paragraph_xml

        new_text = text
        found_any = False
        for placeholder, value in placeholder_map.items():
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
    """placeholder_map: {literal_placeholder_token: replacement_value}.
    Returns (output_docx_bytes, occurrence_counts) where occurrence_counts
    maps each placeholder to how many times it was actually found and
    replaced (0 means it wasn't found anywhere in the template)."""
    with open(template_file_path, "rb") as f:
        src_bytes = f.read()

    occurrence_counts = {p: 0 for p in placeholder_map}
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
