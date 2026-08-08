"""
SOLGulf Procurement Document Generator - Frontend Mockup (Final)
-------------------------------------------------------------------
UI-only mockup for stakeholder review. No real extraction, LLM call,
or document generation happens here - all data is hardcoded/mocked
so the full 3-step flow can be demoed without any backend.

Screens:
    1. Upload Requirements & Select Template
    2. Review Extracted Fields
    3. Document Ready

A sidebar "Jump to screen" control is included purely for demo
purposes, so you can show any screen directly without clicking
through the whole flow each time. It is clearly separated from the
main app content and would not exist in the real product.

Run with:
    streamlit run mockup_app_final.py
"""

import base64
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="SOLGulf Procurement Generator",
    page_icon="\U0001F4C4",
    layout="centered",
)

# ----------------------------------------------------------------
# Styling
# ----------------------------------------------------------------
# NOTE on theme-safety: Streamlit's dark/light mode swaps its own
# --text-color variable automatically. That's fine for elements that
# sit on the app's default background. But any element we give a
# FIXED custom background (badges, file cards, the success circle)
# must also get a FIXED, explicit text color - otherwise it inherits
# --text-color and can end up e.g. white text on a pale mint card in
# dark mode (unreadable). Every custom-background block below now
# pins its own foreground color instead of inheriting the theme's.
st.markdown(
    """
    <style>
    /* Theme-aware secondary-text colours.
       LIGHT MODE (default here): secondary/body/helper/caption text was
       previously a pale grey (#8A897F-family) that read as too light
       against a white background. It's now a clearly-readable dark
       grey - --secondary-text-color for normal secondary copy (labels,
       helper text, captions, status text), --subtle-text-color a touch
       lighter for genuinely tertiary fine-print (e.g. "Template version
       v1.0"), while still staying solidly dark and readable.
       DARK MODE (media query below): left exactly as it already was -
       the same light-grey values used before this pass - since that
       already reads correctly against the dark background and darkening
       it further (e.g. to the light-mode #4B5563) would make it fail
       contrast against a dark background instead. */
    :root {
        --secondary-text-color: #4B5563;
        --subtle-text-color: #5B6472;
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --secondary-text-color: #667085;
            --subtle-text-color: #8A8F98;
        }
    }

    /* Screen-intro captions ONLY (the 4 st.caption() lines directly under
       each screen's title - upload / processing / review / download).
       These need to read as strong subheading text, not secondary/helper
       copy: near-black in light mode, white in dark mode. Scoped
       narrowly via .st-key-screen_intro_* (see st.container(key=...)
       wrappers below) so no other caption, label, helper-text, or
       status text on the page is affected.

       Deliberately NOT using @media (prefers-color-scheme) here: that
       only reflects the OS/browser's theme preference, not which theme
       is actually active inside the Streamlit app. If a user overrides
       the theme via Streamlit's own Settings menu independently of
       their OS setting, a prefers-color-scheme rule goes stale (e.g.
       OS = dark, in-app theme switched to light -> text stays white on
       a white background). Streamlit's built-in --text-color variable,
       by contrast, is live-updated by Streamlit itself the instant the
       in-app theme changes, so aliasing to it here tracks the real
       active theme rather than the OS preference. */
    :root {
        --screen-intro-text-color: var(--text-color);
    }
    .st-key-screen_intro_upload [data-testid="stCaptionContainer"],
    .st-key-screen_intro_upload [data-testid="stCaptionContainer"] p,
    .st-key-screen_intro_upload [data-testid="stCaptionContainer"] small,
    .st-key-screen_intro_processing [data-testid="stCaptionContainer"],
    .st-key-screen_intro_processing [data-testid="stCaptionContainer"] p,
    .st-key-screen_intro_processing [data-testid="stCaptionContainer"] small,
    .st-key-screen_intro_review [data-testid="stCaptionContainer"],
    .st-key-screen_intro_review [data-testid="stCaptionContainer"] p,
    .st-key-screen_intro_review [data-testid="stCaptionContainer"] small,
    .st-key-screen_intro_download [data-testid="stCaptionContainer"],
    .st-key-screen_intro_download [data-testid="stCaptionContainer"] p,
    .st-key-screen_intro_download [data-testid="stCaptionContainer"] small {
        color: var(--screen-intro-text-color) !important;
    }

    .block-container { padding-top: 3rem; padding-bottom: 3rem; max-width: 700px; }

    .brand-header-row {
        display: flex; align-items: center; justify-content: space-between;
        gap: 16px; margin-bottom: 0.25rem;
    }
    .brand-header-text { display: flex; flex-direction: column; }
    .brand-header-logo { display: flex; align-items: center; flex-shrink: 0; }
    .brand-header-logo img { display: block; }

    .step-indicator-text {
        font-size: 12px; font-weight: 600; color: var(--subtle-text-color);
        text-transform: uppercase; letter-spacing: 0.5px; margin: 0 0 4px;
    }
    .page-title {
        font-size: 30px; font-weight: 800; line-height: 1.25;
        margin: 0; letter-spacing: -0.4px;
        color: var(--text-color); /* fine: sits on the app background, so it can follow theme */
    }

    .step-tracker {
        display: flex; align-items: flex-start; gap: 0; margin: 1.25rem 0 1rem;
    }
    .step-tracker .step-unit {
        display: flex; flex-direction: column; align-items: center; gap: 6px;
        width: 22px; flex-shrink: 0;
    }
    .step-tracker .step-label {
        font-size: 14.5px; color: var(--secondary-text-color); font-weight: 500; white-space: nowrap;
    }
    .step-tracker .step-label.active { color: #0B2E4F; font-weight: 700; }
    .step-tracker .step-label.done { color: #4FC3A1; font-weight: 600; }
    .step-dot {
        width: 22px; height: 22px; border-radius: 50%; font-size: 11px;
        display: flex; align-items: center; justify-content: center;
        font-weight: 600; color: #FFFFFF; /* explicit - all three dot states use a solid fill */
        flex-shrink: 0;
    }
    .step-dot.active { background: #0B2E4F; }
    .step-dot.done { background: #4FC3A1; }
    .step-dot.inactive { background: #E4E2DA; color: var(--secondary-text-color); }
    .step-line { width: 40px; height: 2px; background: #E4E2DA; margin-top: 10px; }
    .step-line.done { background: #4FC3A1; } /* was always grey before, even past completed steps */

    .status-badge {
        display: inline-block; padding: 4px 12px; border-radius: 999px;
        font-size: 11px; font-weight: 600; margin-left: 8px;
    }
    .status-ready { background: #E1F5EE; color: #085041; }
    .status-warning { background: #FAEEDA; color: #633806; }
    .status-uploaded { background: #4FC3A1; color: #FFFFFF !important; }

    .file-card {
        display: flex; align-items: center; justify-content: space-between;
        border: 1px solid #E4E2DA; border-radius: 8px; padding: 10px 14px;
        background: rgba(128, 128, 128, 0.08); margin-bottom: 1rem;
        color: var(--text-color); /* neutral card: inheriting theme text is fine here */
    }
    /* Fixed light-mint background needs a fixed dark foreground - this was the
       bug: it previously inherited var(--text-color), so in dark mode the
       filename/badge text rendered near-white on a pale green card. */
    .file-card.success {
        background: #E1F5EE;
        border-color: #9FE1CB;
        color: #085041 !important;
        padding: 12px 16px;
        margin-top: 2px;
    }
    .file-card.success span { color: #085041 !important; }
    .file-card .file-meta-row {
        display: flex; align-items: center; gap: 10px;
    }
    .file-check-icon {
        width: 26px; height: 26px; border-radius: 50%; background: #4FC3A1;
        display: flex; align-items: center; justify-content: center;
        color: #FFFFFF !important; font-size: 13px; font-weight: 700; flex-shrink: 0;
    }
    .file-text-col { display: flex; flex-direction: column; line-height: 1.35; }
    .file-name-text { font-size: 13.5px; font-weight: 600; color: #085041 !important; }
    .file-sub-text { font-size: 11.5px; color: #3E7A68 !important; font-weight: 500; }

    /* Remove/clear ("x") action that sits next to the uploaded file card
       on Step 1. Scoped via st.container(key=...), which Streamlit tags
       with a stable "st-key-..." class we can target directly. */
    .st-key-remove_file_container { display: flex; align-items: center; height: 100%; }
    .st-key-remove_file_container button {
        width: 30px !important; height: 30px !important; padding: 0 !important;
        min-height: 0 !important; border-radius: 50% !important;
        border: 1px solid #E4E2DA !important; background: transparent !important;
        color: var(--secondary-text-color) !important; font-size: 13px !important; line-height: 1 !important;
        margin-top: 10px !important;
    }
    .st-key-remove_file_container button:hover {
        border-color: #D64545 !important; color: #D64545 !important;
        background: rgba(214, 69, 69, 0.06) !important;
    }

    .section-block { margin-bottom: 1.4rem; }
    .section-block.tight { margin-bottom: 0.6rem; }
    .section-block.requirements-block { margin-top: 0.75rem; }
    .section-label { font-size: 13px; color: var(--secondary-text-color); margin-bottom: 6px; font-weight: 500; }
    .helper-text { font-size: 12.5px; color: var(--secondary-text-color); margin: 6px 0 0; line-height: 1.4; }

    /* Native st.caption() text (the page-intro line under each screen's
       title, e.g. "Upload procurement requirements and select an
       approved contract template.") renders with Streamlit's own
       default caption grey, which is too light/washed out - same issue
       as the custom .section-label/.helper-text classes above, just on
       Streamlit's built-in component instead of our own markup. */
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p,
    [data-testid="stCaptionContainer"] small,
    .stCaption, .stCaption p {
        color: var(--secondary-text-color) !important;
    }

    /* Tightens the gap between the upload dropzone, the "Continue to
       Review" button, and the helper text beneath it. Scoped to this
       one wrapper via st.container(key=...) so nothing else on the
       page is affected. */
    .st-key-upload_continue_block { margin-top: -0.9rem; }
    .st-key-upload_continue_block [data-testid="stVerticalBlock"] {
        gap: 0.3rem !important;
    }

    /* Single divider style used consistently between the page intro and
       the section that follows it, on every screen. Margins are kept
       small and symmetric; Streamlit's own vertical gap between blocks
       provides the rest of the spacing, so we no longer need a
       screen-by-screen negative-margin "pull up" hack (that inconsistent
       hack - applied on some screens but not others - was the source of
       the uneven/doubled-looking gaps). */
    .compact-divider { margin: 0.6rem 0 !important; opacity: 0.35; }

    .success-circle {
        width: 52px; height: 52px; border-radius: 50%; background: #E1F5EE;
        display: flex; align-items: center; justify-content: center;
        margin: 0 auto 1rem; font-size: 24px; color: #085041 !important;
    }

    /* Drag-and-drop styling for the native Streamlit uploader dropzone */
    [data-testid="stFileUploaderDropzone"] {
        border: 1.5px dashed #B9C4CE !important;
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px !important;
        min-height: 128px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 20px 16px !important;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #0B2E4F !important;
        background: rgba(11, 46, 79, 0.08) !important;
    }
    /* The native icon/text block and the "Browse files" button used to sit
       as two separate, misaligned groups (button left, text centred), and
       the native icon was duplicated above the button. The button now
       carries its own real SVG icon plus the "Upload document" label
       (see button::before / ::after below), so the native instructions
       block is no longer shown at all - it would just add a second,
       redundant icon and extra vertical space. */
    [data-testid="stFileUploaderDropzoneInstructions"] {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzone"] button {
        order: 1 !important;
        font-size: 0 !important; line-height: 0 !important;
        background: transparent !important;
        border: 1px solid #0B2E4F !important;
        border-radius: 8px !important;
        padding: 9px 20px !important;
        min-height: 0 !important;
        display: flex !important; align-items: center !important;
        justify-content: center !important; gap: 8px !important;
    }
    /* The native button renders its own label text in one or more child
       nodes that carry their own explicit font-size, so they don't
       inherit the font-size: 0 set on the button above - that leftover
       text was still rendering ("Upload") next to our injected ::before
       icon, producing a duplicated label. Zeroing every child node (not
       just span) removes all of that leftover native text without
       touching the icon/label we render via pseudo-elements below. */
    [data-testid="stFileUploaderDropzone"] button * {
        font-size: 0 !important;
    }
    /* Upload icon (::before) and label (::after) - both become flex
       items of the button (display: flex above), so the icon sits
       neatly to the left of "Upload document" with a small, consistent
       gap and stays vertically centred with the text.
       The icon is a real inline SVG (a plain up-arrow-into-tray glyph,
       matching the outline style Streamlit itself uses for this
       control), embedded as a CSS data URI - not a unicode character,
       emoji, or icon-font glyph. Previously this was
       content: "\\2191" (the CSS escape for an up-arrow) inside a
       normal, non-raw Python string. Python's own parser reads a
       backslash followed by octal digits as an octal escape, so
       "\\2191" was silently consumed as "\\21" (an unprintable
       control character) followed by the two literal characters "9"
       and "1" - exactly the stray "91" that was showing up on the
       button. An explicit SVG image via a data URI sidesteps that
       whole class of escaping bug. */
    [data-testid="stFileUploaderDropzone"] button::before {
        content: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNyIgaGVpZ2h0PSIxNyIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMwQjJFNEYiIHN0cm9rZS13aWR0aD0iMi4yIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0xMiAzdjEyIi8+PHBhdGggZD0ibTcgOCA1LTUgNSA1Ii8+PHBhdGggZD0iTTUgMjFoMTQiLz48L3N2Zz4=");
        display: block; width: 17px; height: 17px; line-height: 0;
    }
    [data-testid="stFileUploaderDropzone"] button::after {
        content: "Upload document";
        font-size: 14px; font-weight: 600; color: #0B2E4F; line-height: 1.3;
    }
    [data-testid="stFileUploaderDropzone"] button:hover {
        background: rgba(11, 46, 79, 0.06) !important;
    }
    /* Helper copy below the button, as two independently-spaced lines
       (rather than one block with uniform line-height) so the gap under
       the button (~24px) can be larger than the gap between the two
       lines themselves (~7px), per the requested spacing hierarchy.
       These reuse the dropzone's own ::before/::after slots, now free
       since the icon moved into the button above. */
    [data-testid="stFileUploaderDropzone"]::before {
        content: "or drag and drop your file here";
        order: 2;
        display: block; text-align: center;
        font-size: 12.5px; color: var(--secondary-text-color); line-height: 1.4;
        margin-top: 24px;
    }
    [data-testid="stFileUploaderDropzone"]::after {
        content: "DOCX, TXT  \u2022  Maximum 200MB";
        order: 3;
        display: block; text-align: center;
        font-size: 12.5px; color: var(--subtle-text-color); line-height: 1.4;
        margin-top: 7px;
    }

    /* Subtle hover state for the template dropdown */
    [data-baseweb="select"] > div {
        border-radius: 8px !important;
    }
    [data-baseweb="select"] > div:hover {
        border-color: #0B2E4F !important;
        background: rgba(11, 46, 79, 0.04) !important;
    }

    /* Text inputs (Step 2 review fields) - these were previously reading
       as grey/disabled-looking, which worked against the screen's purpose
       of showing users they CAN edit the extracted values. Give them a
       clearly editable, light input surface with the same 8px rounded
       corners used by the select/button/dropzone elsewhere. */
    [data-testid="stTextInput"] > div {
        background: #FFFFFF !important;
        border: 1px solid #D8D5CB !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }
    [data-testid="stTextInput"] > div:focus-within {
        border-color: #0B2E4F !important;
    }
    [data-testid="stTextInput"] input {
        background: transparent !important;
        color: #1F2937 !important;
        -webkit-text-fill-color: #1F2937 !important;
    }

    /* SOLGulf primary blue for primary buttons (overrides Streamlit's default red) */
    button[kind="primary"], button[data-testid="stBaseButton-primary"] {
        background-color: #0B2E4F !important;
        border-color: #0B2E4F !important;
        color: #FFFFFF !important;
        padding-top: 0.65rem !important;
        padding-bottom: 0.65rem !important;
    }
    button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
        background-color: #123f6b !important;
        border-color: #123f6b !important;
    }
    button[kind="primary"]:disabled, button[data-testid="stBaseButton-primary"]:disabled {
        background-color: #B9C4CE !important;
        border-color: #B9C4CE !important;
        color: #FFFFFF !important;
        opacity: 0.7;
    }

    .template-info-title { font-size: 13px; font-weight: 700; color: var(--text-color); margin-bottom: 2px; }
    .template-info-version { font-size: 11.5px; color: var(--subtle-text-color); margin-bottom: 8px; }
    .template-info-fields { font-size: 12.5px; color: var(--text-color); margin: 4px 0 0; padding-left: 18px; line-height: 1.6; }

    /* Only the bottom border of each row is used to separate rows -
       the list previously also carried its own border-top, which sat
       right underneath the divider above it and read as a doubled
       line. The last row's border is dropped too, so the list doesn't
       end on a stray line of its own. */
    .process-list { margin: 0.5rem 0 1.75rem; }
    .process-item {
        display: flex; align-items: center; gap: 12px;
        padding: 12px 0; border-bottom: 1px solid #E4E2DA;
    }
    .process-item:last-child { border-bottom: none; }
    .process-item .process-icon {
        width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
        font-size: 11px; font-weight: 700;
    }
    .process-item.done .process-icon { background: #4FC3A1; color: #FFFFFF !important; }
    .process-item.pending .process-icon { background: #E4E2DA; color: var(--secondary-text-color) !important; }
    .process-item.done .process-item-text { color: var(--text-color); font-weight: 500; font-size: 14px; }
    .process-item.pending .process-item-text { color: var(--secondary-text-color); font-weight: 500; font-size: 14px; }

    hr, [data-testid="stDivider"] { opacity: 0.4; margin: 1.1rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------
# Mock data (hardcoded - stands in for real extraction output)
# ----------------------------------------------------------------
TEMPLATE_OPTIONS = [
    "Master Services Agreement (MSA)",
    "Statement of Work (SoW)",
    "Service Agreement",
    "Contract Amendment",
]

TEMPLATE_DESCRIPTIONS = {
    "Master Services Agreement (MSA)": (
        "Defines the main terms for working with a supplier."
    ),
    "Statement of Work (SoW)": (
        "Defines the scope, deliverables, and timeline for a specific project."
    ),
    "Service Agreement": (
        "Defines the terms for a standalone service engagement."
    ),
    "Contract Amendment": (
        "Records changes to dates, values, or terms on an existing contract."
    ),
}

TEMPLATE_VERSIONS = {
    "Master Services Agreement (MSA)": "v2.3",
    "Statement of Work (SoW)": "v1.6",
    "Service Agreement": "v1.4",
    "Contract Amendment": "v1.1",
}

TEMPLATE_REQUIRED_FIELDS = {
    "Master Services Agreement (MSA)": [
        "Vendor name", "Service description", "Contract value",
        "Currency", "Start date", "End date", "Payment terms",
    ],
    "Statement of Work (SoW)": [
        "Vendor name", "Project scope", "Deliverables",
        "Timeline", "Contract value",
    ],
    "Service Agreement": [
        "Vendor name", "Service description", "Contract value",
        "Start date", "End date",
    ],
    "Contract Amendment": [
        "Original contract reference", "Amended terms", "Effective date",
    ],
}

MOCK_OUTPUT_NAME = "MSA_GulfMarine_2026.docx"

MOCK_FIELDS = {
    "vendor_name": "Gulf Marine Services Ltd.",
    "service_description": "Offshore maintenance services",
    "contract_value": "850,000",
    "currency": "SAR",
    "start_date": "1 September 2026",
    "end_date": "31 August 2027",
    "payment_terms": "Not found",  # deliberately missing to show the warning state
}

# STEP_SCREENS drives the 3-dot step tracker/brand header numbering (the
# real product steps). "processing" is an interstitial screen shown while
# step 1 hands off to step 2, so it intentionally isn't its own numbered
# step - it borrows step 1's position. ALL_SCREENS is only used for the
# demo sidebar so every screen can still be jumped to directly.
STEP_SCREENS = ["upload", "review", "download"]
ALL_SCREENS = ["upload", "processing", "review", "download"]
SCREEN_LABELS = {
    "upload": "Upload Requirements & Select Template",
    "processing": "Analysing Requirements Document",
    "review": "Review Extracted Fields",
    "download": "Document Ready",
}

# ----------------------------------------------------------------
# Session state
# ----------------------------------------------------------------
if "screen" not in st.session_state:
    st.session_state.screen = "upload"
if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False
if "uploaded_file_data" not in st.session_state:
    st.session_state.uploaded_file_data = None  # {"name": str, "size": str} or None
if "uploader_version" not in st.session_state:
    st.session_state.uploader_version = 0


def go_to(screen_name: str):
    st.session_state.screen = screen_name


def reset_flow():
    st.session_state.screen = "upload"
    st.session_state.file_uploaded = False
    st.session_state.uploaded_file_data = None
    st.session_state.uploader_version += 1


def remove_uploaded_file():
    """Clears the single uploaded document and resets the upload zone to
    its initial empty state. Bumping uploader_version changes the
    file_uploader's key, which is Streamlit's supported way to reset a
    file uploader widget."""
    st.session_state.uploaded_file_data = None
    st.session_state.file_uploaded = False
    st.session_state.uploader_version += 1


# ----------------------------------------------------------------
# Shared components
# ----------------------------------------------------------------
def _logo_html() -> str:
    """Inline the logo as base64 so it can sit in the same flex row as the
    heading text and align vertically with it. Falls back to a text
    wordmark if the asset isn't present (e.g. in this mockup sandbox)."""
    logo_path = Path("assets/solgulf_logo.png")
    if logo_path.exists():
        encoded = base64.b64encode(logo_path.read_bytes()).decode()
        return f'<img src="data:image/png;base64,{encoded}" width="90" />'
    return '<div style="font-weight:600; color:#0B2E4F; font-size:16px;">SOLGulf</div>'


def brand_header(step: int, total_steps: int, heading: str):
    st.markdown(
        f"""
        <div class="brand-header-row">
            <div class="brand-header-text">
                <p class="step-indicator-text">Step {step} of {total_steps}</p>
                <p class="page-title">{heading}</p>
            </div>
            <div class="brand-header-logo">{_logo_html()}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


STEP_SHORT_LABELS = {"upload": "Upload", "review": "Review", "download": "Generate"}


def step_tracker(current_step: int):
    total_steps = len(STEP_SCREENS)
    dots_html = ""
    for i in range(1, total_steps + 1):
        if i < current_step:
            state = "done"
        elif i == current_step:
            state = "active"
        else:
            state = "inactive"
        short_label = STEP_SHORT_LABELS[STEP_SCREENS[i - 1]]
        dots_html += (
            f'<div class="step-unit">'
            f'<div class="step-dot {state}">{i}</div>'
            f'<span class="step-label {state}">{short_label}</span>'
            f'</div>'
        )
        if i != total_steps:
            # the connecting line is "done" only once we've actually passed that step
            line_state = "done" if i < current_step else ""
            dots_html += f'<div class="step-line {line_state}"></div>'

    st.markdown(
        f"""
        <div class="step-tracker">
            {dots_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------
# Demo-only sidebar
# ----------------------------------------------------------------
with st.sidebar:
    st.caption("DEMO CONTROLS (not part of the real product)")
    screen_choice = st.radio(
        "Jump to screen",
        options=ALL_SCREENS,
        format_func=lambda s: SCREEN_LABELS[s],
        index=ALL_SCREENS.index(st.session_state.screen),
    )
    if screen_choice != st.session_state.screen:
        st.session_state.screen = screen_choice
        if screen_choice == "upload":
            st.session_state.file_uploaded = False
            st.session_state.uploaded_file_data = None
        st.rerun()


# ================= SCREEN 1: UPLOAD =================
if st.session_state.screen == "upload":

    brand_header(1, len(STEP_SCREENS), SCREEN_LABELS["upload"])
    step_tracker(1)
    with st.container(key="screen_intro_upload"):
        st.caption("Upload procurement requirements and select an approved contract template.")
    st.markdown('<hr class="compact-divider" />', unsafe_allow_html=True)

    st.markdown('<div class="section-block tight">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Document template</div>', unsafe_allow_html=True)
    template_choice = st.selectbox(
        "Template", TEMPLATE_OPTIONS, label_visibility="collapsed"
    )
    with st.popover("\u24D8 View template details", use_container_width=False):
        version = TEMPLATE_VERSIONS.get(template_choice, "v1.0")
        required_fields = TEMPLATE_REQUIRED_FIELDS.get(template_choice, [])
        fields_html = "".join(f"<li>{field}</li>" for field in required_fields)
        st.markdown(
            f"""
            <div class="template-info-title">{template_choice}</div>
            <div class="template-info-version">Template version {version}</div>
            <p class="helper-text" style="margin:0 0 8px;">
                {TEMPLATE_DESCRIPTIONS[template_choice]}
            </p>
            <div class="section-label" style="margin-bottom:2px;">Required fields</div>
            <ul class="template-info-fields">{fields_html}</ul>
            """,
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-block tight requirements-block">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Requirements document</div>', unsafe_allow_html=True)

    has_file = st.session_state.uploaded_file_data is not None

    if not has_file:
        # Single-file dropzone. Once a file lands here it's promoted into
        # uploaded_file_data and the dropzone itself stops rendering, so
        # there is never a second "upload another" box sitting alongside
        # the uploaded file.
        uploaded_file = st.file_uploader(
            "Upload document",
            type=["docx", "txt"],
            label_visibility="collapsed",
            key=f"requirements_uploader_{st.session_state.uploader_version}",
        )
        if uploaded_file is not None:
            file_size_kb = max(uploaded_file.size / 1024, 0.1)
            file_size_display = (
                f"{file_size_kb / 1024:.1f} MB" if file_size_kb >= 1024 else f"{file_size_kb:.0f} KB"
            )
            st.session_state.uploaded_file_data = {
                "name": uploaded_file.name,
                "size": file_size_display,
            }
            st.session_state.file_uploaded = True
            st.rerun()
    else:
        file_data = st.session_state.uploaded_file_data
        card_col, remove_col = st.columns([11, 1], gap="small")
        with card_col:
            st.markdown(
                f"""
                <div class="file-card success">
                    <div class="file-meta-row">
                        <div class="file-check-icon">&#10003;</div>
                        <div class="file-text-col">
                            <span class="file-name-text">{file_data['name']}</span>
                            <span class="file-sub-text">Uploaded successfully &nbsp;\u2022&nbsp; {file_data['size']} &nbsp;\u2022&nbsp; ready for extraction</span>
                        </div>
                    </div>
                    <span class="status-badge status-uploaded">Uploaded</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with remove_col:
            with st.container(key="remove_file_container"):
                st.button(
                    "\u2715",
                    key="remove_file_btn",
                    help="Remove document",
                    on_click=remove_uploaded_file,
                )
    st.markdown('</div>', unsafe_allow_html=True)

    ready = has_file
    with st.container(key="upload_continue_block"):
        st.button(
            "Continue to Review \u2192",
            type="primary",
            use_container_width=True,
            disabled=not ready,
            on_click=go_to,
            args=("processing",),
        )
        if not ready:
            st.markdown(
                '<p class="helper-text">Upload a requirements document to continue.</p>',
                unsafe_allow_html=True,
            )


# ================= INTERSTITIAL: ANALYSING DOCUMENT =================
elif st.session_state.screen == "processing":

    brand_header(1, len(STEP_SCREENS), SCREEN_LABELS["processing"])
    step_tracker(1)
    with st.container(key="screen_intro_processing"):
        st.caption(
            "The system is reading your requirements document and extracting the "
            "information needed to populate the selected template."
        )
    st.markdown('<hr class="compact-divider" />', unsafe_allow_html=True)

    process_steps = [
        ("Reading document", "done"),
        ("Preparing document content", "done"),
        ("Extracting supplier information", "pending"),
        ("Mapping fields to template", "pending"),
    ]
    items_html = ""
    for label, state in process_steps:
        icon = "&#10003;" if state == "done" else "&#8987;"
        items_html += (
            f'<div class="process-item {state}">'
            f'<div class="process-icon">{icon}</div>'
            f'<span class="process-item-text">{label}</span>'
            f'</div>'
        )
    st.markdown(f'<div class="process-list">{items_html}</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.button("\u2190 Back", use_container_width=True, on_click=go_to, args=("upload",))
    with col2:
        st.button(
            "Continue to review \u2192",
            type="primary",
            use_container_width=True,
            on_click=go_to,
            args=("review",),
        )


# ================= SCREEN 2: REVIEW =================
elif st.session_state.screen == "review":

    brand_header(2, len(STEP_SCREENS), SCREEN_LABELS["review"])
    step_tracker(2)
    with st.container(key="screen_intro_review"):
        st.caption("Confirm or correct the fields below before generating the document.")
    st.markdown('<hr class="compact-divider" />', unsafe_allow_html=True)

    vendor_name = st.text_input("Vendor name", value=MOCK_FIELDS["vendor_name"])
    service_desc = st.text_input(
        "Service description", value=MOCK_FIELDS["service_description"]
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        contract_value = st.text_input("Contract value", value=MOCK_FIELDS["contract_value"])
    with col2:
        currency = st.text_input("Currency", value=MOCK_FIELDS["currency"])

    col3, col4 = st.columns(2)
    with col3:
        start_date = st.text_input("Start date", value=MOCK_FIELDS["start_date"])
    with col4:
        end_date = st.text_input("End date", value=MOCK_FIELDS["end_date"])

    st.write("")
    payment_missing = MOCK_FIELDS["payment_terms"].lower() == "not found"
    if payment_missing:
        st.markdown(
            '<div class="section-label">Payment terms '
            '<span class="status-badge status-warning">Needs verification</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="section-label">Payment terms</div>', unsafe_allow_html=True)

    payment_terms = st.text_input(
        "Payment terms", value=MOCK_FIELDS["payment_terms"], label_visibility="collapsed"
    )
    if payment_missing:
        st.markdown(
            '<p class="helper-text">This field could not be extracted automatically - '
            'please confirm it manually before generating the document.</p>',
            unsafe_allow_html=True,
        )

    st.write("")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.button("\u2190 Back", use_container_width=True, on_click=go_to, args=("upload",))
    with col2:
        st.button(
            "Generate document",
            type="primary",
            use_container_width=True,
            on_click=go_to,
            args=("download",),
        )


# ================= SCREEN 3: DOWNLOAD =================
elif st.session_state.screen == "download":

    brand_header(3, len(STEP_SCREENS), SCREEN_LABELS["download"])
    step_tracker(3)
    with st.container(key="screen_intro_download"):
        st.caption("Your document has been generated and is ready to download.")
    st.markdown('<hr class="compact-divider" />', unsafe_allow_html=True)

    st.markdown(
        """
        <div style="text-align:center; padding: 0.5rem 0 1.5rem;">
            <div class="success-circle">&#10003;</div>
            <p style="font-weight:600; font-size:16px; margin:0 0 4px; color: var(--text-color);">
                Document ready
            </p>
            <p style="font-size:13px; color:var(--secondary-text-color); margin:0;">
                Your document has been generated from the confirmed fields.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="file-card success">
            <div class="file-meta-row">
                <div class="file-check-icon">&#10003;</div>
                <div class="file-text-col">
                    <span class="file-name-text">{MOCK_OUTPUT_NAME}</span>
                    <span class="file-sub-text">DOCX file &nbsp;\u2022&nbsp; 486 KB</span>
                </div>
            </div>
            <span class="status-badge status-ready">Ready</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.download_button(
        "Download document",
        data=b"Mock document content - no real .docx generated in this UI-only demo.",
        file_name=MOCK_OUTPUT_NAME,
        type="primary",
        use_container_width=True,
    )

    st.write("")
    col1, col2 = st.columns(2)
    with col1:
        st.button("\u2190 Back to review", use_container_width=True, on_click=go_to, args=("review",))
    with col2:
        st.button("Start new document", use_container_width=True, on_click=reset_flow)