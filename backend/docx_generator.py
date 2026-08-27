"""
Robust DOCX template filler.

Supports:
- {{customer_name}}
- [CUSTOMER_NAME]
- <<CUSTOMER_NAME>>
- split placeholders across Word runs
- placeholders inside normal paragraphs
- placeholders inside tables
- placeholders in headers and footers

The important rule is:
the field's `placeholder` is the exact token that exists in the template.
We never invent a different token during generation.
"""

import io
import re
import zipfile


# Word XML paragraph
PARAGRAPH_RE = re.compile(
    r"<w:p(?:\s[^>]*)?>.*?</w:p>",
    re.DOTALL,
)

PPR_RE = re.compile(
    r"<w:pPr>.*?</w:pPr>",
    re.DOTALL,
)

RPR_RE = re.compile(
    r"<w:rPr>.*?</w:rPr>",
    re.DOTALL,
)

PARA_TOKEN_RE = re.compile(
    r"<w:t(?:\s[^>]*)?>(.*?)</w:t>"
    r"|<w:t(?:\s[^>]*)?/>"
    r"|<w:br(?:\s[^>]*)?/>"
    r"|<w:tab(?:\s[^>]*)?/>",
    re.DOTALL,
)


# document.xml + headers + footers
TEXT_PART_RE = re.compile(
    r"^word/(document|header\d*|footer\d*)\.xml$"
)


class GenerationError(Exception):
    """Raised when generation cannot proceed safely."""


def _xml_unescape(text: str) -> str:
    return (
        text
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
        .replace("&quot;", '"')
        .replace("&apos;", "'")
    )


def _xml_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _paragraph_text(paragraph_xml: str) -> str:
    """
    Extract visible text from a Word paragraph.

    This reconstructs text even when Word has split a placeholder
    across multiple <w:r> elements.
    """
    parts = []

    for match in PARA_TOKEN_RE.finditer(paragraph_xml):
        token = match.group(0)

        if token.startswith("<w:br"):
            parts.append("\n")

        elif token.startswith("<w:tab"):
            parts.append("\t")

        else:
            parts.append(
                _xml_unescape(match.group(1) or "")
            )

    return "".join(parts)


def _first_run_properties(paragraph_xml: str) -> str:
    """
    Preserve formatting from the first run in the paragraph.
    """
    ppr_match = PPR_RE.search(paragraph_xml)

    search_start = (
        ppr_match.end()
        if ppr_match
        else 0
    )

    rpr_match = RPR_RE.search(
        paragraph_xml,
        search_start,
    )

    return (
        rpr_match.group(0)
        if rpr_match
        else ""
    )


def _text_to_runs_xml(
    text: str,
    rpr: str,
) -> str:

    segments = re.split(
        r"(\n|\t)",
        text,
    )

    runs = []

    for segment in segments:

        if segment == "\n":
            runs.append(
                f"<w:r>{rpr}<w:br/></w:r>"
            )

        elif segment == "\t":
            runs.append(
                f"<w:r>{rpr}<w:tab/></w:r>"
            )

        elif segment == "":
            continue

        else:
            runs.append(
                f'<w:r>{rpr}'
                f'<w:t xml:space="preserve">'
                f'{_xml_escape(segment)}'
                f'</w:t>'
                f'</w:r>'
            )

    if not runs:
        runs.append(
            f'<w:r>{rpr}'
            f'<w:t xml:space="preserve"></w:t>'
            f'</w:r>'
        )

    return "".join(runs)


def _rebuild_paragraph(
    paragraph_xml: str,
    new_text: str,
) -> str:

    ppr_match = PPR_RE.search(
        paragraph_xml
    )

    ppr = (
        ppr_match.group(0)
        if ppr_match
        else ""
    )

    rpr = _first_run_properties(
        paragraph_xml
    )

    runs_xml = _text_to_runs_xml(
        new_text,
        rpr,
    )

    return (
        "<w:p>"
        f"{ppr}"
        f"{runs_xml}"
        "</w:p>"
    )


def _normalise_placeholder(
    placeholder: str,
) -> str:
    """
    Do NOT invent a placeholder.

    We only clean whitespace around the exact
    token stored in the template field.
    """
    return str(
        placeholder or ""
    ).strip()


def _replace_in_xml(
    xml_text: str,
    placeholder_map: dict,
    occurrence_counts: dict,
) -> str:

    normalized_map = {}

    for placeholder, value in placeholder_map.items():

        token = _normalise_placeholder(
            placeholder
        )

        if not token:
            continue

        normalized_map[token] = (
            "" if value is None
            else str(value)
        )

        occurrence_counts.setdefault(
            token,
            0,
        )

    if not normalized_map:
        return xml_text

    # Longest first prevents partial placeholder
    # collisions.
    sorted_placeholders = sorted(
        normalized_map.keys(),
        key=len,
        reverse=True,
    )

    def replace_paragraph(match):

        paragraph_xml = match.group(0)

        visible_text = _paragraph_text(
            paragraph_xml
        )

        if not visible_text:
            return paragraph_xml

        new_text = visible_text
        found_any = False

        for placeholder in sorted_placeholders:

            value = normalized_map[
                placeholder
            ]

            count = new_text.count(
                placeholder
            )

            if count > 0:

                new_text = new_text.replace(
                    placeholder,
                    value,
                )

                occurrence_counts[
                    placeholder
                ] = (
                    occurrence_counts.get(
                        placeholder,
                        0,
                    )
                    + count
                )

                found_any = True

        if not found_any:
            return paragraph_xml

        return _rebuild_paragraph(
            paragraph_xml,
            new_text,
        )

    return PARAGRAPH_RE.sub(
        replace_paragraph,
        xml_text,
    )


def generate_docx(
    template_file_path: str,
    placeholder_map: dict,
) -> tuple[bytes, dict]:

    with open(
        template_file_path,
        "rb",
    ) as f:
        source_bytes = f.read()

    output_buffer = io.BytesIO()

    occurrence_counts = {}

    with zipfile.ZipFile(
        io.BytesIO(source_bytes),
        "r",
    ) as source_zip:

        with zipfile.ZipFile(
            output_buffer,
            "w",
            zipfile.ZIP_DEFLATED,
        ) as output_zip:

            for item in source_zip.infolist():

                data = source_zip.read(
                    item.filename
                )

                if TEXT_PART_RE.match(
                    item.filename
                ):

                    try:
                        xml_text = data.decode(
                            "utf-8"
                        )
                    except UnicodeDecodeError:
                        output_zip.writestr(
                            item,
                            data,
                        )
                        continue

                    xml_text = _replace_in_xml(
                        xml_text,
                        placeholder_map,
                        occurrence_counts,
                    )

                    data = xml_text.encode(
                        "utf-8"
                    )

                output_zip.writestr(
                    item,
                    data,
                )

    return (
        output_buffer.getvalue(),
        occurrence_counts,
    )