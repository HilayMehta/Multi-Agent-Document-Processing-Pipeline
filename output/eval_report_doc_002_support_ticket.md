# Eval report — doc_002_support_ticket.pdf

## Results overview

| Parameter | Result | Gated |
|---|---|---|
| Classification | ✓ (`Support Ticket`) | Yes — must be 100% |
| Field accuracy | 13/13 (100%) | Yes — aggregate ≥ 90% |
| Tag Jaccard | 3/11 (27%) | No (informational) |
| Summary score | 0.81 | No (informational) |

## Classification

GT `Support Ticket` vs pred `Support Ticket` → ✓

## Field accuracy

**Authoritative score (Jaccard for lists):** 13/13 (100%)

> Note: every field is also re-validated against the Pydantic schema (type, nullability, `extra='forbid'`). The *Validation* column below lists the *additional* deterministic checks from `validation.py`. List-of-scalars rows show each GT item's best match; the list's contribution to field accuracy is Jaccard |∩|/|∪|.

| Field | Schema type | Ground truth | Predicted | Eval metric | Score | Match | Validation |
|---|---|---|---|---|---|---|---|
| ticket_metadata.ticket_id | `str \| None` | INC-2024-08471 | INC-2024-08471 | exact (numeric) | = | ✓ | — |
| ticket_metadata.submitted_by | `str \| None` | Priya Mehta (priya.mehta@acmecorp.com) | Priya Mehta (priya.mehta@acmecorp.com) | exact (normalized) | = | ✓ | — |
| ticket_metadata.submitted_date | `str \| None` | 2024-07-15 | 2024-07-15 | exact (numeric) | = | ✓ | ISO date (YYYY-MM-DD) |
| ticket_metadata.priority | `str \| None` | Critical | Critical | exact (normalized) | = | ✓ | — |
| ticket_metadata.category | `str \| None` | Access / Data Loss | Access / Data Loss | exact (normalized) | = | ✓ | — |
| ticket_metadata.affected_system | `str \| None` | Oracle Financials ERP (Production) | Oracle Financials ERP (Production) | exact (normalized) | = | ✓ | — |
| ticket_metadata.assigned_to | `str \| None` | Platform Engineering Team | Platform Engineering Team | exact (normalized) | = | ✓ | — |
| ticket_metadata.current_status | `str \| None` | Resolved | Resolved | exact (normalized) | = | ✓ | — |
| issue_details.description | `str \| None` | Four Accounts Payable team members unable to log into Oracle Financials ERP since 9:00 AM IST on 2024-07-15. Error: ORA-01017 invalid username/password. Suspected cause: Oracle LDAP connector not synced after a mass AD password rotation on July 14 at 11:30 PM. | Since the morning of July 15, Priya Mehta and three other Accounts Payable team members are unable to log into Oracle Financials, receiving an ORA-01017 error. This issue is blocking invoice processing and payment runs, with over 200 vendor invoices totaling approximately ₹1.8 crore needing processing by 5:00 PM IST. The problem arose after an Active Directory password rotation, with Oracle's LDAP connector not syncing post-rotation. | fuzzy (token_set/partial) | 62 | ✓ | — |
| resolution.root_cause | `str \| None` | Oracle LDAP connector sync job failed silently after AD password rotation | Oracle LDAP connector sync job failed silently after AD rotation. | fuzzy (token_set/partial) | 93 | ✓ | — |
| resolution.resolved_by | `str \| None` | Vikram Nair (vikram.nair@acmecorp.com) | Vikram Nair (vikram.nair@acmecorp.com) | exact (normalized) | = | ✓ | — |
| resolution.resolution_time | `str \| None` | 1 hour 33 minutes | 1 hour 33 minutes | exact (normalized) | = | ✓ | — |
| resolution.resolution_notes | `str \| None` | Manually re-triggered LDAP sync at 10:45 AM; sync completed at 11:10 AM. All affected users confirmed able to log in. Post-mortem scheduled for July 17. | Platform Engineering identified the root cause as a failed Oracle LDAP connector sync job after AD rotation. The sync was manually re-triggered and completed successfully, allowing all affected users to log in. A post-mortem is scheduled, and LDAP sync monitoring alerts will be added. | fuzzy (token_set/partial) | 73 | ✓ | — |

## Tags

**Jaccard (exact-match set overlap):** 3/11 (27%) — |∩|=3 matched, |∪|=11 (GT 7 + pred 7 − 3).

| Ground-truth tag | Predicted tag | Match |
|---|---|---|
| `erp` | `erp` | ✓ |
| `ldap` | `ldap` | ✓ |
| `resolved` | `resolved` | ✓ |
| `p1` | `critical` | ✗ |
| `production-down` | `financial-operations` | ✗ |
| `access` | `production` | ✗ |
| `data-loss-risk` | `access-issue` | ✗ |

> ✗ rows line up the leftover GT and predicted tags **by position, not by meaning** — there is no match between them; the Match column is authoritative.

## Summary

> Combined score (0–1) = 50% lexical + 50% semantic. Components shown for transparency. Informational (not gated).

- **Summary score (combined, 0–1):** 0.81
  - lexical (token_set_ratio, 0–100): 73
  - semantic (embedding cosine, 0–1): 0.89

- **GT:** A critical IT support ticket from Priya Mehta (Accounts Payable) reporting that four team members were locked out of Oracle Financials ERP on July 15, 2024, blocking ₹1.8 crore in time-sensitive vendor payments. Root cause was the LDAP connector failing to sync after a scheduled AD password rotation. Resolved by Vikram Nair in under 2 hours by manually re-triggering the LDAP sync.
- **Predicted:** This support ticket, submitted by Priya Mehta on July 15, 2024, involves a critical access issue affecting the Oracle Financials ERP system at Acme Corporation. The problem, caused by a failed Oracle LDAP connector sync job after an Active Directory password rotation, prevented Priya and three other team members from logging in, risking the processing of over 200 vendor invoices totaling approximately ₹1.8 crore. The issue was resolved by Vikram Nair from the Platform Engineering Team in 1 hour and 33 minutes by manually re-triggering the LDAP sync, and a post-mortem is scheduled to prevent future occurrences.