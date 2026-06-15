"""Evaluate pipeline output against data/ground_truth.json.

Scoring rules (from FINDINGS):
- classification: exact match (the gate).
- tags: exact-match Jaccard set overlap, normalised/case-insensitive (informational).
- fields: walk every GT leaf. IDs/dates/codes/amounts -> exact (case- + space-insensitive,
  amounts compared numerically); free text -> token_set_ratio >= 60; both-null -> match.
  Lists of scalars scored by JACCARD (|intersection| / |union|, one-to-one fuzzy match), so
  both missing and extra items are penalised. Lists of dicts are greedily aligned and scored
  leaf-by-leaf.
- summary: one combined score on 0-1 = weighted blend of lexical (token_set_ratio) and
  semantic (embedding cosine) similarity. Informational.
- exit non-zero if classification < 100% or aggregate field accuracy < 90%.
"""

import hashlib
import json
import logging
import math
import re
import sys
from collections.abc import Callable
from pathlib import Path

from rapidfuzz import fuzz
from rich.console import Console
from rich.table import Table

import config
from llm import embed_texts
from graph import run_pipeline
from validation import parse_inr

logger = logging.getLogger(__name__)

FUZZY_FIELD_THRESHOLD = 60
FIELD_ACC_GATE = 0.90
# Combined summary score = SUMMARY_LEX_WEIGHT·lexical + (1-SUMMARY_LEX_WEIGHT)·semantic, on 0-1.
SUMMARY_LEX_WEIGHT = 0.5

# Keys whose values are identifiers/dates/amounts -> compared exactly, not fuzzily.
_EXACT_HINTS = (
    "date", "number", "id", "code", "amount", "price", "subtotal", "total",
    "budget", "ifsc", "account", "sow", "rate", "quantity",
)


def _norm(value: object) -> str:
    return " ".join(str(value).split()).lower()


def _is_exact_field(key: str) -> bool:
    return any(h in key.lower() for h in _EXACT_HINTS)


# Specific field paths (list indices stripped) forced to normalized-exact string match, beyond
# the key-hint list above. Path-based so we can target one field while a sibling with the same
# leaf key stays fuzzy (e.g. key_contacts.name exact, payment_milestones.name fuzzy).
_EXACT_PATHS = frozenset({
    # Vendor Contract
    "parties_and_dates.parties",
    "commercial_terms.contract_value",
    "legal.governing_law",
    # Support Ticket
    "ticket_metadata.submitted_by",
    "ticket_metadata.priority",
    "ticket_metadata.category",
    "ticket_metadata.affected_system",
    "ticket_metadata.assigned_to",
    "ticket_metadata.current_status",
    "resolution.resolved_by",
    "resolution.resolution_time",
    # Statement of Work
    "project_name",
    "client",
    "vendor",
    "payment_milestones.milestone",
    # key_contacts.role stays fuzzy: GT uses labels absent from the document (e.g. "Engagement
    # Manager"), so exact would penalise a correct prediction — the GT-label trap (FINDINGS §6).
    "key_contacts.name",
    "key_contacts.email",
    # Invoice
    "payment_terms",
    "payment_instructions.upi_or_email",
    "payment_instructions.bank",
})


def _is_exact_path(path: str) -> bool:
    return re.sub(r"\[\d+\]", "", path) in _EXACT_PATHS


def _compare_leaf(key: str, exp: object, pred: object, path: str = "") -> bool:
    if exp is None and pred is None:
        return True
    if exp is None or pred is None:
        return False
    e, p = _norm(exp), _norm(pred)
    if _is_exact_field(key):
        # Identifiers/money: compare numerically when both parse, else normalized string.
        ev, pv = parse_inr(str(exp)), parse_inr(str(pred))
        if ev is not None and pv is not None:
            return ev == pv
        return e.replace(" ", "") == p.replace(" ", "")
    if _is_exact_path(path):
        # Targeted fields: normalized string equality only (no numeric shortcut, so incidental
        # digits like a sector number can't false-match).
        return e.replace(" ", "") == p.replace(" ", "")
    # Free text: token_set handles reordering; partial_ratio handles subset/substring
    # (e.g. GT "30 days" vs the fuller, correct "30 days' prior written notice").
    return max(fuzz.token_set_ratio(e, p), fuzz.partial_ratio(e, p)) >= FUZZY_FIELD_THRESHOLD


def _jaccard(exp: list, pred: list, match: Callable[[object, object], bool]
             ) -> tuple[int, int, list[int]]:
    """One-to-one set overlap → (|intersection|, |union|, unmatched_exp_indices).

    Each predicted item may satisfy at most one GT item, so extra predicted items
    enlarge the union and lower the score. `match` decides item equality (fuzzy for
    prose lists, exact for tags). Score = |intersection| / |union|.
    """
    used: set[int] = set()
    intersection = 0
    unmatched: list[int] = []
    for i, ei in enumerate(exp):
        for j, pj in enumerate(pred):
            if j not in used and match(ei, pj):
                intersection += 1
                used.add(j)
                break
        else:
            unmatched.append(i)
    union = len(exp) + len(pred) - intersection
    return intersection, union, unmatched


def _tag_jaccard(exp_tags: list[str], pred_tags: list[str]) -> tuple[int, int]:
    """Tags scored by exact-match Jaccard (normalised, case-insensitive). Strict by design:
    `Net-30` == `net-30`, but synonyms (`saas` vs `annual-subscription`) do not match."""
    inter, union, _ = _jaccard(exp_tags, pred_tags, lambda a, b: _norm(a) == _norm(b))
    return inter, union


def _walk(exp: object, pred: object, key: str, path: str, misses: list[str]) -> tuple[int, int]:
    if isinstance(exp, dict):
        m = t = 0
        psub = pred if isinstance(pred, dict) else {}
        for k, v in exp.items():
            dm, dt = _walk(v, psub.get(k), k, f"{path}.{k}" if path else k, misses)
            m += dm
            t += dt
        return m, t
    if isinstance(exp, list):
        return _walk_list(exp, pred if isinstance(pred, list) else [], key, path, misses)
    matched = _compare_leaf(key, exp, pred, path)
    if not matched:
        misses.append(f"{path} (gt={exp!r} pred={pred!r})")
    return (1 if matched else 0), 1


def _walk_list(exp: list, pred: list, key: str, path: str, misses: list[str]) -> tuple[int, int]:
    if exp and isinstance(exp[0], dict):
        m = t = 0
        used: set[int] = set()
        for i, ei in enumerate(exp):
            best_j, best_ratio = None, -1.0
            for j, pj in enumerate(pred):
                if j in used:
                    continue
                dm, dt = _walk(ei, pj, key, "", [])
                ratio = dm / dt if dt else 0
                if ratio > best_ratio:
                    best_ratio, best_j = ratio, j
            if best_j is not None:
                used.add(best_j)
            dm, dt = _walk(ei, pred[best_j] if best_j is not None else None, key, f"{path}[{i}]", misses)
            m += dm
            t += dt
        return m, t
    # list of scalars -> Jaccard set overlap (fuzzy member match, see _jaccard).
    inter, union, unmatched = _jaccard(exp, pred, lambda a, b: _compare_leaf(key, a, b, path))
    for i in unmatched:
        misses.append(f"{path}[{i}] (gt={exp[i]!r})")
    return inter, union


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


_EMBED_CACHE_PATH = config.OUTPUT_DIR / ".embedding_cache.json"


def _embed_cached(texts: list[str], model: str) -> list[list[float]]:
    """Embed texts, reusing a content-addressed disk cache keyed by hash(model + text). The
    ground-truth summaries are constant, so they are embedded once and reused on every later run;
    unchanged predictions are reused too. Only cache-missing texts hit the API (one batched call)."""
    cache: dict[str, list[float]] = {}
    if _EMBED_CACHE_PATH.exists():
        cache = json.loads(_EMBED_CACHE_PATH.read_text(encoding="utf-8"))
    key = lambda t: hashlib.sha256(f"{model}\n{t}".encode()).hexdigest()  # noqa: E731
    misses = [t for t in texts if key(t) not in cache]
    if misses:
        for t, vec in zip(misses, embed_texts(misses, model=model)):
            cache[key(t)] = vec
        _EMBED_CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")
    return [cache[key(t)] for t in texts]


def _summary_semantic_sim(exp_summary: str, pred_summary: str) -> float | None:
    """Embedding cosine similarity of the two summaries (0-1). Returns None if embeddings
    are unavailable (no API key / offline) so a cached eval still runs — it is informational."""
    if not exp_summary or not pred_summary:
        return None
    try:
        gt_vec, pred_vec = _embed_cached([exp_summary, pred_summary], config.MODEL_EMBED)
    except Exception as exc:  # noqa: BLE001 — informational metric must never break the eval
        logger.warning("semantic summary similarity unavailable: %s", exc)
        return None
    return _cosine(gt_vec, pred_vec)


def _summary_score(exp_summary: str, pred_summary: str) -> tuple[float, float, float | None]:
    """One combined summary score on 0-1 = weighted blend of lexical (token_set_ratio) and
    semantic (embedding cosine) similarity. Returns (combined, lexical_0_100, semantic_0_1_or_None);
    falls back to lexical-only if embeddings are unavailable (offline / no key)."""
    lexical = float(fuzz.token_set_ratio(_norm(exp_summary), _norm(pred_summary)))  # 0-100
    semantic = _summary_semantic_sim(exp_summary, pred_summary)                     # 0-1 or None
    if semantic is None:
        return lexical / 100, lexical, None
    combined = SUMMARY_LEX_WEIGHT * (lexical / 100) + (1 - SUMMARY_LEX_WEIGHT) * semantic
    return combined, lexical, semantic


def _get_output(doc_name: str) -> dict:
    out_path = config.OUTPUT_DIR / f"{Path(doc_name).stem}.json"
    if out_path.exists():
        return json.loads(out_path.read_text(encoding="utf-8"))
    result = run_pipeline(str(config.SAMPLES_DIR / doc_name))
    out_path.write_text(json.dumps(result.model_dump(), indent=2, ensure_ascii=False),
                        encoding="utf-8")
    return result.model_dump()


def main() -> int:
    console = Console()
    ground_truth = json.loads(config.GROUND_TRUTH_PATH.read_text(encoding="utf-8"))

    table = Table(title="Evaluation vs ground truth")
    for col in ("Document", "Class", "Field acc", "Tag Jaccard", "Summary score"):
        table.add_column(col)

    class_correct = 0
    agg_m = agg_t = 0
    all_misses: dict[str, list[str]] = {}

    for doc_name, gt in ground_truth.items():
        out = _get_output(doc_name)

        class_ok = out["classification"]["document_type"] == gt["document_type"]
        class_correct += int(class_ok)

        misses: list[str] = []
        fm, ft = _walk(gt["extracted_fields"], out["extracted_fields"], "", "", misses)
        agg_m += fm
        agg_t += ft
        all_misses[doc_name] = misses

        tag_i, tag_u = _tag_jaccard(gt["tags"], out["tags"])
        summary_score, _, _ = _summary_score(gt["summary"], out["summary"])

        table.add_row(
            doc_name, "✓" if class_ok else "✗",
            f"{fm}/{ft} ({fm / ft:.0%})",
            f"{tag_i}/{tag_u} ({tag_i / tag_u:.0%})" if tag_u else "—",
            f"{summary_score:.2f}",
        )

    console.print(table)
    for doc_name, misses in all_misses.items():
        if misses:
            console.print(f"\n[yellow]{doc_name} missed fields:[/yellow]")
            for miss in misses:
                console.print(f"  • {miss}")

    class_acc = class_correct / len(ground_truth)
    field_acc = agg_m / agg_t if agg_t else 0.0
    console.print(f"\n[bold]Classification accuracy:[/bold] {class_acc:.0%}")
    console.print(f"[bold]Aggregate field accuracy:[/bold] {field_acc:.0%} ({agg_m}/{agg_t})")

    passed = class_acc >= 1.0 and field_acc >= FIELD_ACC_GATE
    console.print(f"[bold]{'PASS' if passed else 'FAIL'}[/bold] "
                  f"(gate: classification 100%, field accuracy {FIELD_ACC_GATE:.0%})")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
