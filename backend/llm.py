"""
Field discovery — reads a template's text and asks Claude to identify which
pieces of information vary from contract to contract (vendor name, contract
value, dates, etc.) as opposed to the fixed legal wording.

This only runs when an admin clicks "Discover fields" on a template — never
during normal document generation — so it costs a small amount once per
template, not per document.
"""

import json
import os
import re
import urllib.error
import urllib.request

VALID_FIELD_TYPES = {"text", "paragraph", "number", "currency", "date"}


def derive_placeholder(field: dict) -> str:
    """The literal token to find-and-replace in a template's .docx file for
    this field. Uses whatever the AI found (or an admin set manually) if
    present; otherwise falls back to a predictable "[KEY_UPPERCASE]" form
    so generation always has *something* deterministic to look for."""
    explicit = field.get("placeholder")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    return f"[{field['key'].upper()}]"

# Google has been retiring Gemini model versions frequently. Rather than
# hardcode one model name that breaks the moment it's retired, try these in
# order and fall through automatically if one comes back "not found".
# Newest/current first. gemini-3-flash is deliberately excluded — confirmed
# 404 on this account already, no point retrying it.
GEMINI_MODEL_CANDIDATES = ["gemini-3.5-flash", "gemini-2.5-flash"]


class FieldDiscoveryError(Exception):
    """Raised for any problem getting a usable field list back — missing
    API key, network failure, or a response we couldn't parse."""


def _call_gemini_model(prompt: str, model: str) -> str:
    """Calls one specific Gemini model. Raises FieldDiscoveryError on any
    failure, including a distinguishable message when the model itself
    isn't found (so the caller can decide whether to try the next one)."""
    api_key = os.environ.get("GEMINI_API_KEY")
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        if e.code == 404:
            raise FieldDiscoveryError(f"MODEL_NOT_FOUND: {model}: {detail}")
        raise FieldDiscoveryError(f"The AI request failed ({e.code}): {detail}")
    except urllib.error.URLError as e:
        raise FieldDiscoveryError(f"Couldn't reach the AI service: {e.reason}")
    except json.JSONDecodeError:
        raise FieldDiscoveryError("The AI service returned a response that wasn't valid JSON.")

    try:
        candidates = response_data["candidates"]
        parts = candidates[0]["content"]["parts"]
        return "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError, TypeError):
        raise FieldDiscoveryError("The AI service returned an unexpected response format.")


def _call_gemini(prompt: str) -> str:
    """The one function that actually talks to the network. Kept separate
    from everything else so the rest of this module can be tested without
    a real API key or network access. Tries each candidate model in turn,
    skipping past any that Google has retired."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise FieldDiscoveryError(
            "GEMINI_API_KEY is not set. Add it to a .env file in this "
            "folder (see README.md) before using AI field discovery."
        )

    last_error = None
    for model in GEMINI_MODEL_CANDIDATES:
        try:
            return _call_gemini_model(prompt, model)
        except FieldDiscoveryError as e:
            if str(e).startswith("MODEL_NOT_FOUND"):
                last_error = e
                continue
            raise  # a real error (bad key, rate limit, etc) — don't mask it by retrying

    raise FieldDiscoveryError(
        "None of the AI models this app knows about are available on your API key "
        f"right now. Last error: {last_error}"
    )


def _build_prompt(template_name: str, document_type: str, document_text: str) -> str:
    return f"""You are helping a procurement team set up a contract template in a document generation system.

Below is the text of a contract template called "{template_name}" (document type: {document_type}).

Identify the pieces of information that CHANGE from one contract to the next when this template is used — such as counterparty name, contract value, dates, scope of work — as opposed to the fixed legal wording that stays the same every time. This template likely contains literal placeholder tokens (often in square brackets, e.g. [VENDOR_NAME], [TOTAL_PRICE], [EFFECTIVE_DATE]) marking exactly where each piece of variable information goes.

Respond with ONLY a JSON array (no explanation, no markdown code fences, nothing else) where each item has exactly these keys:
- "key": a short snake_case machine identifier, e.g. "vendor_name"
- "label": a short human-readable label, e.g. "Vendor name"
- "type": one of "text", "paragraph", "number", "currency", "date"
- "required": true or false
- "placeholder": the exact literal placeholder token as it appears verbatim in the document text (e.g. "[VENDOR_NAME]"), copied exactly including brackets/formatting — or null if you can't find a literal placeholder for this field.

Template text:
---
{document_text}
---"""


def _sanitize_key(raw_key: str, label: str, used_keys: set) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", (raw_key or label or "field").lower()).strip("_")
    base = base or "field"
    key = base
    n = 2
    while key in used_keys:
        key = f"{base}_{n}"
        n += 1
    used_keys.add(key)
    return key


def _parse_fields_response(raw_text: str) -> list:
    text = raw_text.strip()
    # Models sometimes wrap JSON in code fences despite instructions not to.
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Last resort: grab the first [...] block in the response.
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            raise FieldDiscoveryError(
                "The AI's response wasn't in the expected format. Try again, "
                "or add the fields manually below."
            )
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            raise FieldDiscoveryError(
                "The AI's response wasn't valid — try again, or add fields manually."
            )

    if not isinstance(parsed, list):
        raise FieldDiscoveryError("The AI didn't return a list of fields — try again.")

    fields = []
    used_keys = set()
    for item in parsed:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        if not label:
            continue
        field_type = item.get("type") if item.get("type") in VALID_FIELD_TYPES else "text"
        key = _sanitize_key(item.get("key", ""), label, used_keys)
        raw_placeholder = item.get("placeholder")
        placeholder = raw_placeholder.strip() if isinstance(raw_placeholder, str) and raw_placeholder.strip() else None
        fields.append(
            {
                "key": key,
                "label": label,
                "type": field_type,
                "required": bool(item.get("required", False)),
                "placeholder": placeholder,
            }
        )

    if not fields:
        raise FieldDiscoveryError(
            "The AI didn't identify any fields in this document — try again, "
            "or add fields manually below."
        )
    return fields


def discover_fields(template_name: str, document_type: str, document_text: str) -> list:
    """Returns a list of field dicts: [{key, label, type, required}, ...].
    Raises FieldDiscoveryError with a message safe to show the admin."""
    if not document_text.strip():
        raise FieldDiscoveryError(
            "This template's file appears to have no readable text."
        )
    prompt = _build_prompt(template_name, document_type, document_text)
    raw_response = _call_gemini(prompt)
    return _parse_fields_response(raw_response)


# ============================================================================
# Field VALUE extraction — reads a requirements document and pulls out the
# actual values for a template's already-confirmed fields. Uses the same
# _call_gemini network layer as discovery above; only the prompt and the
# response shape differ (an object of key -> value, not a list of field
# definitions).
# ============================================================================


def _build_extraction_prompt(fields: list, document_text: str) -> str:
    field_lines = "\n".join(
        f"- {f['key']} (label: \"{f['label']}\", type: {f['type']})" for f in fields
    )
    return f"""You are extracting specific information from a procurement requirements document, to populate a contract.

Below is a list of fields to find values for, and the text of a requirements document to find them in.

For each field, find its value in the document. If a field's value genuinely isn't in the document, use null for that field — never guess, invent, or estimate a value that isn't actually there.

Respond with ONLY a JSON object (no explanation, no markdown code fences, nothing else) mapping each field's key to either a string value or null. Every key listed below must appear in your response.

Fields:
{field_lines}

Document text:
---
{document_text}
---"""


def _parse_extraction_response(raw_text: str, expected_keys: list) -> dict:
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise FieldDiscoveryError(
                "The AI's response wasn't in the expected format. Try again."
            )
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            raise FieldDiscoveryError("The AI's response wasn't valid — try again.")

    if not isinstance(parsed, dict):
        raise FieldDiscoveryError("The AI didn't return the expected field values — try again.")

    result = {}
    for key in expected_keys:
        value = parsed.get(key)
        if isinstance(value, (str, int, float)) and str(value).strip():
            result[key] = str(value).strip()
        else:
            # Missing key, null, empty string, or an unexpected type (a
            # list/dict the model shouldn't have returned) — all treated the
            # same way: not found, never invented.
            result[key] = None
    return result


def extract_field_values(fields: list, document_text: str) -> dict:
    """Returns {key: value_or_None} for every field in `fields`. Raises
    FieldDiscoveryError with a message safe to show the user."""
    if not fields:
        raise FieldDiscoveryError("This template has no fields configured yet.")
    if not document_text.strip():
        raise FieldDiscoveryError("This document appears to have no readable text.")

    prompt = _build_extraction_prompt(fields, document_text)
    raw_response = _call_gemini(prompt)
    expected_keys = [f["key"] for f in fields]
    return _parse_extraction_response(raw_response, expected_keys)
