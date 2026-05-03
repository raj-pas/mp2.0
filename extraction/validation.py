"""Phase 9 — Inferred-fact evidence-quote validation.

Phase 4 + Phase 9.1 + 9.2 calibrate Bedrock toward extracting
explicit facts and avoiding fabrication. Phase 9.3 closes the
remaining loophole: when Bedrock emits a fact with
``derivation_method="inferred"``, we require the ``evidence_quote``
to actually appear in the source document. Inferred facts whose
quote does not substring-overlap the source text are dropped — they
are the most common hallucination class (model invents a quote to
support a fabricated value).

The validator is intentionally lenient on whitespace and
punctuation so legitimate inferred facts still pass:

  - Both source text and evidence_quote are normalized to lowercase,
    runs of whitespace collapsed, and most punctuation stripped.
  - We require ≥60% character overlap (longest common substring
    ratio) instead of exact substring match — Bedrock often drops a
    leading or trailing label fragment.
  - Empty quote → fail (canon §11.4 inferred facts must cite source).

Extracted facts (``derivation_method="extracted"``) are NOT
validated here — they're already constrained by the tool-use
schema + per-type prompts. Only inferred facts go through this
gate.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from extraction.schemas import FactCandidate

__all__ = [
    "EVIDENCE_OVERLAP_THRESHOLD",
    "filter_inferred_facts_by_evidence",
    "validate_fact_evidence_quote",
]

# Minimum character-overlap ratio required for inferred facts. Set to
# 0.6 after Phase 9 design: Bedrock often emits a quote that's a
# short substring of a longer source line + an extra label prefix
# (e.g., quote "client age 58" on source line "Per ID review: client
# age 58"). 0.6 still passes those; 0.8 drops too many legitimate
# cases. Re-tune after sweep data accumulates.
EVIDENCE_OVERLAP_THRESHOLD = 0.6

_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+", re.UNICODE)


def _normalize(text: str) -> str:
    """Lowercase + strip punctuation + collapse whitespace.

    Inferred-fact evidence overlap is judged on normalized text so
    minor punctuation differences (smart quotes, em-dashes) don't
    cause false-rejects. Pure structural similarity is what we care
    about.
    """
    if not text:
        return ""
    lowered = text.lower()
    no_punct = _PUNCTUATION_RE.sub(" ", lowered)
    return _WHITESPACE_RE.sub(" ", no_punct).strip()


def _longest_common_substring_ratio(quote: str, source: str) -> float:
    """Best contiguous overlap of ``quote`` inside ``source``, ratio.

    Returns the length of the longest contiguous substring of
    ``quote`` that also appears in ``source``, divided by len(quote).
    Bounded in [0.0, 1.0]. Empty inputs return 0.0.

    Implementation: dynamic-programming LCS over normalized strings.
    O(len(quote) * len(source)) time, O(min(len(quote), len(source)))
    space using the rolling-row pattern. Quotes are bounded to 240
    chars by the schema and source documents are typically <120K
    chars after the text_max_chars cap, so the worst case is well
    under 30M ops — dominated by the Bedrock call latency anyway.
    """
    if not quote or not source:
        return 0.0
    q = _normalize(quote)
    s = _normalize(source)
    if not q or not s:
        return 0.0
    if q in s:
        return 1.0
    n_q = len(q)
    n_s = len(s)
    prev = [0] * (n_s + 1)
    best = 0
    for i in range(1, n_q + 1):
        cur = [0] * (n_s + 1)
        for j in range(1, n_s + 1):
            if q[i - 1] == s[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best / n_q


def validate_fact_evidence_quote(fact: FactCandidate, parsed_text: str) -> bool:
    """True if the fact's evidence_quote is supported by parsed_text.

    Only inferred facts go through this gate. Extracted facts pass
    through unconditionally (they're already schema-constrained). An
    empty source text always passes — happens for vision-path facts
    where parsed_text is "" because the PDF rendered through the
    document content block (Bedrock processes the image directly).
    The vision path's quote validity is anchored by the model's own
    OCR of the image; we cannot character-match against an image.
    """
    if fact.derivation_method != "inferred":
        return True
    if not parsed_text or not parsed_text.strip():
        return True
    if not fact.evidence_quote or not fact.evidence_quote.strip():
        return False
    ratio = _longest_common_substring_ratio(fact.evidence_quote, parsed_text)
    return ratio >= EVIDENCE_OVERLAP_THRESHOLD


def filter_inferred_facts_by_evidence(
    facts: list[FactCandidate],
    parsed_text: str,
    *,
    extraction_run_id: str = "",
) -> tuple[list[FactCandidate], list[FactCandidate]]:
    """Split facts into (kept, dropped) based on evidence-quote overlap.

    Dropped facts are persisted (when ``MP20_DEBUG_BEDROCK_RESPONSES=1``
    and a secure root is configured) for audit / threshold tuning.
    The on-disk dump captures only the structural shape of the drop
    (field path, derivation method, confidence, overlap ratio) — the
    quote text itself stays inside the secure root, never the repo.
    """
    kept: list[FactCandidate] = []
    dropped: list[FactCandidate] = []
    for fact in facts:
        if validate_fact_evidence_quote(fact, parsed_text):
            kept.append(fact)
        else:
            dropped.append(fact)
    if dropped:
        _maybe_log_dropped(dropped, extraction_run_id, parsed_text)
    return kept, dropped


def _maybe_log_dropped(
    dropped: list[FactCandidate],
    extraction_run_id: str,
    parsed_text: str,
) -> None:
    """Audit-log dropped facts inside MP20_SECURE_DATA_ROOT/_debug/.

    Gated on ``MP20_DEBUG_BEDROCK_RESPONSES=1`` to avoid disk writes
    in production. Real-PII discipline: the raw quote text MAY
    include client values; the debug dir is treated as PII storage
    and never leaves the secure root.
    """
    if os.getenv("MP20_DEBUG_BEDROCK_RESPONSES") != "1":
        return
    secure_root = os.environ.get("MP20_SECURE_DATA_ROOT")
    if not secure_root:
        return
    debug_dir = Path(secure_root) / "_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    safe_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", extraction_run_id)[:80] or "unknown"
    timestamp = int(time.time() * 1000)
    target = debug_dir / f"{safe_id}-evidence-drops-{timestamp}.txt"
    rows = [
        f"# Source text length: {len(parsed_text)} chars",
        f"# Dropped fact count: {len(dropped)}",
        "",
    ]
    for fact in dropped:
        ratio = _longest_common_substring_ratio(fact.evidence_quote, parsed_text)
        rows.append(
            f"field={fact.field} confidence={fact.confidence} "
            f"derivation={fact.derivation_method} overlap={ratio:.2f} "
            f"quote_len={len(fact.evidence_quote)}"
        )
    target.write_text("\n".join(rows), encoding="utf-8")
