from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.audit import log_outcome, recent_audit_entries
from src.extraction import extract_enquiry
from src.llm import extract_with_openai
from src.models import EnquiryAnalysis, HumanReviewStatus
from src.responses import generate_draft_response
from src.retrieval import CatalogueRetriever, attach_suggestions


BASE_DIR = Path(__file__).resolve().parent
CATALOGUE_PATH = BASE_DIR / "data" / "sample_catalogue.csv"
EXAMPLES_PATH = BASE_DIR / "data" / "demo_enquiries.json"
load_dotenv(BASE_DIR / ".env")


def audit_database_path() -> Path:
    configured = os.getenv("AUDIT_DB_PATH", "").strip()
    return Path(configured) if configured else BASE_DIR / "data" / "audit.db"


st.set_page_config(
    page_title="Bathroom Spare Parts | Enquiry Triage",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
    :root {
        --ink: #153044;
        --muted: #526875;
        --teal: #0a6c60;
        --teal-dark: #07564d;
        --teal-soft: #e7f3f0;
        --navy: #123047;
        --line: #d9e3e7;
        --surface: #ffffff;
        --canvas: #f4f7f8;
        --amber: #9a5b00;
        --amber-soft: #fff4d9;
        --red: #9b2c2c;
        --red-soft: #fff0ef;
    }
    .stApp { background: var(--canvas); }
    .main .block-container {
        max-width: 1180px;
        padding-top: 1.4rem;
        padding-bottom: 4rem;
    }
    h1, h2, h3 { color: var(--ink); letter-spacing: -0.02em; }
    p, li, label, [data-testid="stMarkdownContainer"] { line-height: 1.55; }
    .app-header {
        background: linear-gradient(135deg, #123047 0%, #0b5f59 100%);
        border-radius: 18px;
        padding: 26px 30px;
        margin-bottom: 22px;
        box-shadow: 0 10px 28px rgba(18, 48, 71, 0.14);
    }
    .app-header .eyebrow {
        color: #bfe4dc;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .app-header h1 { color: #ffffff; font-size: clamp(1.75rem, 4vw, 2.55rem); margin: 0 0 8px; }
    .app-header p { color: #e4f0f2; max-width: 760px; margin: 0; font-size: 1rem; }
    .mode-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 8px 20px;
        padding: 12px 16px;
        margin: -8px 0 22px;
        border: 1px solid var(--line);
        border-radius: 12px;
        background: rgba(255,255,255,0.76);
        color: var(--muted);
        font-size: 0.9rem;
    }
    .mode-strip strong { color: var(--ink); }
    .section-kicker {
        color: var(--teal-dark);
        font-weight: 750;
        font-size: 0.78rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 2px;
    }
    .status-banner {
        border-radius: 14px;
        padding: 14px 16px;
        border: 1px solid;
        margin: 8px 0 18px;
    }
    .status-banner strong { display: block; margin-bottom: 2px; }
    .status-ready { background: var(--teal-soft); border-color: #9dcfc4; color: #064c43; }
    .status-review { background: var(--amber-soft); border-color: #e5bd69; color: #704100; }
    .confidence-note {
        padding: 12px 14px;
        background: #eef3f5;
        border-left: 4px solid var(--navy);
        border-radius: 8px;
        color: var(--ink);
        margin: 10px 0 18px;
    }
    div[data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--line);
        padding: 16px;
        border-radius: 14px;
        min-height: 116px;
    }
    div[data-testid="stMetricLabel"] { color: var(--muted); }
    div[data-testid="stMetricValue"] { color: var(--ink); font-variant-numeric: tabular-nums; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--surface);
        border-color: var(--line) !important;
        border-radius: 14px;
    }
    .field-label { color: var(--muted); font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }
    .field-value { color: var(--ink); font-size: 1rem; margin: 2px 0 14px; }
    .evidence-item { margin-bottom: 5px; color: var(--ink); }
    .stButton > button, .stDownloadButton > button, .stLinkButton > a {
        min-height: 44px;
        border-radius: 10px;
        font-weight: 700;
    }
    .stButton > button[kind="primary"] {
        background: var(--teal);
        border-color: var(--teal);
    }
    .stButton > button[kind="primary"]:hover {
        background: var(--teal-dark);
        border-color: var(--teal-dark);
    }
    textarea, input, [data-baseweb="select"] > div { border-radius: 10px !important; }
    textarea:focus, input:focus, button:focus-visible, a:focus-visible {
        outline: 3px solid rgba(10, 108, 96, 0.28) !important;
        outline-offset: 2px;
    }
    [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 8px; }
    [data-testid="stTabs"] button[role="tab"] { min-height: 44px; }
    .prototype-footer {
        margin-top: 26px;
        padding-top: 16px;
        border-top: 1px solid var(--line);
        color: var(--muted);
        font-size: 0.88rem;
    }
    @media (max-width: 700px) {
        .main .block-container { padding: 0.75rem 1rem 3rem; }
        .app-header { padding: 22px 20px; border-radius: 14px; }
        .app-header h1 { font-size: 1.8rem; }
    }
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { scroll-behavior: auto !important; transition: none !important; animation: none !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_retriever() -> CatalogueRetriever:
    return CatalogueRetriever(CATALOGUE_PATH)


@st.cache_data
def load_examples() -> list[dict[str, str]]:
    return json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))


def fixed_html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def render_header() -> None:
    fixed_html(
        """
        <header class="app-header">
            <div class="eyebrow">Staff decision support prototype</div>
            <h1>Enquiry Triage Assistant</h1>
            <p>Turn an unstructured customer message into a structured, evidence-led recommendation and a draft reply for staff approval.</p>
        </header>
        """
    )
    mode = "OpenAI-assisted extraction available" if os.getenv("OPENAI_API_KEY") else "Deterministic demo mode"
    fixed_html(
        f"""
        <div class="mode-strip">
            <span><strong>Mode:</strong> {mode}</span>
            <span><strong>Catalogue:</strong> 40 fictional records</span>
            <span><strong>Safety:</strong> Staff approval always required</span>
        </div>
        """
    )


def render_field(label: str, value: object) -> None:
    st.markdown(f"**{label}**")
    if isinstance(value, list):
        st.write(", ".join(str(item) for item in value) if value else "Not supplied")
    else:
        st.write(value if value not in (None, "") else "Not supplied")


def render_status(analysis: EnquiryAnalysis) -> None:
    needs_review = analysis.human_review_status == HumanReviewStatus.HUMAN_REVIEW_REQUIRED
    css_class = "status-review" if needs_review else "status-ready"
    detail = (
        "Low confidence or missing evidence means the result must be escalated before a response is sent."
        if needs_review
        else "Enough information is present for staff to review the recommendation and draft response."
    )
    fixed_html(
        f'<div class="status-banner {css_class}"><strong>{analysis.human_review_status.value}</strong>{detail}</div>'
    )


def run_analysis(message: str, uploaded_photo: object | None, use_openai: bool) -> None:
    retriever = get_retriever()
    mode_used = "Deterministic demo"
    if use_openai:
        try:
            analysis = extract_with_openai(message, bool(uploaded_photo), retriever.brands)
            mode_used = "OpenAI-assisted"
        except Exception as exc:  # API failure must never break the demonstration path.
            st.warning(f"OpenAI extraction was unavailable, so deterministic mode was used. Details: {exc}")
            analysis = extract_enquiry(message, bool(uploaded_photo), retriever.brands)
    else:
        analysis = extract_enquiry(message, bool(uploaded_photo), retriever.brands)

    suggestions = retriever.search(analysis, message)
    analysis = attach_suggestions(analysis, suggestions)
    st.session_state.analysis_result = analysis
    st.session_state.original_message = message
    st.session_state.response_draft = generate_draft_response(analysis)
    st.session_state.mode_used = mode_used


def render_matches(analysis: EnquiryAnalysis) -> None:
    if not analysis.suggested_products:
        st.warning(
            "No catalogue suggestion cleared the evidence threshold. Ask the recommended follow-up question or escalate for manual review."
        )
        return

    st.caption("Suggestions are possible matches only. Confidence is evidence strength, not confirmation of compatibility.")
    for rank, product in enumerate(analysis.suggested_products, start=1):
        with st.container(border=True):
            left, right = st.columns([3, 1])
            with left:
                st.markdown(f"### {rank}. {product.product_name}")
                st.write(f"{product.brand} · {product.category} · SKU {product.sku}")
            with right:
                st.metric("Match confidence", f"{product.confidence_score:.0%}")
            st.progress(product.confidence_score)
            st.markdown("**Evidence used**")
            for item in product.evidence:
                st.markdown(f"- {item}")
            st.caption(f"Availability: {product.stock_status}. This is not live stock information.")


def render_decision(analysis: EnquiryAnalysis) -> None:
    st.markdown("### Draft response")
    st.caption("Edit freely. Nothing is sent automatically.")
    draft = st.text_area(
        "Customer response draft",
        value=st.session_state.response_draft,
        height=280,
        key=f"draft_{analysis.enquiry_id}",
    )
    st.markdown("### Record staff decision")
    decision = st.selectbox(
        "Decision",
        ["Approve draft", "Edit and approve", "Reject recommendation", "Escalate for specialist review"],
    )
    sku_options = ["No product selected"] + [item.sku for item in analysis.suggested_products]
    selected = st.selectbox("Selected catalogue SKU", sku_options)
    notes = st.text_area(
        "Staff notes",
        placeholder="Briefly record what was checked or why the recommendation was changed.",
        height=100,
    )
    if st.button("Save decision to audit log", type="primary", width="stretch"):
        status_map = {
            "Approve draft": HumanReviewStatus.APPROVED,
            "Edit and approve": HumanReviewStatus.EDITED_AND_APPROVED,
            "Reject recommendation": HumanReviewStatus.REJECTED,
            "Escalate for specialist review": HumanReviewStatus.ESCALATED,
        }
        reviewed = analysis.model_copy(update={"human_review_status": status_map[decision]})
        record_id = log_outcome(
            audit_database_path(),
            reviewed,
            st.session_state.original_message,
            draft,
            decision,
            None if selected == "No product selected" else selected,
            notes,
        )
        st.session_state.analysis_result = reviewed
        st.session_state.response_draft = draft
        st.success(f"Decision saved as audit record {record_id}. No customer message was sent.")


def render_results(analysis: EnquiryAnalysis) -> None:
    st.divider()
    fixed_html('<div class="section-kicker">Analysis complete</div>')
    st.subheader(f"Enquiry {analysis.enquiry_id}")
    render_status(analysis)
    first, second, third, fourth = st.columns(4)
    first.metric("Category", analysis.enquiry_category.value)
    second.metric("Completeness", f"{analysis.information_completeness_score}%")
    third.metric("Confidence", f"{analysis.confidence_score:.0%}")
    fourth.metric("Candidates", len(analysis.suggested_products))

    detail_tab, matches_tab, response_tab, json_tab = st.tabs(
        ["Extracted details", "Catalogue matches", "Draft and decision", "Validated JSON"]
    )
    with detail_tab:
        left, right = st.columns(2)
        with left:
            render_field("Product category", analysis.product_category.value)
            render_field("Brand", analysis.brand)
            render_field("Model or range", analysis.product_or_model_name)
            render_field("Part code", analysis.part_code)
            render_field("Markings", analysis.markings)
        with right:
            render_field("Reported problem", analysis.symptoms_or_reported_problem)
            render_field("Measurements", analysis.measurements)
            render_field("Order number", analysis.order_number)
            render_field("Photograph attached", "Yes" if analysis.photograph_attached else "No")
            render_field("Extraction mode", st.session_state.get("mode_used", "Deterministic demo"))

        st.markdown("### Completeness check")
        st.progress(analysis.information_completeness_score / 100)
        if analysis.missing_information:
            st.markdown("**Missing or recommended evidence**")
            for item in analysis.missing_information:
                st.markdown(f"- {item}")
        fixed_html(f'<div class="confidence-note"><strong>Best next question</strong><br>{analysis.recommended_next_question}</div>')

    with matches_tab:
        render_matches(analysis)
    with response_tab:
        render_decision(analysis)
    with json_tab:
        st.caption("Pydantic-validated output used by retrieval, response drafting and audit logging.")
        st.json(analysis.as_json_dict(), expanded=True)


render_header()
workspace_tab, audit_tab, notes_tab = st.tabs(["Triage workspace", "Audit log", "Prototype notes"])

with workspace_tab:
    fixed_html('<div class="section-kicker">Step 1 · Review the enquiry</div>')
    st.subheader("Paste a fictional customer message")
    input_column, example_column = st.columns([2, 1], gap="large")
    examples = load_examples()

    with example_column:
        with st.container(border=True):
            st.markdown("### Demonstration scenarios")
            selected_example = st.selectbox(
                "Choose an example",
                examples,
                format_func=lambda item: item["title"],
                label_visibility="visible",
            )
            if st.button("Load example", width="stretch"):
                st.session_state.enquiry_text = selected_example["message"]
                st.session_state.pop("analysis_result", None)
                st.rerun()
            st.caption("All examples are fictional and designed to exercise a different safety path.")
        with st.container(border=True):
            st.markdown("### Privacy guardrail")
            st.write("Do not paste real names, email addresses, phone numbers or payment information into this prototype.")

    with input_column:
        message = st.text_area(
            "Customer enquiry",
            key="enquiry_text",
            height=230,
            placeholder="Example: I need a replacement cartridge for an AquaVale Metro tap. It drips and I have attached a photo…",
            help="Use fictional enquiries only. The app redacts common email and phone patterns before audit storage.",
        )
        uploaded_photo = st.file_uploader(
            "Sample photograph (optional)",
            type=["jpg", "jpeg", "png", "webp"],
            help="The prototype records that a photo is present; it does not perform image recognition.",
        )
        if uploaded_photo:
            st.image(uploaded_photo, caption="Uploaded sample image", width=240)
            st.caption("Image content is not analysed or saved to the audit log in this prototype.")

        api_available = bool(os.getenv("OPENAI_API_KEY"))
        use_openai = st.checkbox(
            "Use OpenAI-assisted extraction",
            value=False,
            disabled=not api_available,
            help=(
                "The enquiry is redacted for common email and phone patterns before it is sent."
                if api_available
                else "Set OPENAI_API_KEY in a local .env file to enable this optional mode."
            ),
        )
        if st.button("Analyse enquiry", type="primary", width="stretch"):
            if len(message.strip()) < 15:
                st.error("Enter a more complete fictional customer message before analysing it.")
            else:
                with st.spinner("Extracting details and checking the sample catalogue…"):
                    run_analysis(message.strip(), uploaded_photo, use_openai)

    if "analysis_result" in st.session_state:
        render_results(st.session_state.analysis_result)

with audit_tab:
    fixed_html('<div class="section-kicker">Human oversight</div>')
    st.subheader("Decision audit log")
    st.write("Only explicit staff decisions are stored. Common email and phone patterns are redacted before storage.")
    audit_entries = recent_audit_entries(audit_database_path())
    if audit_entries.empty:
        st.info("No decisions have been recorded yet. Analyse an enquiry and save a decision to create the first audit entry.")
    else:
        st.dataframe(audit_entries, width="stretch", hide_index=True)
        st.download_button(
            "Download audit summary as CSV",
            audit_entries.to_csv(index=False).encode("utf-8"),
            file_name="enquiry_audit_summary.csv",
            mime="text/csv",
        )

with notes_tab:
    fixed_html('<div class="section-kicker">Scope and safeguards</div>')
    st.subheader("What this prototype does")
    st.markdown(
        """
        - Extracts structured fields from a free-text enquiry and validates them with Pydantic.
        - Scores information completeness using category-specific evidence requirements.
        - Searches only a 40-record fictional catalogue and returns no more than three candidates.
        - Shows the exact evidence used for each candidate and escalates weak results.
        - Drafts a response for editing and requires a recorded staff decision.
        """
    )
    st.subheader("What it deliberately does not do")
    st.markdown(
        """
        - It does not connect to stock, customer, order, supplier or email systems.
        - It does not confirm compatibility or automatically contact a customer.
        - It does not identify parts from image pixels; an upload only counts as supplied evidence.
        - It does not make binding returns, installation or warranty decisions.
        """
    )
    st.info("Catalogue names, SKUs, links and availability labels are fictional demonstration data.")

fixed_html(
    '<div class="prototype-footer">Prototype for demonstration purposes · Fictional enquiries and catalogue data only · Human review required before any action</div>'
)
