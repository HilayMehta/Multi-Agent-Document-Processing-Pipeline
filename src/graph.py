"""LangGraph wiring: parse → classify → [extract → (tag ∥ summarize) → validate → retry].

After classify, a confident supported type proceeds to extraction; "Other" or a low-confidence
result stops the run there (no extraction/tags/summary) — mirroring the product UI's classify gate.
The validator routes failures back to the single failing stage (never the classifier), bounded by
MAX_RETRIES_PER_STAGE. Routing by document_type is code (config_for / route_after_classify), not LLM.
"""

import operator
import time
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

import config
from agents.classifier import classify
from agents.extractor import Extractor, config_for
from agents.summarizer import summarize
from agents.tagger import tag
from parsing import parse_document
from registry import EXTRACTORS
from schemas.common import Classification, FinalOutput, PipelineMeta
from validation import validate

RETRYABLE_STAGES = ("extract", "tag", "summarize")


def _merge_dict(a: dict, b: dict) -> dict:
    merged = dict(a or {})
    merged.update(b or {})
    return merged


class PipelineState(TypedDict):
    source_path: str
    raw_text: str
    classification: Classification | None
    extracted_fields: dict | None
    tags: list[str] | None
    summary: str | None
    validation_errors: dict[str, list[str]]
    retry_counts: Annotated[dict[str, int], _merge_dict]   # concurrent writers -> merge
    model_calls: Annotated[int, operator.add]              # concurrent writers -> sum
    errors_seen: Annotated[list[str], operator.add]        # accumulated across retries


# ── Thin wrappers so nodes are tiny and easily mocked in tests ──────────────────
def _classify(text: str) -> Classification:
    return classify(text).parsed


def _extract_fields(cfg, text: str, prior: list[str] | None) -> dict:
    return Extractor(cfg).run(text, prior_errors=prior).parsed.model_dump()


def _tag(doc_type: str, text: str, fields: dict, prior: list[str] | None) -> list[str]:
    return tag(doc_type, text, fields, prior_errors=prior).parsed.tags


def _summarize(doc_type: str, text: str, fields: dict, prior: list[str] | None) -> str:
    return summarize(doc_type, text, fields, prior_errors=prior).parsed.summary


# ── Nodes ───────────────────────────────────────────────────────────────────────
def parse_node(state: PipelineState) -> dict:
    return {"raw_text": parse_document(state["source_path"])}


def classify_node(state: PipelineState) -> dict:
    return {"classification": _classify(state["raw_text"]), "model_calls": 1}


def extract_node(state: PipelineState) -> dict:
    c = state["classification"]
    cfg = config_for(c.document_type)                         # code-level routing
    prior = state["validation_errors"].get("extract")
    counts = {"extract": state["retry_counts"].get("extract", 0) + 1} if prior else {}
    fields = _extract_fields(cfg, state["raw_text"], prior)
    return {"extracted_fields": fields, "model_calls": 1, "retry_counts": counts}


def tag_node(state: PipelineState) -> dict:
    c = state["classification"]
    prior = state["validation_errors"].get("tag")
    counts = {"tag": state["retry_counts"].get("tag", 0) + 1} if prior else {}
    tags = _tag(c.document_type, state["raw_text"], state["extracted_fields"], prior)
    return {"tags": tags, "model_calls": 1, "retry_counts": counts}


def summarize_node(state: PipelineState) -> dict:
    c = state["classification"]
    prior = state["validation_errors"].get("summarize")
    counts = {"summarize": state["retry_counts"].get("summarize", 0) + 1} if prior else {}
    summary = _summarize(c.document_type, state["raw_text"], state["extracted_fields"], prior)
    return {"summary": summary, "model_calls": 1, "retry_counts": counts}


def validate_node(state: PipelineState) -> dict:
    c = state["classification"]
    errors = validate(c.document_type, state["extracted_fields"] or {},
                      state["tags"], state["summary"])
    seen = [f"{stage}: {msg}" for stage, msgs in errors.items() for msg in msgs]
    return {"validation_errors": errors, "errors_seen": seen}


def route_after_classify(state: PipelineState) -> str:
    """Extract only a supported type the classifier is confident about; otherwise stop (END) right
    after classification — no extraction/tags/summary — for "Other" or low-confidence results."""
    c = state["classification"]
    confident_supported = (c.document_type in EXTRACTORS
                           and c.confidence >= config.CLASSIFY_CONFIDENCE_THRESHOLD)
    return "extract" if confident_supported else END


def route_after_validate(state: PipelineState) -> str:
    """Send the run back to the single failing stage, or END when clean/out of budget."""
    errors = state["validation_errors"]
    if not errors:
        return END
    for stage in RETRYABLE_STAGES:
        if stage in errors and state["retry_counts"].get(stage, 0) < config.MAX_RETRIES_PER_STAGE:
            return stage
    return END  # budget exhausted — emit anyway with unresolved errors


def build_graph():
    g = StateGraph(PipelineState)
    for name, fn in [
        ("parse", parse_node), ("classify", classify_node), ("extract", extract_node),
        ("tag", tag_node), ("summarize", summarize_node), ("validate", validate_node),
    ]:
        g.add_node(name, fn)
    g.add_edge(START, "parse")
    g.add_edge("parse", "classify")
    g.add_conditional_edges(              # supported type -> extract; "Other" -> stop
        "classify", route_after_classify, {"extract": "extract", END: END},
    )
    g.add_edge("extract", "tag")          # fan-out
    g.add_edge("extract", "summarize")    # fan-out
    g.add_edge("tag", "validate")         # fan-in
    g.add_edge("summarize", "validate")   # fan-in
    g.add_conditional_edges(
        "validate", route_after_validate,
        {"extract": "extract", "tag": "tag", "summarize": "summarize", END: END},
    )
    return g.compile()


COMPILED_GRAPH = build_graph()


def run_pipeline(source_path: str) -> FinalOutput:
    """Run the full pipeline on one document and assemble the output envelope."""
    initial: PipelineState = {
        "source_path": source_path, "raw_text": "", "classification": None,
        "extracted_fields": None, "tags": None, "summary": None,
        "validation_errors": {}, "retry_counts": {}, "model_calls": 0, "errors_seen": [],
    }
    start = time.perf_counter()
    final = COMPILED_GRAPH.invoke(initial)
    return _assemble(source_path, final, time.perf_counter() - start)


def _assemble(source_path: str, final: dict, duration: float) -> FinalOutput:
    val_errors = final.get("validation_errors") or {}
    unresolved = [f"{s}: {m}" for s, msgs in val_errors.items() for m in msgs]
    seen = list(dict.fromkeys(final.get("errors_seen") or []))
    fixed = [e for e in seen if e not in unresolved]
    retries = {"extract": 0, "tag": 0, "summarize": 0}
    retries.update(final.get("retry_counts") or {})
    meta = PipelineMeta(
        model_calls=final.get("model_calls", 0),
        retries=retries,
        validation_errors_fixed=fixed,
        validation_errors_unresolved=unresolved,
        duration_seconds=round(duration, 2),
    )
    return FinalOutput(
        source_file=Path(source_path).name,
        classification=final["classification"],
        tags=final.get("tags") or [],
        extracted_fields=final.get("extracted_fields") or {},
        summary=final.get("summary") or "",
        pipeline_meta=meta,
    )
