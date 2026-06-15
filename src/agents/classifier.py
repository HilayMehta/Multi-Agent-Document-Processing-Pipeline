"""Classifier agent: document type + confidence + signals from the first 2,000 chars."""

import config
from llm import StructuredResponse, call_structured
from schemas.common import Classification

CLASSIFIER_SYSTEM_PROMPT = """\
You classify business documents into exactly one type:

- "Vendor Contract": a signed agreement establishing service terms between parties — fees,
  liability, termination, governing law.
- "Support Ticket": an incident or issue report — ticket ID, priority, status,
  affected system, resolution notes.
- "Statement of Work": defines FUTURE work to be performed — scope, deliverables,
  milestones, acceptance criteria.
- "Invoice": demands PAYMENT for completed work — invoice number, line items with amounts,
  total due, payment due date.
- "Other": none of the above fits.

Critical boundary: an invoice often references a Statement of Work number — a document that
merely MENTIONS an SOW is not a Statement of Work. Classify by what the document DOES
(demand payment vs define future work), not by what it cites.

Report 1-3 short verbatim signals from the document that justify your choice, and a
calibrated confidence between 0 and 1.
"""


def classify(raw_text: str) -> StructuredResponse:
    """Classify a document from its opening window of text."""
    return call_structured(
        stage="classify",
        model=config.MODEL_CLASSIFY,
        system=CLASSIFIER_SYSTEM_PROMPT,
        user_text=raw_text[: config.CLASSIFY_WINDOW],
        schema=Classification,
        max_tokens=config.MAX_TOKENS_CLASSIFY,
    )
