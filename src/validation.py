"""Deterministic validation of pipeline outputs. No LLM calls.

Each check returns errors keyed by the STAGE that should be retried, so the graph can
re-invoke only the failing agent (never the classifier).
"""

import re
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TAG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MONEY_RE = re.compile(r"(?:₹|\$|Rs\.?)\s?[\d,]+(?:\.\d+)?")
RUPEE_TOLERANCE = Decimal("1")  # ±1 rupee for arithmetic rounding

# Abbreviations that are NEVER sentence-final: their period is always masked.
_ABBREV_NEVER_FINAL = re.compile(r"\b(?i:pvt|mr|mrs|ms|dr|st|no|vs|jr|sr|etc)\.")
# Company suffixes that CAN end a sentence: mask the period only when what follows is a
# lowercase letter, digit, or comma (clearly mid-sentence). A following capital is a real
# boundary and is left intact. The lookahead is case-sensitive (flag scoped to the group).
_ABBREV_MAYBE_FINAL = re.compile(r"\b(?i:ltd|inc|corp|co|llc|plc)\.(?=\s*[,a-z0-9])")


def _count_sentences(text: str) -> int:
    """Count sentences, treating company-name abbreviations (Pvt. Ltd., Inc.) correctly."""
    protected = _ABBREV_NEVER_FINAL.sub(lambda m: m.group(0)[:-1], text)
    protected = _ABBREV_MAYBE_FINAL.sub(lambda m: m.group(0)[:-1], protected)
    return len([s for s in re.split(r"(?<=[.!?])\s+", protected.strip()) if s.strip()])


def parse_inr(value: str | None) -> Decimal | None:
    """Parse an amount string into a Decimal, ignoring currency symbols and grouping.

    Indian grouping is irrelevant once separators are stripped: "₹14,16,000" -> 1416000,
    "₹2,16,000" -> 216000. Returns None when there is no parseable number.
    """
    if not value:
        return None
    digits = re.sub(r"[^\d.]", "", value)
    if not digits or digits == ".":
        return None
    try:
        return Decimal(digits)
    except InvalidOperation:
        return None


def parse_percent(value: str | None) -> Decimal | None:
    """Parse "18%" -> Decimal('0.18'). Returns None if unparseable."""
    num = parse_inr(value)
    return num / 100 if num is not None else None


def validate_tags(tags: list[str] | None) -> list[str]:
    """Tag contract: 3-7, regex per tag, no duplicates."""
    errors: list[str] = []
    if not tags:
        return ["tags: missing"]
    if not 3 <= len(tags) <= 7:
        errors.append(f"tags: count {len(tags)} not in 3-7")
    for t in tags:
        if not TAG_RE.match(t):
            errors.append(f"tags: '{t}' must be lowercase hyphen-separated")
    if len(set(tags)) != len(tags):
        errors.append("tags: duplicates present")
    return errors


def validate_summary(summary: str | None) -> list[str]:
    """Summary must be non-empty and 2-3 sentences."""
    if not summary or not summary.strip():
        return ["summary: empty"]
    count = _count_sentences(summary)
    if not 2 <= count <= 3:
        return [f"summary: {count} sentences, expected 2-3"]
    return []


def validate_dates(fields: dict) -> list[str]:
    """Every value under a *_date / date_* key must be ISO YYYY-MM-DD or null."""
    errors: list[str] = []

    def walk(node: object, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        else:
            key = path.split(".")[-1].split("[")[0]
            if ("date" in key) and node is not None:
                if not (isinstance(node, str) and ISO_DATE_RE.match(node)):
                    errors.append(f"dates: {path}='{node}' not ISO YYYY-MM-DD")

    walk(fields, "")
    return errors


def validate_invoice_math(fields: dict) -> list[str]:
    """Line items sum to subtotal; subtotal*gst == gst_amount; subtotal+gst == total.

    Also: Net-30 implies due_date == invoice_date + 30 days. All within ±1 rupee.
    """
    errors: list[str] = []
    totals = fields.get("totals") or {}
    subtotal = parse_inr(totals.get("subtotal"))
    gst_amount = parse_inr(totals.get("gst_amount"))
    gst_rate = parse_percent(totals.get("gst_rate"))
    total_due = parse_inr(totals.get("total_due"))

    line_items = fields.get("line_items") or []
    item_amounts = [parse_inr(li.get("amount")) for li in line_items]
    if line_items and all(a is not None for a in item_amounts) and subtotal is not None:
        if abs(sum(item_amounts) - subtotal) > RUPEE_TOLERANCE:
            errors.append(f"invoice: line items {sum(item_amounts)} != subtotal {subtotal}")

    if subtotal is not None and gst_rate is not None and gst_amount is not None:
        if abs(subtotal * gst_rate - gst_amount) > RUPEE_TOLERANCE:
            errors.append(f"invoice: subtotal*gst {subtotal * gst_rate} != gst_amount {gst_amount}")

    if subtotal is not None and gst_amount is not None and total_due is not None:
        if abs(subtotal + gst_amount - total_due) > RUPEE_TOLERANCE:
            errors.append(f"invoice: subtotal+gst {subtotal + gst_amount} != total_due {total_due}")

    errors.extend(_validate_net30(fields))
    return errors


def _validate_net30(fields: dict) -> list[str]:
    terms = (fields.get("payment_terms") or "").lower()
    inv, due = fields.get("invoice_date"), fields.get("due_date")
    if "net-30" not in terms.replace(" ", "-"):
        return []
    if not (isinstance(inv, str) and ISO_DATE_RE.match(inv)
            and isinstance(due, str) and ISO_DATE_RE.match(due)):
        return []
    expected = date.fromisoformat(inv) + timedelta(days=30)
    if date.fromisoformat(due) != expected:
        return [f"invoice: Net-30 due_date {due} != invoice_date+30 ({expected.isoformat()})"]
    return []


def validate_grounding(summary: str | None, fields: dict) -> list[str]:
    """Every monetary amount in the summary must appear in the extracted fields."""
    if not summary:
        return []
    field_blob = _normalize_money(_flatten_text(fields))
    errors: list[str] = []
    for raw_amount in MONEY_RE.findall(summary):
        amount = raw_amount.strip(" ,.;")          # drop trailing punctuation from the match
        if _normalize_money(amount) not in field_blob:
            errors.append(f"grounding: summary amount '{amount}' not in extracted fields")
    return errors


def validate(document_type: str, fields: dict, tags: list[str] | None,
             summary: str | None) -> dict[str, list[str]]:
    """Run all checks; return {stage: [errors]} for the stages that must be retried."""
    by_stage: dict[str, list[str]] = defaultdict(list)
    by_stage["extract"].extend(validate_dates(fields))
    if document_type == "Invoice":
        by_stage["extract"].extend(validate_invoice_math(fields))
    by_stage["tag"].extend(validate_tags(tags))
    by_stage["summarize"].extend(validate_summary(summary))
    by_stage["summarize"].extend(validate_grounding(summary, fields))
    return {stage: errs for stage, errs in by_stage.items() if errs}


def _flatten_text(node: object) -> str:
    if isinstance(node, dict):
        return " ".join(_flatten_text(v) for v in node.values())
    if isinstance(node, list):
        return " ".join(_flatten_text(v) for v in node)
    return str(node) if node is not None else ""


def _normalize_money(text: str) -> str:
    """Lowercase and strip spaces so '₹ 2,16,000' matches '₹2,16,000'."""
    return re.sub(r"\s+", "", text.lower())
