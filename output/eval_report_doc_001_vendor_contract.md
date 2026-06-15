# Eval report — doc_001_vendor_contract.docx

## Results overview

| Parameter | Result | Gated |
|---|---|---|
| Classification | ✓ (`Vendor Contract`) | Yes — must be 100% |
| Field accuracy | 13/13 (100%) | Yes — aggregate ≥ 90% |
| Tag Jaccard | 3/11 (27%) | No (informational) |
| Summary score | 0.76 | No (informational) |

## Classification

GT `Vendor Contract` vs pred `Vendor Contract` → ✓

## Field accuracy

**Authoritative score (Jaccard for lists):** 13/13 (100%)

> Note: every field is also re-validated against the Pydantic schema (type, nullability, `extra='forbid'`). The *Validation* column below lists the *additional* deterministic checks from `validation.py`. List-of-scalars rows show each GT item's best match; the list's contribution to field accuracy is Jaccard |∩|/|∪|.

| Field | Schema type | Ground truth | Predicted | Eval metric | Score | Match | Validation |
|---|---|---|---|---|---|---|---|
| parties_and_dates.parties[0] | `str` | Acme Corporation | Acme Corporation | jaccard member (exact) | = | ✓ | — |
| parties_and_dates.parties[1] | `str` | CloudBase Inc. | CloudBase Inc. | jaccard member (exact) | = | ✓ | — |
| parties_and_dates.effective_date | `str \| None` | 2024-03-01 | 2024-03-01 | exact (numeric) | = | ✓ | ISO date (YYYY-MM-DD) |
| parties_and_dates.expiry_date | `str \| None` | 2025-02-28 | 2025-02-28 | exact (numeric) | = | ✓ | ISO date (YYYY-MM-DD) |
| commercial_terms.contract_value | `str \| None` | $120,000 USD/year | $120,000 USD/year | exact (normalized) | = | ✓ | — |
| commercial_terms.payment_terms | `str \| None` | Quarterly in advance at $30,000/quarter; Net-30 from invoice date; 1.5% per month late interest | Customer shall pay Vendor an annual subscription fee of $120,000 USD, invoiced quarterly in advance at $30,000 per quarter. All invoices are due Net-30 from the invoice date. Late payments accrue interest at 1.5% per month. | fuzzy (token_set/partial) | 82 | ✓ | — |
| renewal_and_termination.auto_renewal | `str \| None` | Yes — auto-renews for successive 1-year terms | Yes — auto-renews for successive one-year periods | fuzzy (token_set/partial) | 91 | ✓ | — |
| renewal_and_termination.auto_renewal_notice_period | `str \| None` | 45 days prior written notice to prevent renewal | 45 days | fuzzy (token_set/partial) | 100 | ✓ | — |
| renewal_and_termination.termination_notice_convenience | `str \| None` | 30 days | 30 days' prior written notice | fuzzy (token_set/partial) | 100 | ✓ | — |
| renewal_and_termination.termination_notice_cause | `str \| None` | 15 days to cure after written notice | 15 days to cure breach after notice | fuzzy (token_set/partial) | 89 | ✓ | — |
| legal.governing_law | `str \| None` | State of Delaware | State of Delaware | exact (normalized) | = | ✓ | — |
| legal.dispute_resolution | `str \| None` | Binding arbitration via JAMS, New York, NY | binding arbitration in New York, NY under the rules of JAMS | fuzzy (token_set/partial) | 88 | ✓ | — |
| legal.liability_cap | `str \| None` | Total fees paid or payable in the 12 months immediately preceding the claim | the total fees paid or payable by Customer in the twelve (12) months immediately preceding the claim | fuzzy (token_set/partial) | 98 | ✓ | — |

## Tags

**Jaccard (exact-match set overlap):** 3/11 (27%) — |∩|=3 matched, |∪|=11 (GT 7 + pred 7 − 3).

| Ground-truth tag | Predicted tag | Match |
|---|---|---|
| `cloud-infrastructure` | `cloud-infrastructure` | ✓ |
| `auto-renewal` | `auto-renewal` | ✓ |
| `net-30` | `net-30` | ✓ |
| `saas` | `b2b` | ✗ |
| `liability-cap` | `managed-service` | ✗ |
| `indemnity` | `subscription` | ✗ |
| `multi-party` | `bilateral` | ✗ |

> ✗ rows line up the leftover GT and predicted tags **by position, not by meaning** — there is no match between them; the Match column is authoritative.

## Summary

> Combined score (0–1) = 50% lexical + 50% semantic. Components shown for transparency. Informational (not gated).

- **Summary score (combined, 0–1):** 0.76
  - lexical (token_set_ratio, 0–100): 69
  - semantic (embedding cosine, 0–1): 0.83

- **GT:** A master services agreement between Acme Corporation and CloudBase Inc. for cloud hosting, managed Kubernetes orchestration, and 24/7 infrastructure monitoring, valued at $120,000/year. The 12-month contract runs from March 2024 to February 2025, auto-renews unless 45 days' notice is given, and caps liability at the prior 12 months of fees paid. Governed by Delaware law with disputes resolved via JAMS arbitration in New York.
- **Predicted:** This Vendor Contract is an agreement between Acme Corporation and CloudBase Inc., effective from March 1, 2024, to February 28, 2025. The contract involves an annual subscription fee of $120,000 USD, paid quarterly at $30,000 per quarter, with invoices due within 30 days. The agreement includes automatic renewal for one-year periods unless terminated with a 45-day notice, and it is governed by Delaware law with disputes resolved through arbitration in New York.