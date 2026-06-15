"""Shared helpers for the Streamlit pages (Process + Evaluation).

Only the four sample documents (those present in data/ground_truth.json) are in scope; any other
upload is rejected without extraction. The scoring/report helpers are reused from eval/ so no
matching logic is duplicated here.

Importing this module also wires src/ and eval/ onto sys.path, so both pages just `import ui_common`.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).parent
for _sub in ("src", "eval"):
    p = str(_ROOT / _sub)
    if p not in sys.path:
        sys.path.insert(0, p)

import config  # noqa: E402
from agents.classifier import classify  # noqa: E402
from evaluate import _summary_score, _tag_jaccard, _walk  # noqa: E402
from graph import run_pipeline  # noqa: E402
from parsing import parse_document  # noqa: E402
from report import _write_report  # noqa: E402

# The four document types this pipeline supports; anything classified "Other" is unsupported.
SUPPORTED_TYPES = ("Vendor Contract", "Support Ticket", "Statement of Work", "Invoice")


def load_ground_truth() -> dict:
    return json.loads(config.GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


def is_in_scope(name: str, ground_truth: dict) -> bool:
    return name in ground_truth


def _write_temp(uploaded) -> str:
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getvalue())
        return tmp.name


# ── Page 1 (product): classify first, extract only if a supported type ─────────────────────────
def process_for_product(uploaded) -> tuple[str, dict | None]:
    """Parse + classify an upload. If the result is a confident supported type, run the full
    pipeline and return (type, data); otherwise ("Other", or below the confidence threshold) stop
    early and return (type, None) — no extraction. Mirrors the backend's route_after_classify.
    GT-independent: works on any uploaded file."""
    tmp_path = None
    try:
        tmp_path = _write_temp(uploaded)
        c = classify(parse_document(tmp_path)).parsed
        if c.document_type not in SUPPORTED_TYPES or c.confidence < config.CLASSIFY_CONFIDENCE_THRESHOLD:
            return c.document_type, None
        result = run_pipeline(tmp_path)
        result.source_file = uploaded.name      # show the real name, not the temp path
        return c.document_type, result.model_dump()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def unsupported_type_message(name: str, doc_type: str) -> None:
    if doc_type in SUPPORTED_TYPES:             # supported type, but low confidence -> stopped
        st.error(
            f"🚫 **Low confidence** — `{name}` was classified as **{doc_type}** but below the "
            "confidence threshold, so extraction was stopped."
        )
    else:
        st.error(
            f"🚫 **Unsupported document** — `{name}` was classified as **{doc_type}**, which this "
            "pipeline does not handle. Extraction was stopped. Supported types: "
            + ", ".join(SUPPORTED_TYPES) + "."
        )


# ── Page 2 (evaluation): only the sample files with ground truth ───────────────────────────────
def run_on_upload(uploaded) -> dict:
    """Run the full pipeline on an uploaded file and return its model_dump dict."""
    tmp_path = None
    try:
        tmp_path = _write_temp(uploaded)
        result = run_pipeline(tmp_path)
        result.source_file = uploaded.name
        return result.model_dump()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def out_of_scope_message(name: str, ground_truth: dict) -> None:
    st.error(
        f"🚫 **Out of scope** — `{name}` is not one of the known sample documents, so there is no "
        "ground truth to evaluate against. It was not processed."
    )
    st.caption("Recognised samples: " + ", ".join(f"`{n}`" for n in ground_truth))


# ── product rendering (no scoring) ───────────────────────────────────────────────────────────
def render_structured_output(data: dict) -> None:
    """Page 1: classification, tags, extracted fields, summary — the deliverable, no accuracy."""
    c = data["classification"]
    st.metric("Type", c["document_type"])
    st.caption(f"Classifier confidence: {c['confidence']:.0%}")

    st.markdown("**Tags**")
    st.write(" ".join(f"`{t}`" for t in data["tags"]))

    st.markdown("**Extracted fields**")
    st.json(data["extracted_fields"])

    st.markdown("**Summary**")
    st.write(data["summary"])


# ── evaluation scoring (reuse eval/ functions) ───────────────────────────────────────────────
def compute_scores(gt: dict, data: dict) -> dict:
    """Score one prediction against ground truth using the eval functions (no new logic)."""
    pred_type = data["classification"]["document_type"]
    fm, ft = _walk(gt["extracted_fields"], data["extracted_fields"], "", "", [])
    ti, tu = _tag_jaccard(gt["tags"], data["tags"])
    sscore, lex, sem = _summary_score(gt["summary"], data["summary"])
    return {
        "pred_type": pred_type,
        "class_ok": pred_type == gt["document_type"],
        "expected_type": gt["document_type"],
        "field_m": fm, "field_t": ft,
        "tag_i": ti, "tag_u": tu,
        "summary": sscore, "lex": lex, "sem": sem,
    }


def render_eval_metrics(sc: dict) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Classification", "✓ correct" if sc["class_ok"] else "✗ wrong",
                delta=None if sc["class_ok"] else f"expected {sc['expected_type']}",
                delta_color="off" if sc["class_ok"] else "inverse")
    col2.metric("Field accuracy", f"{sc['field_m']}/{sc['field_t']}",
                f"{sc['field_m'] / sc['field_t']:.0%}" if sc["field_t"] else "—")
    col3.metric("Tag Jaccard", f"{sc['tag_i']}/{sc['tag_u']}",
                f"{sc['tag_i'] / sc['tag_u']:.0%}" if sc["tag_u"] else "—")
    col4.metric("Summary score", f"{sc['summary']:.2f}",
                f"lex {sc['lex']:.0f} · sem {sc['sem']:.2f}" if sc["sem"] is not None
                else "lexical-only")


def generate_report(name: str, gt: dict, data: dict) -> tuple[Path, str]:
    """Generate the per-document eval report .md from this run and return (path, markdown)."""
    path = _write_report(name, gt, data)
    return path, path.read_text(encoding="utf-8")
