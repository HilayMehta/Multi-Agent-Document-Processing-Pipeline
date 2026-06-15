"""Validation tests: INR parsing, invoice arithmetic, tags, dates, summary, grounding."""

from decimal import Decimal

import pytest

from validation import (
    parse_inr,
    parse_percent,
    validate,
    validate_dates,
    validate_grounding,
    validate_invoice_math,
    validate_summary,
    validate_tags,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("₹14,16,000", Decimal("1416000")),
        ("₹2,16,000", Decimal("216000")),
        ("₹ 2,16,000", Decimal("216000")),
        ("₹40,00,000", Decimal("4000000")),
        ("$120,000", Decimal("120000")),
        ("40 hrs", Decimal("40")),
        (None, None),
        ("", None),
    ],
)
def test_parse_inr(raw, expected):
    assert parse_inr(raw) == expected


def test_parse_percent():
    assert parse_percent("18%") == Decimal("0.18")
    assert parse_percent(None) is None


def _good_invoice() -> dict:
    return {
        "payment_terms": "Net-30",
        "invoice_date": "2024-10-28",
        "due_date": "2024-11-27",
        "line_items": [
            {"amount": "₹10,00,000"},
            {"amount": "₹1,40,000"},
            {"amount": "₹60,000"},
        ],
        "totals": {
            "subtotal": "₹12,00,000",
            "gst_rate": "18%",
            "gst_amount": "₹2,16,000",
            "total_due": "₹14,16,000",
        },
    }


def test_invoice_math_passes_on_correct_invoice():
    assert validate_invoice_math(_good_invoice()) == []


def test_invoice_math_catches_wrong_subtotal():
    bad = _good_invoice()
    bad["totals"]["subtotal"] = "₹11,00,000"
    errors = validate_invoice_math(bad)
    assert any("subtotal" in e for e in errors)


def test_invoice_math_catches_wrong_gst():
    bad = _good_invoice()
    bad["totals"]["gst_amount"] = "₹2,00,000"
    assert any("gst_amount" in e for e in validate_invoice_math(bad))


def test_invoice_math_catches_wrong_total():
    bad = _good_invoice()
    bad["totals"]["total_due"] = "₹15,00,000"
    assert any("total_due" in e for e in validate_invoice_math(bad))


def test_net30_due_date_mismatch():
    bad = _good_invoice()
    bad["due_date"] = "2024-12-15"
    assert any("Net-30" in e for e in validate_invoice_math(bad))


def test_tags_rules():
    assert validate_tags(["net-30", "gst", "saas"]) == []
    assert validate_tags(["a", "b"])                       # too few -> non-empty errors
    assert validate_tags(["Net-30", "gst", "saas"])        # uppercase
    assert validate_tags(["gst", "gst", "saas"])           # duplicate


def test_summary_sentence_count():
    assert validate_summary("One sentence. Two sentences.") == []
    assert validate_summary("Only one sentence.")           # too few
    assert validate_summary("")                             # empty


def test_dates_must_be_iso():
    assert validate_dates({"invoice_date": "2024-10-28", "due_date": None}) == []
    assert validate_dates({"start_date": "Oct 28, 2024"})   # non-ISO -> error


def test_grounding_flags_ungrounded_amount():
    fields = {"totals": {"total_due": "₹14,16,000"}}
    assert validate_grounding("Total is ₹14,16,000.", fields) == []
    assert validate_grounding("Total is ₹99,99,999.", fields)  # not in fields


def test_grounding_ignores_trailing_comma():
    # the amount is followed by a comma in the summary; it is still grounded
    fields = {"totals": {"total_due": "₹14,16,000"}}
    assert validate_grounding("The total is ₹14,16,000, including GST.", fields) == []


def test_summary_abbreviations_do_not_inflate_sentence_count():
    # "Ltd." mid-sentence (followed by capital "The") must not break the count, but the
    # period that genuinely ends sentence 1 must still be honoured -> 2 sentences.
    two = (
        "This is an invoice from Ententia AI Solutions Pvt. Ltd. to NovaBridge "
        "Financial Services Pvt. Ltd. The total due is stated below."
    )
    assert validate_summary(two) == []


def test_summary_three_real_sentences_with_abbreviations():
    # mirrors the real SOW summary: "Ltd. and"/"Ltd. for" are mid-sentence (lowercase) -> 3
    three = (
        "The SOW is between NovaBridge Financial Services Pvt. Ltd. and Ententia AI "
        "Solutions Pvt. Ltd. for the project. The budget is fixed. It runs for 20 weeks."
    )
    assert validate_summary(three) == []


def test_validate_routes_errors_to_stages():
    fields = {"start_date": "Oct 2024"}
    result = validate("Statement of Work", fields, tags=["a"], summary="One.")
    assert "extract" in result   # bad date
    assert "tag" in result       # too few tags
    assert "summarize" in result # one sentence
