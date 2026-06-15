# Evaluation Scoring: How Accuracy Is Calculated

This document explains exactly how `eval/evaluate.py` scores the pipeline's output against
`data/ground_truth.json`, field by field. It is the reference for interpreting the eval table.

## 1. The four scored components

For each document the harness scores four things independently:

| Component | How it scores | Gated? |
|-----------|---------------|--------|
| **Classification** | exact string match of `document_type` | **Yes**, must be 100% |
| **Extracted fields** | per-leaf walk (the bulk of this doc) | **Yes**, aggregate >= 90% |
| **Tags** | exact-match Jaccard set overlap | No (informational) |
| **Summary** | one combined lexical + semantic similarity score (0 to 1) | No (informational) |

The CI gate (non-zero exit) trips if **classification < 100%** OR **aggregate field accuracy < 90%**.

---

## 2. Field accuracy: the core algorithm

Ground truth for a document is a nested structure (dicts, lists, scalars). The scorer walks the
**ground-truth** structure and, for every **leaf** value, finds the corresponding value in the
prediction at the same path and decides match / no-match. Each leaf is worth **1 point**.

```
field accuracy (per doc)  = matched leaves / total leaves
aggregate field accuracy  = sum(matched leaves) / sum(total leaves)   (across all 4 docs)
```

The walk has three cases.

### 2a. Scalar leaf (string / number / null)

Decision order in `_compare_leaf`:

1. **Both null** is a match. (This is the "absent fields are null, not omitted" guarantee being
   rewarded, not penalised.)
2. **One null, one present** is no match.
3. **Key looks like an identifier / number / date / amount** (see the hint list below): **EXACT**
   comparison:
   - if both values parse as numbers (`parse_inr`), compare **numerically**
     (`₹14,16,000` equals `₹ 14,16,000` equals `1416000`);
   - otherwise compare as strings after lowercasing and removing all spaces
     (`HDFC0001234` equals `hdfc0001234`).
4. **Otherwise (free text)**: **FUZZY**, `max(token_set_ratio, partial_ratio) >= 60`
   (rapidfuzz, 0 to 100). `token_set_ratio` handles word reordering; `partial_ratio` handles the
   case where one value is a subset / substring of the other (for example GT "30 days" vs the
   fuller, correct "30 days' prior written notice").

**The "exact field" hint list** (a key is scored EXACT if it *contains* any of these substrings,
case-insensitive):

```
date, number, id, code, amount, price, subtotal, total, budget, ifsc, account, sow, rate, quantity
```

Rationale: identifiers, codes, dates, and money must be character- or value-exact (a wrong digit
is wrong), while descriptions, names, terms, and notes are prose where phrasing legitimately varies.

**Path-targeted exact override.** Beyond the key-hint list, specific fields are pinned to
**normalized-exact** by their full path (list indices stripped) via `_EXACT_PATHS` /
`_is_exact_path`, for example `ticket_metadata.priority`, `key_contacts.name`. This is path-based
(not key-based) so one field can be exact while a sibling sharing the same leaf key stays fuzzy
(`key_contacts.name` exact, `payment_milestones.name` fuzzy). These use **normalized string
equality only**, lowercase plus whitespace-stripped, with **no numeric shortcut**, so incidental
digits (for example a bank "Sector 18") cannot false-match. A field hit by a numeric / ID hint
still takes the hint (numeric) path first.

### 2b. List of scalars: JACCARD (set overlap)

For example `deliverables: [...]`. The two lists are treated as **sets** and scored by Jaccard
similarity:

```
score = |intersection| / |union|
```

The **intersection** is built by one-to-one fuzzy matching: each GT item claims the first
not-yet-used predicted item that satisfies the scalar rule from 2a, so a single predicted item
cannot cover two GT items. The **union** = `len(GT) + len(predicted) - |intersection|`. The walk
returns `(|intersection|, |union|)`, which slots straight into the aggregate
`sum(matched) / sum(total)`.

Why Jaccard (not recall): unlike recall, Jaccard penalises **both** directions. A missing GT item
*and* an extra predicted item each enlarge the union and lower the score. So if GT has 7
deliverables and the prediction has 6 that all match, the score is 6/7, about 0.86; predicting 6
correct plus 3 junk items scores 6/9, about 0.67. This makes over- and under-prediction both
visible rather than rewarding the extractor for emitting extra items.

### 2c. List of dicts: GREEDY ALIGNMENT, then per-leaf

For example `payment_milestones`, `key_contacts`, `line_items`. Each GT dict is greedily matched
to the **not-yet-used** predicted dict with the highest leaf-match ratio; then that pair is scored
leaf-by-leaf (recursively, so the rules in 2a apply to each inner field). Score = sum of matched
inner leaves / sum of inner leaves.

This gives **partial credit**: a milestone whose `amount` and `due_date` are right but whose
`name` differs scores 3/4, not 0.

---

## 3. Per-field reference (which rule applies to each field)

`E` = exact (hint: numeric / ID), `Ex` = normalized-exact (path-targeted string), `F` = fuzzy
free-text, `L(scalars)` = Jaccard set-overlap list, `L(dicts)` = aligned dict list.

### Vendor Contract
| Field | Rule | Note |
|-------|------|------|
| parties_and_dates.parties | L(scalars), **Ex** members | party names exact-matched |
| parties_and_dates.effective_date / expiry_date | E | ISO date, exact |
| commercial_terms.contract_value | **Ex** | "$120,000 USD/year" |
| commercial_terms.payment_terms | F | long free text |
| renewal_and_termination.auto_renewal | F | |
| renewal_and_termination.auto_renewal_notice_period | F | |
| renewal_and_termination.termination_notice_convenience | F | GT "30 days" is a substring of fuller pred, so partial_ratio matches it |
| renewal_and_termination.termination_notice_cause | F | |
| legal.governing_law | **Ex** | |
| legal.dispute_resolution / liability_cap | F | |

### Support Ticket
| Field | Rule | Note |
|-------|------|------|
| ticket_metadata.ticket_id | E | "id" hint |
| ticket_metadata.submitted_date | E | "date" hint |
| ticket_metadata.submitted_by | **Ex** | "Name (email)" |
| ticket_metadata.priority | **Ex** | normalized ("CRITICAL" equals "Critical") |
| ticket_metadata.category / affected_system / assigned_to / current_status | **Ex** | |
| issue_details.description | F | synthesized paraphrase |
| resolution.resolved_by / resolution_time | **Ex** | |
| resolution.root_cause / resolution_notes | F | prose |

### Statement of Work
| Field | Rule | Note |
|-------|------|------|
| project_name | **Ex** | |
| sow_number | E | "sow" + "number" hints |
| client / vendor | **Ex** | |
| start_date / end_date | E | "date" hint |
| total_budget | E | "total" + "budget", numeric (`₹40,00,000`) |
| deliverables | L(scalars) | Jaccard; 6-vs-7 gives 6/7, about 0.86 |
| payment_milestones | L(dicts) | per item: milestone **Ex**, name F, amount E, due_date E |
| key_contacts | L(dicts) | per item: role F (GT-label trap, section 6), name **Ex**, email **Ex** |

### Invoice
| Field | Rule | Note |
|-------|------|------|
| invoice_number | E | "number" hint |
| invoice_date / due_date | E | "date" hint |
| payment_terms | **Ex** | "Net-30" |
| reference_sow | E | "sow" hint |
| vendor / client | **Ex** | |
| line_items | L(dicts) | per item: description F, quantity E, unit_price E, amount E |
| totals.subtotal / gst_amount / total_due | E | numeric, exact equality of parsed value |
| totals.gst_rate | E | "rate" hint (not present in GT, so unscored) |
| payment_instructions.bank | **Ex** | |
| payment_instructions.account_name | E | matched by "account" hint, a name compared exactly* |
| payment_instructions.account_number | E | "account" + "number" |
| payment_instructions.ifsc_code | E | "ifsc" + "code" |
| payment_instructions.upi_or_email | **Ex** | |

\* Known simplification: `account_name` contains the substring "account", so it is scored EXACT
even though it is a company name. Harmless here (GT and prediction match exactly), but it shows the
hint list is a heuristic, not a perfect classifier.

---

## 4. Tags, summary (informational, not gated)

- **Tags**: **exact-match Jaccard**, the same set-overlap metric as list-of-scalars (2b) but with
  *exact* member equality instead of fuzzy. Each GT tag claims the first unused predicted tag that
  is string-equal after normalising (lowercase plus collapse whitespace), so `Net-30` equals
  `net-30` but synonyms (`saas` vs `annual-subscription`) do **not** match. Score is
  `|intersection| / |union|`. Deliberately strict; not gated because tag vocabulary is subjective
  (see FINDINGS section 9).
- **Summary**: **one combined score on 0 to 1**, a weighted blend of two complementary similarity
  signals (`_summary_score`):

  ```
  combined = SUMMARY_LEX_WEIGHT * (lexical / 100) + (1 - SUMMARY_LEX_WEIGHT) * semantic
  ```

  - **Lexical**: `token_set_ratio` of GT vs predicted summary (0 to 100, scaled to 0 to 1);
    shared terminology / keyword overlap.
  - **Semantic**: cosine similarity of OpenAI embeddings (`MODEL_EMBED`, default
    `text-embedding-3-small`) of the two summaries (0 to 1); catches same-meaning,
    different-wording that the lexical score misses. Both summaries are embedded in one API call.

  `SUMMARY_LEX_WEIGHT` defaults to **0.5** (equal weight). The two components are still printed in
  the per-doc report for transparency, but the headline is the single blended number. Lexical
  secures keyword presence (blind to paraphrase); semantic captures meaning (but can rate two
  same-topic-but-factually-different summaries as close), so blending balances the two. If
  embeddings are unavailable (no API key or offline), the score **falls back to lexical-only** so a
  cached eval still runs; pin the embedding model id for run-to-run comparability. Not gated
  because a 2 to 3 sentence summary legitimately selects which figures and phrasing to include.

---

## 5. Worked examples

- **`due_date` = "2024-11-27" vs "2024-11-27"**: key has "date", so EXACT; both parse as dates,
  strings equal, so it is a match (1/1).
- **`total_due` "₹14,16,000" vs "₹ 14,16,000"**: "total", so EXACT; `parse_inr` both equal
  1416000, so it is a match.
- **`termination_notice_convenience` "30 days" vs "30 days' prior written notice"**: free text;
  `token_set_ratio` is low (the apostrophe splits "days'"), but `partial_ratio` is about 95 (GT is
  a substring), so `max(...) >= 60` is a match.
- **`payment_milestones[0].name` "Architecture Sign-off" vs "Architecture Decision Record, Data
  Handling Agreement"**: free text; both ratios low, so no match (the GT-label trap: GT wording is
  not in the source document, so this is unscorable, not an extraction error, see FINDINGS
  section 6). The sibling `amount` / `due_date` / `milestone` of that item still score, so the
  milestone gets partial credit.

---

## 6. Residual misses are ground-truth labels, not extraction errors

After the `partial_ratio` and path-targeted-exact rules, the residual misses are the **GT-label
traps**: a few SOW milestone names and one contact field where ground truth uses wording absent
from the document (for example "Architecture Sign-off", or "Ramesh Iyer (CTO)" where the document
gives only "Ramesh Iyer"). These are genuinely unscorable by any lexical metric and are **not
extraction errors**. They are reported transparently in the eval's "missed fields" list. With
them included, aggregate field accuracy on the four samples is 96% (98/102), which clears the 90%
gate. The breakdown is discussed in the README's limitations section.
