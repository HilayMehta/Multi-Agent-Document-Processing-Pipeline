# Eval report — doc_004_invoice.pdf

## Results overview

| Parameter | Result | Gated |
|---|---|---|
| Classification | ✓ (`Invoice`) | Yes — must be 100% |
| Field accuracy | 27/27 (100%) | Yes — aggregate ≥ 90% |
| Tag Jaccard | 5/9 (56%) | No (informational) |
| Summary score | 0.77 | No (informational) |

## Classification

GT `Invoice` vs pred `Invoice` → ✓

## Field accuracy

**Authoritative score (Jaccard for lists):** 27/27 (100%)

> Note: every field is also re-validated against the Pydantic schema (type, nullability, `extra='forbid'`). The *Validation* column below lists the *additional* deterministic checks from `validation.py`. List-of-scalars rows show each GT item's best match; the list's contribution to field accuracy is Jaccard |∩|/|∪|.

| Field | Schema type | Ground truth | Predicted | Eval metric | Score | Match | Validation |
|---|---|---|---|---|---|---|---|
| invoice_number | `str \| None` | ENT-INV-2024-0043 | ENT-INV-2024-0043 | exact (numeric) | = | ✓ | — |
| invoice_date | `str \| None` | 2024-10-28 | 2024-10-28 | exact (numeric) | = | ✓ | ISO date (YYYY-MM-DD) |
| due_date | `str \| None` | 2024-11-27 | 2024-11-27 | exact (numeric) | = | ✓ | ISO date (YYYY-MM-DD) |
| payment_terms | `str \| None` | Net-30 | Net-30 | exact (normalized) | = | ✓ | Net-30 → due = invoice_date + 30d |
| reference_sow | `str \| None` | ENT-SOW-2024-019 | ENT-SOW-2024-019 | exact (numeric) | = | ✓ | — |
| vendor | `str \| None` | Ententia AI Solutions Pvt. Ltd. | ENTENTIA AI SOLUTIONS PVT. LTD. | exact (normalized) | = | ✓ | — |
| client | `str \| None` | NovaBridge Financial Services Pvt. Ltd. | NovaBridge Financial Services Pvt. Ltd. | exact (normalized) | = | ✓ | — |
| line_items[0].description | `str \| None` | Milestone 2 Delivery: Document Ingestion Pipeline & Classification Model (Beta) | Milestone 2 Delivery: Document Ingestion Pipeline & Classification Model (Beta) [per SOW ENT-SOW-2024-019, Milestone 2] | fuzzy (token_set/partial) | 100 | ✓ | — |
| line_items[0].quantity | `str \| None` | 1 | 1 | exact (numeric) | = | ✓ | — |
| line_items[0].unit_price | `str \| None` | ₹10,00,000 | ₹10,00,000 | exact (numeric) | = | ✓ | — |
| line_items[0].amount | `str \| None` | ₹10,00,000 | ₹10,00,000 | exact (numeric) | = | ✓ | Σ line amounts = subtotal |
| line_items[1].description | `str \| None` | Additional Data Annotation Services (Change Order CO-2024-003) | Additional Data Annotation Services — manual labelling of 1,200 edge-case documents [Change Order CO-2024-003, dated Oct 10, 2024] | fuzzy (token_set/partial) | 80 | ✓ | — |
| line_items[1].quantity | `str \| None` | 40 hrs | 40 hrs | exact (numeric) | = | ✓ | — |
| line_items[1].unit_price | `str \| None` | ₹3,500 | ₹3,500 | exact (numeric) | = | ✓ | — |
| line_items[1].amount | `str \| None` | ₹1,40,000 | ₹1,40,000 | exact (numeric) | = | ✓ | Σ line amounts = subtotal |
| line_items[2].description | `str \| None` | Cloud Infrastructure Setup & Configuration (one-time, at cost) | Cloud Infrastructure Setup & Configuration — AWS account provisioning, VPC setup, IAM roles [one-time, billed at cost] | fuzzy (token_set/partial) | 84 | ✓ | — |
| line_items[2].quantity | `str \| None` | 1 | 1 | exact (numeric) | = | ✓ | — |
| line_items[2].unit_price | `str \| None` | ₹60,000 | ₹60,000 | exact (numeric) | = | ✓ | — |
| line_items[2].amount | `str \| None` | ₹60,000 | ₹60,000 | exact (numeric) | = | ✓ | Σ line amounts = subtotal |
| totals.subtotal | `str \| None` | ₹12,00,000 | ₹12,00,000 | exact (numeric) | = | ✓ | = Σ items; ×GST = gst_amount; +gst = total |
| totals.gst_amount | `str \| None` | ₹2,16,000 | ₹2,16,000 | exact (numeric) | = | ✓ | subtotal × rate; subtotal + gst = total |
| totals.total_due | `str \| None` | ₹14,16,000 | ₹14,16,000 | exact (numeric) | = | ✓ | subtotal + gst_amount = total_due |
| payment_instructions.bank | `str \| None` | HDFC Bank Ltd., Noida Sector 18 | HDFC Bank Ltd., Noida Sector 18 | exact (normalized) | = | ✓ | — |
| payment_instructions.account_name | `str \| None` | Ententia AI Solutions Pvt. Ltd. | Ententia AI Solutions Pvt. Ltd. | exact (string) | = | ✓ | — |
| payment_instructions.account_number | `str \| None` | 50200098765432 | 50200098765432 | exact (numeric) | = | ✓ | — |
| payment_instructions.ifsc_code | `str \| None` | HDFC0001234 | HDFC0001234 | exact (numeric) | = | ✓ | — |
| payment_instructions.upi_or_email | `str \| None` | billing@ententia.ai | billing@ententia.ai | exact (normalized) | = | ✓ | — |

## Tags

**Jaccard (exact-match set overlap):** 5/9 (56%) — |∩|=5 matched, |∪|=9 (GT 7 + pred 7 − 5).

| Ground-truth tag | Predicted tag | Match |
|---|---|---|
| `net-30` | `net-30` | ✓ |
| `gst` | `gst` | ✓ |
| `change-order` | `change-order` | ✓ |
| `ai` | `ai` | ✓ |
| `b2b` | `b2b` | ✓ |
| `milestone-payment` | `cloud-infrastructure` | ✗ |
| `saas` | `milestone` | ✗ |

> ✗ rows line up the leftover GT and predicted tags **by position, not by meaning** — there is no match between them; the Match column is authoritative.

## Summary

> Combined score (0–1) = 50% lexical + 50% semantic. Components shown for transparency. Informational (not gated).

- **Summary score (combined, 0–1):** 0.77
  - lexical (token_set_ratio, 0–100): 65
  - semantic (embedding cosine, 0–1): 0.88

- **GT:** An invoice from Ententia AI Solutions to NovaBridge Financial Services for ₹14,16,000 (including 18% GST), due November 27, 2024. The invoice covers Milestone 2 delivery of the document ingestion pipeline and classifier (₹10,00,000), additional annotation services under Change Order CO-2024-003 (₹1,40,000), and one-time AWS infrastructure setup (₹60,000), all under SOW ENT-SOW-2024-019.
- **Predicted:** This document is an invoice from ENTENTIA AI SOLUTIONS PVT. LTD. to NovaBridge Financial Services Pvt. Ltd., dated October 28, 2024, with a due date of November 27, 2024. The invoice, numbered ENT-INV-2024-0043, totals ₹14,16,000, including GST, for services related to a document ingestion pipeline, data annotation, and cloud infrastructure setup. Payment terms are Net-30, and a late fee of 1.5% per month applies to overdue balances.