"""Per-document evaluation reports: one markdown table per document.

Columns: field | schema type | ground truth | predicted | eval metric | score | match | validation.
- schema type   : introspected from the Pydantic extraction schema (single source of truth).
- eval metric   : which scoring rule fired (from evaluate.py — numbers match `cli eval`).
- validation    : the deterministic logic-layer checks (validation.py) that apply to that field.

Run:  PYTHONPATH=src python eval/report.py
"""

import json
import re
import typing
from itertools import zip_longest
from pathlib import Path

from pydantic import BaseModel
from rapidfuzz import fuzz

import config
from evaluate import (
    FUZZY_FIELD_THRESHOLD,
    SUMMARY_LEX_WEIGHT,
    _get_output,
    _is_exact_field,
    _is_exact_path,
    _norm,
    _summary_score,
    _tag_jaccard,
    _walk,
)
from registry import EXTRACTORS
from validation import parse_inr


# ── formatting ──────────────────────────────────────────────────────────────────
def _fmt(value: object) -> str:
    if value is None:
        return "—"
    # flatten newlines and escape pipes so the value stays in one table cell; no truncation
    return str(value).replace("|", "\\|").replace("\n", " ")


# ── schema-type introspection ───────────────────────────────────────────────────
def _root_model(doc_type: str) -> type[BaseModel]:
    return EXTRACTORS[doc_type].schema      # reports run only on the four supported sample types


def _unwrap_optional(ann: object) -> object:
    args = typing.get_args(ann)
    if args and type(None) in args:
        return next(a for a in args if a is not type(None))
    return ann


def _fmt_type(ann: object) -> str:
    if ann is None:
        return "?"
    if isinstance(ann, type):
        return ann.__name__
    s = str(ann).replace("typing.", "").replace("NoneType", "None")
    return re.sub(r"\b\w+\.(?=[A-Z]\w*)", "", s)        # strip module path before ClassName


def _schema_type(root: type[BaseModel], path: str) -> str:
    """Resolve the schema-declared type at a leaf path like 'totals.subtotal' or 'line_items[0].amount'."""
    cur: object = root
    ann: object = None
    for seg in path.split("."):
        m = re.match(r"([^\[]+)(\[\d+\])?", seg)
        name, indexed = m.group(1), bool(m.group(2))
        if not (isinstance(cur, type) and issubclass(cur, BaseModel)):
            return "?"
        field = cur.model_fields.get(name)
        if field is None:
            return "?"
        ann = field.annotation
        core = _unwrap_optional(ann)
        if indexed:                                      # step into list[X] -> X
            inner = typing.get_args(core)
            cur = ann = inner[0] if inner else None
        elif isinstance(core, type) and issubclass(core, BaseModel):
            cur = core                                   # descend into nested model
        else:
            cur = core
    return _fmt_type(ann)


# ── validation-layer mapping ─────────────────────────────────────────────────────
def _validation_for(doc_type: str, path: str) -> str:
    key = path.split(".")[-1].split("[")[0].lower()
    checks: list[str] = []
    if "date" in key:
        checks.append("ISO date (YYYY-MM-DD)")
    if doc_type == "Invoice":
        if path.startswith("line_items") and key == "amount":
            checks.append("Σ line amounts = subtotal")
        elif path == "totals.subtotal":
            checks.append("= Σ items; ×GST = gst_amount; +gst = total")
        elif path == "totals.gst_rate":
            checks.append("subtotal × rate = gst_amount")
        elif path == "totals.gst_amount":
            checks.append("subtotal × rate; subtotal + gst = total")
        elif path == "totals.total_due":
            checks.append("subtotal + gst_amount = total_due")
        elif key == "payment_terms":
            checks.append("Net-30 → due = invoice_date + 30d")
    return "; ".join(checks) if checks else "—"


# ── per-leaf eval rows ───────────────────────────────────────────────────────────
def _leaf_row(key: str, exp: object, pred: object, path: str) -> tuple[str, str, str, str, bool]:
    if exp is None and pred is None:
        return "—", "—", "both-null", "—", True
    if exp is None or pred is None:
        return _fmt(exp), _fmt(pred), "null-mismatch", "0", False
    e, p = _norm(exp), _norm(pred)
    if _is_exact_field(key):
        ev, pv = parse_inr(str(exp)), parse_inr(str(pred))
        if ev is not None and pv is not None:
            ok = ev == pv
            return _fmt(exp), _fmt(pred), "exact (numeric)", "=" if ok else "≠", ok
        ok = e.replace(" ", "") == p.replace(" ", "")
        return _fmt(exp), _fmt(pred), "exact (string)", "=" if ok else "≠", ok
    if _is_exact_path(path):
        ok = e.replace(" ", "") == p.replace(" ", "")
        return _fmt(exp), _fmt(pred), "exact (normalized)", "=" if ok else "≠", ok
    score = max(fuzz.token_set_ratio(e, p), fuzz.partial_ratio(e, p))
    return _fmt(exp), _fmt(pred), "fuzzy (token_set/partial)", f"{score:.0f}", score >= FUZZY_FIELD_THRESHOLD


def _rows(doc_type: str, root: type[BaseModel], exp: object, pred: object, path: str, out: list) -> None:
    if isinstance(exp, dict):
        psub = pred if isinstance(pred, dict) else {}
        for k, v in exp.items():
            _rows(doc_type, root, v, psub.get(k), f"{path}.{k}" if path else k, out)
    elif isinstance(exp, list):
        _list_rows(doc_type, root, exp, pred if isinstance(pred, list) else [], path, out)
    else:
        gt, pr, metric, score, ok = _leaf_row(path.split(".")[-1].split("[")[0], exp, pred, path)
        out.append((path, _schema_type(root, path), gt, pr, metric, score, ok,
                    _validation_for(doc_type, path)))


def _list_rows(doc_type, root, exp: list, pred: list, path: str, out: list) -> None:
    if exp and isinstance(exp[0], dict):                 # list of dicts -> greedy align
        used: set[int] = set()
        for i, ei in enumerate(exp):
            best_j, best_ratio = None, -1.0
            for j, pj in enumerate(pred):
                if j in used:
                    continue
                m, t = _walk(ei, pj, "", "", [])
                ratio = m / t if t else 0
                if ratio > best_ratio:
                    best_ratio, best_j = ratio, j
            if best_j is not None:
                used.add(best_j)
            _rows(doc_type, root, ei, pred[best_j] if best_j is not None else None, f"{path}[{i}]", out)
    else:                                                # list of scalars -> per-item best match
        exact = _is_exact_path(path)
        for i, ei in enumerate(exp):
            best_pred, best_score, best_ok = None, -1.0, False
            for pj in pred:
                if exact:
                    ok = _norm(ei).replace(" ", "") == _norm(pj).replace(" ", "")
                    sc = 100.0 if ok else 0.0
                else:
                    sc = max(fuzz.token_set_ratio(_norm(ei), _norm(pj)),
                             fuzz.partial_ratio(_norm(ei), _norm(pj)))
                    ok = sc >= FUZZY_FIELD_THRESHOLD
                if sc > best_score:
                    best_score, best_pred, best_ok = sc, pj, ok
            metric = "jaccard member (exact)" if exact else "jaccard member (fuzzy)"
            score_cell = ("=" if best_ok else "≠") if exact else (f"{best_score:.0f}" if pred else "—")
            out.append((f"{path}[{i}]", _schema_type(root, f"{path}[{i}]"), _fmt(ei),
                        _fmt(best_pred), metric, score_cell, best_ok, "—"))


def _tag_match_detail(gt_tags: list[str], pred_tags: list[str]
                      ) -> tuple[list[tuple[str, str]], list[str], list[str]]:
    """One-to-one exact (normalised) tag match — mirrors evaluate._tag_jaccard.
    Returns (matched_pairs, missed_gt_tags, extra_pred_tags)."""
    used: set[int] = set()
    matched: list[tuple[str, str]] = []
    missed: list[str] = []
    for g in gt_tags:
        hit = None
        for j, pt in enumerate(pred_tags):
            if j not in used and _norm(g) == _norm(pt):
                used.add(j)
                hit = pt
                break
        (matched.append((g, hit)) if hit is not None else missed.append(g))
    extra = [pt for j, pt in enumerate(pred_tags) if j not in used]
    return matched, missed, extra


def _write_report(doc_name: str, gt: dict, out: dict) -> Path:
    doc_type = gt["document_type"]
    root = _root_model(doc_type)
    rows: list = []
    _rows(doc_type, root, gt["extracted_fields"], out["extracted_fields"], "", rows)

    m, t = _walk(gt["extracted_fields"], out["extracted_fields"], "", "", [])   # authoritative
    class_ok = doc_type == out["classification"]["document_type"]
    pred_type = out["classification"]["document_type"]
    tag_i, tag_u = _tag_jaccard(gt["tags"], out["tags"])
    tag_score = tag_i / tag_u if tag_u else 0.0
    sscore, lex, sem = _summary_score(gt["summary"], out["summary"])   # also used in ## Summary
    sem_str = f"{sem:.2f}" if sem is not None else "— (unavailable, score is lexical-only)"

    lines = [
        f"# Eval report — {doc_name}",
        "",
        "## Results overview",
        "",
        "| Parameter | Result | Gated |",
        "|---|---|---|",
        f"| Classification | {'✓' if class_ok else '✗'} (`{pred_type}`) | Yes — must be 100% |",
        f"| Field accuracy | {m}/{t} ({m / t:.0%}) | Yes — aggregate ≥ 90% |",
        f"| Tag Jaccard | {tag_i}/{tag_u} ({tag_score:.0%}) | No (informational) |",
        f"| Summary score | {sscore:.2f} | No (informational) |",
        "",
        "## Classification",
        "",
        f"GT `{doc_type}` vs pred `{pred_type}` → {'✓' if class_ok else '✗'}",
        "",
        "## Field accuracy",
        "",
        f"**Authoritative score (Jaccard for lists):** {m}/{t} ({m / t:.0%})",
        "",
        "> Note: every field is also re-validated against the Pydantic schema (type, nullability, "
        "`extra='forbid'`). The *Validation* column below lists the *additional* deterministic "
        "checks from `validation.py`. List-of-scalars rows show each GT item's best match; the "
        "list's contribution to field accuracy is Jaccard |∩|/|∪|.",
        "",
        "| Field | Schema type | Ground truth | Predicted | Eval metric | Score | Match | Validation |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for path, stype, gtv, prv, metric, score, ok, valid in rows:
        stype_cell = stype.replace("|", "\\|")   # escape pipe so it isn't a table delimiter
        lines.append(f"| {path} | `{stype_cell}` | {gtv} | {prv} | {metric} | {score} | "
                     f"{'✓' if ok else '✗'} | {valid} |")

    matched, missed, extra = _tag_match_detail(gt["tags"], out["tags"])
    lines += ["", "## Tags", "",
              f"**Jaccard (exact-match set overlap):** {tag_i}/{tag_u} ({tag_score:.0%}) "
              f"— |∩|={tag_i} matched, |∪|={tag_u} (GT {len(gt['tags'])} + pred "
              f"{len(out['tags'])} − {tag_i}).",
              "",
              "| Ground-truth tag | Predicted tag | Match |",
              "|---|---|---|"]
    for g, pt in matched:                                    # exact matches: GT == pred
        lines.append(f"| `{g}` | `{pt}` | ✓ |")
    for g, e in zip_longest(missed, extra):                  # unmatched GT vs predicted-only
        gcell = f"`{g}`" if g else ""
        ecell = f"`{e}`" if e else ""
        lines.append(f"| {gcell} | {ecell} | ✗ |")
    lines += ["", "> ✗ rows line up the leftover GT and predicted tags **by position, not by "
              "meaning** — there is no match between them; the Match column is authoritative."]

    lines += ["", "## Summary", "",
              f"> Combined score (0–1) = {SUMMARY_LEX_WEIGHT:.0%} lexical + "
              f"{1 - SUMMARY_LEX_WEIGHT:.0%} semantic. Components shown for transparency. "
              "Informational (not gated).",
              "",
              f"- **Summary score (combined, 0–1):** {sscore:.2f}",
              f"  - lexical (token_set_ratio, 0–100): {lex:.0f}",
              f"  - semantic (embedding cosine, 0–1): {sem_str}",
              "",
              f"- **GT:** {gt['summary']}", f"- **Predicted:** {out['summary']}"]

    report_path = config.OUTPUT_DIR / f"eval_report_{Path(doc_name).stem}.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> int:
    ground_truth = json.loads(config.GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    for doc_name, gt in ground_truth.items():
        path = _write_report(doc_name, gt, _get_output(doc_name))
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
