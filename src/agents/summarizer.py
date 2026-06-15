"""Summarizer agent: a 2-3 sentence plain-language summary grounded in extracted fields."""

import json

import config
from llm import StructuredResponse, call_structured
from schemas.common import Summary

SUMMARIZER_SYSTEM_PROMPT = """\
You write a 2-3 sentence plain-language summary of a business document.

- Lead with what the document IS and the parties involved, then the key figures, dates, and
  outcome.
- Ground every fact in the provided extracted fields and document text — do not introduce
  numbers, names, or dates that are not present. Monetary amounts you mention must match the
  extracted fields exactly (including currency symbol and digit grouping).
- Plain, neutral language. No marketing tone, no bullet points. 2 to 3 sentences.
"""


def summarize(document_type: str, raw_text: str, extracted_fields: dict,
              prior_errors: list[str] | None = None) -> StructuredResponse:
    """Produce a grounded 2-3 sentence summary of the document."""
    user_text = _build_user_text(document_type, raw_text, extracted_fields, prior_errors)
    return call_structured(
        stage="summarize",
        model=config.MODEL_SUMMARY,
        system=SUMMARIZER_SYSTEM_PROMPT,
        user_text=user_text,
        schema=Summary,
        max_tokens=config.MAX_TOKENS_SUMMARY,
    )


def _build_user_text(document_type: str, raw_text: str, extracted_fields: dict,
                     prior_errors: list[str] | None) -> str:
    parts = [
        f"Document type: {document_type}",
        f"Extracted fields:\n{json.dumps(extracted_fields, ensure_ascii=False)}",
        f"Full document text:\n{raw_text}",
    ]
    if prior_errors:
        parts.append(
            "Your previous summary failed these checks:\n"
            + "\n".join(f"- {e}" for e in prior_errors)
            + "\nProduce a corrected summary."
        )
    return "\n\n".join(parts)
