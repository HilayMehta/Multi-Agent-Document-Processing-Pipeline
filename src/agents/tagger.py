"""Tagger agent: 3-7 lowercase, hyphen-separated, content-grounded semantic tags."""

import json

import config
from llm import StructuredResponse, call_structured
from schemas.common import TagSet

TAGGER_SYSTEM_PROMPT = """\
You assign 3 to 7 semantic tags to a business document.

Tags are short, canonical retrieval labels: lowercase, hyphen-separated. Prefer the standard
short term or acronym for a concept over a longer descriptive phrase (for example the system
category or its acronym rather than a product name, the business model rather than a sentence).

Cover the facets that genuinely apply, choosing a few from across these groups:
- business or engagement model (for example saas, b2b, subscription, managed-service),
- industry or domain (for example fintech, ai, ocr, cloud-infrastructure),
- key commercial or contractual terms (for example net-30, gst, change-order, auto-renewal),
- party structure (for example multi-party, bilateral),
- status, priority, or severity where present (for example resolved, p1, production-down).

Rules:
- 3 to 7 tags. Use only lowercase letters, digits, and single hyphens between words: no dots,
  percent signs, slashes, spaces, or other punctuation. Each tag must match
  ^[a-z0-9]+(-[a-z0-9]+)*$.
- Do not encode decimals, percentages, or version numbers in a tag (use "uptime-sla", not
  "sla-99.9").
- Each tag must be justified by the document: no generic filler like "document" or "business".
- Favour a widely recognized category term or acronym over a document-specific proper noun when
  both fit (for example "erp" rather than "oracle-financials").
"""


def tag(document_type: str, raw_text: str, extracted_fields: dict,
        prior_errors: list[str] | None = None) -> StructuredResponse:
    """Generate semantic tags grounded in the document and its extracted fields."""
    user_text = _build_user_text(document_type, raw_text, extracted_fields, prior_errors)
    return call_structured(
        stage="tag",
        model=config.MODEL_TAG,
        system=TAGGER_SYSTEM_PROMPT,
        user_text=user_text,
        schema=TagSet,
        max_tokens=config.MAX_TOKENS_TAG,
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
            "Your previous tags failed these checks:\n"
            + "\n".join(f"- {e}" for e in prior_errors)
            + "\nProduce corrected tags."
        )
    return "\n\n".join(parts)
