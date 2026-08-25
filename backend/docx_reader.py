"""
Pulls the plain text out of a .docx file so it can be sent to the LLM for
field discovery / value extraction. A .docx is a zip file containing XML —
we don't need the python-docx library for something this simple, just the
standard library's zipfile + xml modules.
"""

import io
import zipfile
from xml.etree import ElementTree

# Word's XML namespace for text runs/paragraphs.
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# Safety cap so an enormous document doesn't blow up the LLM call's cost or
# context size. Long enough for any realistic contract template.
MAX_CHARS = 120_000


def _extract_text_from_zip_source(zip_source) -> str:
    """zip_source can be a file path (str) or a file-like object (e.g.
    io.BytesIO) — zipfile.ZipFile accepts either."""
    try:
        with zipfile.ZipFile(zip_source) as zf:
            xml_bytes = zf.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError, FileNotFoundError) as e:
        raise ValueError(f"Couldn't read this as a .docx file: {e}")

    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as e:
        raise ValueError(f"This .docx file's contents look corrupted: {e}")

    paragraphs = []
    for paragraph in root.iter(f"{W_NS}p"):
        # Walk every descendant in document order (not just <w:t> elements)
        # so that <w:br/> (a manual line break *within* one paragraph) and
        # <w:tab/> are correctly interleaved with the text around them —
        # otherwise text on visually separate lines inside one paragraph
        # gets silently joined together with no space at all.
        parts = []
        for node in paragraph.iter():
            if node.tag == f"{W_NS}t":
                parts.append(node.text or "")
            elif node.tag == f"{W_NS}br":
                parts.append("\n")
            elif node.tag == f"{W_NS}tab":
                parts.append("\t")
        line = "".join(parts).strip()
        if line:
            paragraphs.append(line)

    text = "\n".join(paragraphs)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n\n[...truncated for length...]"
    return text


def extract_text(docx_path: str) -> str:
    """Returns the document's visible text, paragraphs separated by
    newlines. Raises ValueError if the file isn't a readable .docx.
    For files already saved on disk (e.g. stored templates)."""
    return _extract_text_from_zip_source(docx_path)


def extract_text_from_bytes(file_bytes: bytes) -> str:
    """Same as extract_text, but for a .docx that's only in memory (e.g. a
    freshly uploaded requirements document that we don't want to write to
    disk just to read it once)."""
    return _extract_text_from_zip_source(io.BytesIO(file_bytes))


def extract_text_from_plain_bytes(file_bytes: bytes) -> str:
    """For plain .txt uploads — just decode and apply the same length cap
    as the .docx path, so callers don't need to special-case truncation."""
    text = file_bytes.decode("utf-8", errors="replace")
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n\n[...truncated for length...]"
    return text
