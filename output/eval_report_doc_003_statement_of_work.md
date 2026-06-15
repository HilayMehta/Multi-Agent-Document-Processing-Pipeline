# Eval report — doc_003_statement_of_work.docx

## Results overview

| Parameter | Result | Gated |
|---|---|---|
| Classification | ✓ (`Statement of Work`) | Yes — must be 100% |
| Field accuracy | 45/49 (92%) | Yes — aggregate ≥ 90% |
| Tag Jaccard | 4/10 (40%) | No (informational) |
| Summary score | 0.77 | No (informational) |

## Classification

GT `Statement of Work` vs pred `Statement of Work` → ✓

## Field accuracy

**Authoritative score (Jaccard for lists):** 45/49 (92%)

> Note: every field is also re-validated against the Pydantic schema (type, nullability, `extra='forbid'`). The *Validation* column below lists the *additional* deterministic checks from `validation.py`. List-of-scalars rows show each GT item's best match; the list's contribution to field accuracy is Jaccard |∩|/|∪|.

| Field | Schema type | Ground truth | Predicted | Eval metric | Score | Match | Validation |
|---|---|---|---|---|---|---|---|
| project_name | `str \| None` | Intelligent Document Processing Automation | Intelligent Document Processing Automation | exact (normalized) | = | ✓ | — |
| sow_number | `str \| None` | ENT-SOW-2024-019 | ENT-SOW-2024-019 | exact (numeric) | = | ✓ | — |
| client | `str \| None` | NovaBridge Financial Services Pvt. Ltd. | NovaBridge Financial Services Pvt. Ltd. | exact (normalized) | = | ✓ | — |
| vendor | `str \| None` | Ententia AI Solutions Pvt. Ltd. | Ententia AI Solutions Pvt. Ltd. | exact (normalized) | = | ✓ | — |
| start_date | `str \| None` | 2024-09-20 | 2024-09-20 | exact (numeric) | = | ✓ | ISO date (YYYY-MM-DD) |
| end_date | `str \| None` | 2025-02-07 | 2025-02-07 | exact (numeric) | = | ✓ | ISO date (YYYY-MM-DD) |
| total_budget | `str \| None` | ₹40,00,000 | ₹40,00,000 | exact (numeric) | = | ✓ | — |
| deliverables[0] | `str` | Document Ingestion & Pre-processing Module (PDF, JPEG, PNG, TIFF + OCR) | Scalable document ingestion and pre-processing pipeline supporting PDF, JPEG, PNG, and TIFF formats with OCR and quality assessment. | jaccard member (fuzzy) | 82 | ✓ | — |
| deliverables[1] | `str` | Document Classification Engine — 7 classes, ≥95% accuracy | Document classification engine with multi-class support and ≥95% accuracy on test set. | jaccard member (fuzzy) | 87 | ✓ | — |
| deliverables[2] | `str` | Intelligent Field Extraction with confidence scoring and human-review queue | Intelligent field extraction with named entity recognition and confidence scoring. | jaccard member (fuzzy) | 79 | ✓ | — |
| deliverables[3] | `str` | Validation & Business Rules Engine with cross-document checks | Validation and business rules engine with cross-document checks and audit logging. | jaccard member (fuzzy) | 98 | ✓ | — |
| deliverables[4] | `str` | REST API integration with Nucleus Software Finnone + webhook support | Integration and API layer with REST API, webhook support, and admin dashboard. | jaccard member (fuzzy) | 73 | ✓ | — |
| deliverables[5] | `str` | Admin dashboard for throughput and accuracy monitoring | Integration and API layer with REST API, webhook support, and admin dashboard. | jaccard member (fuzzy) | 52 | ✗ | — |
| deliverables[6] | `str` | Testing, UAT support (2 rounds), documentation, and on-site training | Testing, UAT, and handover with technical documentation and training. | jaccard member (fuzzy) | 68 | ✓ | — |
| payment_milestones[0].milestone | `str \| None` | Milestone 1 | Milestone 1 | exact (normalized) | = | ✓ | — |
| payment_milestones[0].name | `str \| None` | Architecture Sign-off | Architecture Decision Record and Data Handling Agreement | fuzzy (token_set/partial) | 78 | ✓ | — |
| payment_milestones[0].amount | `str \| None` | ₹8,00,000 | ₹8,00,000 | exact (numeric) | = | ✓ | — |
| payment_milestones[0].due_date | `str \| None` | 2024-09-20 | 2024-09-20 | exact (numeric) | = | ✓ | ISO date (YYYY-MM-DD) |
| payment_milestones[1].milestone | `str \| None` | Milestone 2 | Milestone 2 | exact (normalized) | = | ✓ | — |
| payment_milestones[1].name | `str \| None` | Ingestion Pipeline & Classifier (Beta) | Ingestion Pipeline and Classifier | fuzzy (token_set/partial) | 94 | ✓ | — |
| payment_milestones[1].amount | `str \| None` | ₹10,00,000 | ₹10,00,000 | exact (numeric) | = | ✓ | — |
| payment_milestones[1].due_date | `str \| None` | 2024-10-25 | 2024-10-25 | exact (numeric) | = | ✓ | ISO date (YYYY-MM-DD) |
| payment_milestones[2].milestone | `str \| None` | Milestone 3 | Milestone 3 | exact (normalized) | = | ✓ | — |
| payment_milestones[2].name | `str \| None` | Extraction Engine & Validation Rules | Extraction Engine and Validation Rule Engine | fuzzy (token_set/partial) | 93 | ✓ | — |
| payment_milestones[2].amount | `str \| None` | ₹12,00,000 | ₹12,00,000 | exact (numeric) | = | ✓ | — |
| payment_milestones[2].due_date | `str \| None` | 2024-12-06 | 2024-12-06 | exact (numeric) | = | ✓ | ISO date (YYYY-MM-DD) |
| payment_milestones[3].milestone | `str \| None` | Milestone 4 | Milestone 4 | exact (normalized) | = | ✓ | — |
| payment_milestones[3].name | `str \| None` | API Layer, Dashboard & UAT | Integrated API and UAT Support | fuzzy (token_set/partial) | 50 | ✗ | — |
| payment_milestones[3].amount | `str \| None` | ₹8,00,000 | ₹8,00,000 | exact (numeric) | = | ✓ | — |
| payment_milestones[3].due_date | `str \| None` | 2025-01-17 | 2025-01-17 | exact (numeric) | = | ✓ | ISO date (YYYY-MM-DD) |
| payment_milestones[4].milestone | `str \| None` | Milestone 5 | Milestone 5 | exact (normalized) | = | ✓ | — |
| payment_milestones[4].name | `str \| None` | Go-Live, Training & Documentation | Production Deployment and Training | fuzzy (token_set/partial) | 60 | ✗ | — |
| payment_milestones[4].amount | `str \| None` | ₹2,00,000 | ₹2,00,000 | exact (numeric) | = | ✓ | — |
| payment_milestones[4].due_date | `str \| None` | 2025-02-07 | 2025-02-07 | exact (numeric) | = | ✓ | ISO date (YYYY-MM-DD) |
| key_contacts[0].role | `str \| None` | Client — Exec Sponsor | Client — Exec Sponsor | fuzzy (token_set/partial) | 100 | ✓ | — |
| key_contacts[0].name | `str \| None` | Ramesh Iyer (CTO) | Ramesh Iyer | exact (normalized) | ≠ | ✗ | — |
| key_contacts[0].email | `str \| None` | ramesh.iyer@novabridge.in | ramesh.iyer@novabridge.in | exact (normalized) | = | ✓ | — |
| key_contacts[1].role | `str \| None` | Client — Project Lead | Client — Project Lead | fuzzy (token_set/partial) | 100 | ✓ | — |
| key_contacts[1].name | `str \| None` | Kavitha Subramaniam | Kavitha Subramaniam | exact (normalized) | = | ✓ | — |
| key_contacts[1].email | `str \| None` | kavitha.s@novabridge.in | kavitha.s@novabridge.in | exact (normalized) | = | ✓ | — |
| key_contacts[2].role | `str \| None` | Client — IT Integration | Client — IT Integration Lead | fuzzy (token_set/partial) | 100 | ✓ | — |
| key_contacts[2].name | `str \| None` | Yash Malhotra | Yash Malhotra | exact (normalized) | = | ✓ | — |
| key_contacts[2].email | `str \| None` | yash.malhotra@novabridge.in | yash.malhotra@novabridge.in | exact (normalized) | = | ✓ | — |
| key_contacts[3].role | `str \| None` | Vendor — Engagement Manager | Vendor — Exec Sponsor | fuzzy (token_set/partial) | 69 | ✓ | — |
| key_contacts[3].name | `str \| None` | Nishant Shah | Nishant Shah | exact (normalized) | = | ✓ | — |
| key_contacts[3].email | `str \| None` | nishant.shah@ententia.ai | nishant.shah@ententia.ai | exact (normalized) | = | ✓ | — |
| key_contacts[4].role | `str \| None` | Vendor — Technical Lead | Vendor — Technical Lead | fuzzy (token_set/partial) | 100 | ✓ | — |
| key_contacts[4].name | `str \| None` | Arjun Pillai | Arjun Pillai | exact (normalized) | = | ✓ | — |
| key_contacts[4].email | `str \| None` | arjun.pillai@ententia.ai | arjun.pillai@ententia.ai | exact (normalized) | = | ✓ | — |

## Tags

**Jaccard (exact-match set overlap):** 4/10 (40%) — |∩|=4 matched, |∪|=10 (GT 7 + pred 7 − 4).

| Ground-truth tag | Predicted tag | Match |
|---|---|---|
| `ai` | `ai` | ✓ |
| `ocr` | `ocr` | ✓ |
| `fintech` | `fintech` | ✓ |
| `multi-party` | `multi-party` | ✓ |
| `document-processing` | `idp` | ✗ |
| `milestone-based` | `b2b` | ✗ |
| `saas` | `change-order` | ✗ |

> ✗ rows line up the leftover GT and predicted tags **by position, not by meaning** — there is no match between them; the Match column is authoritative.

## Summary

> Combined score (0–1) = 50% lexical + 50% semantic. Components shown for transparency. Informational (not gated).

- **Summary score (combined, 0–1):** 0.77
  - lexical (token_set_ratio, 0–100): 66
  - semantic (embedding cosine, 0–1): 0.89

- **GT:** A 20-week statement of work between NovaBridge Financial Services and Ententia AI Solutions to build an AI-powered Intelligent Document Processing system for automating loan application document classification, extraction, and validation. The project runs from September 2024 to February 2025, covers 7 document classes, and is valued at ₹40,00,000 paid across 5 milestones. It includes OCR, a classification engine targeting ≥95% accuracy, field extraction with confidence scoring, validation rules, and integration with NovaBridge's Finnone loan origination system.
- **Predicted:** The document is a Statement of Work (SOW) between NovaBridge Financial Services Pvt. Ltd. and Ententia AI Solutions Pvt. Ltd. for the 'Intelligent Document Processing Automation' project. The project, with a total budget of ₹40,00,000, is scheduled to start on September 20, 2024, and end on February 7, 2025. It outlines deliverables such as a document ingestion pipeline, classification engine, and API integration, with payment milestones tied to specific deliverables throughout the project timeline.