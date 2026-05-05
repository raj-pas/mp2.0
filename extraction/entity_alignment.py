"""Cross-document entity alignment for MP2.0 fact reconciliation (P1.1).

Each Bedrock extraction emits facts with local indices (`people[0]`,
`accounts[0]`, `goals[0]`) scoped to the SOURCE DOCUMENT only. The same
real-world person, account, or goal can appear under different local
indices across docs (e.g. KYC says Alice = people[0]; statement says
Bob = people[0]). Without alignment, the field-keyed reconciliation
in `extraction.reconciliation.conflicts_for_facts` mistakes Alice and
Bob's distinct values for a single field as a CONFLICT.

This module performs greedy clustering across documents to assign each
(document, prefix, local_index) tuple a workspace-stable canonical
index. The reconciliation grouping then keys on the canonical field
(`people[<canonical_idx>].display_name`) instead of the raw field, so
distinct entities never collapse into a single conflict bucket.

Design (locked Round 13 #2 — TIGHTENED 2-field threshold):

    people: require TWO identifying fields for any merge
        - name token shared after normalize_key   -> +60
        - DOB exact ISO match                     -> +40
        - last-name exact match                   -> +30
        - last4 of an account number match        -> +25 (boost only)

      MERGE RULES
        * name (>=60) AND DOB (+40)                          = 100 -> MERGE
        * name (>=60) AND last-name (+30) AND last4 (+25)    >=115 -> MERGE
        * single-field score                                 -> NEW canonical

      The single-field rule is the LOAD-BEARING fail-safe: father+son who
      share a surname but lack DOB / account_number overlap stay distinct.

    accounts: redaction-safe hash on account_number anchors merges.
        - account_number exact (hashed)                    -> +100
        - (account_type, institution) match + single cand. -> +50
        - account_type + |current_value| within 5% + single -> +40
        Threshold: >=80.

    goals:
        - normalize_key(name) match                        -> +80
        - target_amount within 5% + time_horizon match     -> +50
        Threshold: >=80.

    Tie-break:
        Highest score wins. Ties go to the canonical with the most prior
        contributing documents. Ties of contributors break by lowest
        canonical id (stable, deterministic).

The module is pure-Python and contains NO Django / web / engine
imports. Returns an `EntityAlignment` value object whose
`align_facts(facts)` re-indexer rewrites each fact's `field` from
`prefix[local_index].suffix` to `prefix[canonical_index].suffix`.

Engine purity (canon §9.4.2): this module lives in `extraction/`, NOT
`engine/`. AI-numbers rule (canon §9.4.5): alignment NEVER invents
field values; only re-indexes existing facts. Real-PII discipline
(canon §11.8.3): account numbers are hashed via SHA-256 truncated to
16 hex chars BEFORE feature extraction, so account_number features
never carry raw PII inside the matcher.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Literal

from extraction.normalization import normalize_key

ENTITY_PREFIXES: tuple[str, ...] = ("people", "accounts", "goals")

# people: TIGHTENED 2-field threshold (Round 13 #2). See module docstring.
PEOPLE_THRESHOLD: int = 100
# accounts: account_number exact OR strong (type, institution, value) match.
ACCOUNTS_THRESHOLD: int = 80
# goals: name match OR (target+horizon) match.
GOALS_THRESHOLD: int = 80

# ---------------------------------------------------------------------------
# Tier-2 merge-candidate bands (Round 18 #1 — broad surface).
# Tier-1 thresholds above are UNCHANGED. Tier-2 bands sit STRICTLY BELOW the
# Tier-1 thresholds; pairs that score in these bands are surfaced to the
# advisor as merge candidates rather than auto-merged. Pairs with
# *contradicting* identity fields (different DOB / different last_name /
# different account_number_hash) are NEVER candidates regardless of score.
# ---------------------------------------------------------------------------
PEOPLE_TIER2_FLOOR: int = 60
PEOPLE_TIER2_CEILING: int = 99  # strictly below PEOPLE_THRESHOLD (100)
ACCOUNTS_TIER2_FLOOR: int = 50
ACCOUNTS_TIER2_CEILING: int = 79  # strictly below ACCOUNTS_THRESHOLD (80)
GOALS_TIER2_FLOOR: int = 50
GOALS_TIER2_CEILING: int = 79  # strictly below GOALS_THRESHOLD (80)

# Score weights — keep in sync with module docstring.
PEOPLE_SCORE_NAME_TOKEN = 60
PEOPLE_SCORE_DOB = 40
PEOPLE_SCORE_LAST_NAME = 30
PEOPLE_SCORE_LAST4_BOOST = 25

ACCOUNTS_SCORE_NUMBER_EXACT = 100
ACCOUNTS_SCORE_TYPE_INSTITUTION = 50
ACCOUNTS_SCORE_TYPE_VALUE_CLOSE = 40

GOALS_SCORE_NAME = 80
GOALS_SCORE_TARGET_HORIZON = 50

# Numeric closeness tolerance for account current_value + goal target_amount.
NUMERIC_CLOSE_PCT = 0.05  # 5%

_FIELD_RE = re.compile(r"^(?P<prefix>people|accounts|goals)\[(?P<index>\d+)\]\.(?P<suffix>.+)$")


# ---------------------------------------------------------------------------
# Public value-object types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _CanonicalEntity:
    """One entry in the workspace-scoped canonical entity table.

    `contributing_docs` is the set of unique document identifiers (any
    hashable, typically `document.id` or `document.original_filename`)
    that have contributed at least one fact to this canonical. Used as
    tie-break weight when scores collide.
    """

    canonical_index: int
    prefix: str
    features: dict[str, Any]
    contributing_docs: set[Any] = field(default_factory=set)


@dataclass(frozen=True)
class MergeCandidate:
    """Tier-2 merge candidate surfaced for advisor adjudication (Round 18 #1).

    Emitted by `_compute_merge_candidates` when a pair of canonical
    entities scores within the Tier-2 band (60-99 people, 50-79
    accounts/goals) AND has no contradicting identity field (different
    DOB / different last_name / different account_number_hash /
    different institution / different target_amount-with-same-horizon).

    Persisted to `reviewed_state['merge_candidates']` (JSON shape, per
    Round 18 #36); resolved via the
    `MergeCandidateResolveView` / `MergeCandidateBulkKeepSeparateView`
    endpoints. Real-PII discipline (canon §11.8.3): the dataclass holds
    only structural / non-PII fields — index integers, prefix string,
    score, matched/contradicting field-name tuples. Display name is
    surfaced separately at the JSON-shape boundary in `review_state.py`,
    not in the dataclass itself.
    """

    prefix: Literal["people", "accounts", "goals"]
    canonical_a_index: int
    canonical_b_index: int
    score: int  # 60-99 (people) or 50-79 (accounts/goals)
    matched_fields: tuple[str, ...]
    contradicting_fields: tuple[str, ...] = ()
    confidence: Literal["medium"] = "medium"


@dataclass(frozen=True)
class EntityAlignment:
    """Workspace-scoped alignment table.

    `mapping[(document_key, prefix, local_index)] -> canonical_index` is
    the load-bearing lookup; `canonical_entities` is the deduplicated
    list, indexed by canonical_index.

    `merge_candidates` (Round 18 #1) carries Tier-2 advisor-adjudication
    pairs — canonicals whose pairwise score landed below the Tier-1
    auto-merge threshold but above the Tier-2 floor and have no
    contradicting identity fields. Defaults to an empty tuple so older
    callers that ignore Tier-2 stay backwards-compatible.
    """

    mapping: dict[tuple[Any, str, int], int]
    canonical_entities: list[_CanonicalEntity]
    merge_candidates: tuple[MergeCandidate, ...] = field(default_factory=tuple)

    @property
    def canonical_count(self) -> int:
        return len(self.canonical_entities)

    def canonical_count_by_prefix(self) -> dict[str, int]:
        """Count of canonical entities per prefix (people/accounts/goals)."""
        counts: dict[str, int] = {p: 0 for p in ENTITY_PREFIXES}
        for entity in self.canonical_entities:
            counts[entity.prefix] = counts.get(entity.prefix, 0) + 1
        return counts

    def align_facts(self, facts: Iterable[Any]) -> list[Any]:
        """Re-index every fact whose field matches a known prefix.

        Mutates each fact's `field` attribute in-place when a mapping
        exists; returns the same list of facts (for convenience). Facts
        whose field does not match `(people|accounts|goals)[N].suffix`
        are passed through unchanged.

        Backwards-compat: if `mapping` is empty (e.g. the workspace had
        zero entity facts), this is a no-op pass-through.
        """
        result: list[Any] = []
        for fact in facts:
            new_field = self.aligned_field_for(fact)
            if new_field is not None and new_field != getattr(fact, "field", None):
                fact.field = new_field
            result.append(fact)
        return result

    def aligned_field_for(self, fact: Any) -> str | None:
        """Compute the aligned field path for a single fact.

        Returns None if the field doesn't carry a recognized prefix
        OR no mapping exists for the (document, prefix, local_index)
        triple.
        """
        field_str = str(getattr(fact, "field", "") or "")
        match = _FIELD_RE.match(field_str)
        if match is None:
            return None
        prefix = match.group("prefix")
        local_index = int(match.group("index"))
        suffix = match.group("suffix")
        document_key = _document_key(fact)
        canonical = self.mapping.get((document_key, prefix, local_index))
        if canonical is None:
            return None
        return f"{prefix}[{canonical}].{suffix}"

    def canonical_index_for(self, fact: Any) -> int | None:
        """Lookup helper: canonical index for the fact, or None."""
        field_str = str(getattr(fact, "field", "") or "")
        match = _FIELD_RE.match(field_str)
        if match is None:
            return None
        prefix = match.group("prefix")
        local_index = int(match.group("index"))
        document_key = _document_key(fact)
        return self.mapping.get((document_key, prefix, local_index))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def align_facts(facts: Iterable[Any]) -> EntityAlignment:
    """Compute the cross-document `EntityAlignment` for a workspace.

    Algorithm:
      1. Per (document, prefix, local_index), accumulate a feature dict
         from all facts that match that triple.
      2. Process triples in deterministic order — sort by document_key,
         then by prefix-rank (people, accounts, goals), then by local
         index. This guarantees `align_facts(facts)` returns the SAME
         canonical assignment regardless of input ordering, satisfying
         the determinism property test.
      3. For each triple, score it against every existing canonical
         entity for the same prefix. If the BEST score >= threshold,
         merge into that canonical (boost contributing_docs); otherwise
         allocate a new canonical_index.
      4. Single-fact-list edge cases:
           - empty list -> empty mapping, empty canonical list.
           - one document, N entities -> canonical_index === local_index.
           - one document, two distinct entities sharing only surname
             -> two canonical entities (single-field rejection).

    Note on the "field" attribute: each fact must expose `.field` (str)
    and ideally `.document.id` or `.document.original_filename` for
    document keying. If `.document` is None, the fact's id is used as
    a fallback document_key (so single-fact alignment works in tests).
    """
    triples = _build_feature_table(facts)

    canonical_entities: list[_CanonicalEntity] = []
    mapping: dict[tuple[Any, str, int], int] = {}

    # Iterate in deterministic order so the alignment is order-invariant
    # at the input level. (Property test: same set of facts in any order
    # -> same canonical assignment.)
    for triple_key in sorted(triples.keys(), key=_triple_sort_key):
        document_key, prefix, local_index = triple_key
        features = triples[triple_key]
        match_index = _best_match(prefix, features, canonical_entities)
        if match_index is None:
            new_index = _next_canonical_index(prefix, canonical_entities)
            canonical_entities.append(
                _CanonicalEntity(
                    canonical_index=new_index,
                    prefix=prefix,
                    features=dict(features),
                    contributing_docs={document_key},
                )
            )
            mapping[triple_key] = new_index
        else:
            mapping[triple_key] = match_index
            existing = next(
                e
                for e in canonical_entities
                if e.prefix == prefix and e.canonical_index == match_index
            )
            # Merge: union document set + fold in any new feature keys
            # WITHOUT overwriting existing values. Alignment NEVER
            # invents fields; existing values win (canon §9.4.5).
            existing.contributing_docs.add(document_key)
            for key, value in features.items():
                existing.features.setdefault(key, value)

    merge_candidates = _compute_merge_candidates(canonical_entities)
    return EntityAlignment(
        mapping=mapping,
        canonical_entities=canonical_entities,
        merge_candidates=merge_candidates,
    )


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------


def _build_feature_table(
    facts: Iterable[Any],
) -> dict[tuple[Any, str, int], dict[str, Any]]:
    """Group facts by (document, prefix, local_index) and assemble a
    feature dict per triple. The feature dict shape is per-prefix:

        people:   {name_tokens: set[str], last_name: str|None,
                   dob: str|None, account_last4: set[str]}
        accounts: {account_number_hash: str|None, account_type: str|None,
                   institution: str|None, current_value: float|None}
        goals:    {name_key: str|None, target_amount: float|None,
                   time_horizon_years: int|None}
    """
    triples: dict[tuple[Any, str, int], dict[str, Any]] = {}
    person_account_links: dict[Any, dict[int, set[str]]] = {}

    for fact in facts:
        field_str = str(getattr(fact, "field", "") or "")
        match = _FIELD_RE.match(field_str)
        if match is None:
            continue
        prefix = match.group("prefix")
        local_index = int(match.group("index"))
        suffix = match.group("suffix")
        document_key = _document_key(fact)
        triple_key = (document_key, prefix, local_index)
        bucket = triples.setdefault(triple_key, _empty_features_for(prefix))
        _absorb_fact(bucket, prefix, suffix, getattr(fact, "value", None))

        # Side-channel: cache last4 of account numbers per document so we
        # can boost people-merge scoring when the same person appears as
        # the holder of an account.
        if prefix == "accounts" and suffix == "account_number":
            value_str = _stringify(getattr(fact, "value", None))
            last4 = _last4_digits(value_str)
            if last4:
                doc_links = person_account_links.setdefault(document_key, {})
                # local_index here is the ACCOUNT local_index; we don't
                # know which person it links to without explicit holder
                # facts, so we associate it with the document and let
                # the scoring use any matching last4 in features.
                doc_links.setdefault(local_index, set()).add(last4)

    # Fold doc-level last4 into every people-feature bucket for that doc
    # — alignment is workspace-scoped and the simplest cross-doc signal
    # is "this household has account X4321 in doc A and person John in
    # doc A; doc B also references X4321 with person John -> boost".
    for triple_key, bucket in triples.items():
        document_key, prefix, _ = triple_key
        if prefix == "people":
            doc_accounts = person_account_links.get(document_key) or {}
            for last4_set in doc_accounts.values():
                bucket["account_last4"].update(last4_set)

    return triples


def _empty_features_for(prefix: str) -> dict[str, Any]:
    if prefix == "people":
        return {
            "name_tokens": set(),
            "last_name": None,
            "dob": None,
            "account_last4": set(),
        }
    if prefix == "accounts":
        return {
            "account_number_hash": None,
            "account_type": None,
            "institution": None,
            "current_value": None,
        }
    # goals
    return {
        "name_key": None,
        "target_amount": None,
        "time_horizon_years": None,
    }


def _absorb_fact(bucket: dict[str, Any], prefix: str, suffix: str, value: Any) -> None:
    """Mutate `bucket` in-place to absorb (suffix, value) into features."""
    if prefix == "people":
        if suffix in ("display_name", "name", "full_name"):
            value_str = _stringify(value)
            tokens = _name_tokens(value_str)
            bucket["name_tokens"].update(tokens)
            last_name = _last_name_token(value_str)
            if last_name and bucket["last_name"] is None:
                bucket["last_name"] = last_name
        elif suffix == "date_of_birth":
            iso = _iso_date(value)
            if iso and bucket["dob"] is None:
                bucket["dob"] = iso
        return

    if prefix == "accounts":
        if suffix == "account_number":
            number_str = _stringify(value)
            hashed = _hash_account_number(number_str)
            if hashed and bucket["account_number_hash"] is None:
                bucket["account_number_hash"] = hashed
        elif suffix == "account_type":
            type_key = normalize_key(_stringify(value))
            if type_key and bucket["account_type"] is None:
                bucket["account_type"] = type_key
        elif suffix == "institution":
            inst_key = normalize_key(_stringify(value))
            if inst_key and bucket["institution"] is None:
                bucket["institution"] = inst_key
        elif suffix in ("current_value", "market_value", "balance"):
            num = _maybe_float(value)
            if num is not None and bucket["current_value"] is None:
                bucket["current_value"] = num
        return

    # goals
    if suffix in ("name", "goal_name"):
        name_key = normalize_key(_stringify(value))
        if name_key and bucket["name_key"] is None:
            bucket["name_key"] = name_key
    elif suffix == "target_amount":
        num = _maybe_float(value)
        if num is not None and bucket["target_amount"] is None:
            bucket["target_amount"] = num
    elif suffix in ("time_horizon_years", "horizon_years", "time_horizon"):
        num = _maybe_int(value)
        if num is not None and bucket["time_horizon_years"] is None:
            bucket["time_horizon_years"] = num


# ---------------------------------------------------------------------------
# Scoring + matching
# ---------------------------------------------------------------------------


def _best_match(
    prefix: str,
    features: dict[str, Any],
    canonical_entities: list[_CanonicalEntity],
) -> int | None:
    """Return the canonical_index with the highest score >= threshold,
    or None if no candidate clears the bar.

    Tie-break (locked):
      1. Highest score wins.
      2. On equal score, canonical with MORE contributing_docs wins.
      3. On equal score AND equal contributing_docs, lowest canonical_index
         wins (deterministic).
    """
    threshold = _threshold_for(prefix)
    best: tuple[int, int, int] | None = None  # (score, contrib_count, -canonical_index)
    best_index: int | None = None

    for entity in canonical_entities:
        if entity.prefix != prefix:
            continue
        score = _score(prefix, features, entity.features)
        if score < threshold:
            continue
        ranking = (score, len(entity.contributing_docs), -entity.canonical_index)
        if best is None or ranking > best:
            best = ranking
            best_index = entity.canonical_index

    return best_index


def _score(
    prefix: str,
    new_features: dict[str, Any],
    canonical_features: dict[str, Any],
) -> int:
    if prefix == "people":
        return _score_people(new_features, canonical_features)
    if prefix == "accounts":
        return _score_accounts(new_features, canonical_features)
    return _score_goals(new_features, canonical_features)


def _score_people(new: dict[str, Any], existing: dict[str, Any]) -> int:
    """TIGHTENED 2-field threshold (Round 13 #2).

    Single-field score returns BELOW the people threshold; only true
    name+DOB or name+last-name+last4 combos clear the gate.
    """
    score = 0
    has_name_token = bool(new["name_tokens"] & existing["name_tokens"])
    if has_name_token:
        score += PEOPLE_SCORE_NAME_TOKEN

    has_dob = (
        new["dob"] is not None and existing["dob"] is not None and new["dob"] == existing["dob"]
    )
    if has_dob:
        score += PEOPLE_SCORE_DOB

    has_last_name = (
        new["last_name"] is not None
        and existing["last_name"] is not None
        and new["last_name"] == existing["last_name"]
    )
    if has_last_name:
        score += PEOPLE_SCORE_LAST_NAME

    has_last4 = bool(new["account_last4"] & existing["account_last4"])
    if has_last4:
        score += PEOPLE_SCORE_LAST4_BOOST

    # Single-field gate. We refuse to merge when ONLY the name token
    # matches — that is the father+son same-surname false-merge guard.
    field_count = sum(1 for ok in (has_name_token, has_dob, has_last_name, has_last4) if ok)
    if field_count < 2:
        return 0

    return score


def _score_accounts(new: dict[str, Any], existing: dict[str, Any]) -> int:
    score = 0
    if (
        new["account_number_hash"] is not None
        and existing["account_number_hash"] is not None
        and new["account_number_hash"] == existing["account_number_hash"]
    ):
        score += ACCOUNTS_SCORE_NUMBER_EXACT

    if (
        new["account_type"]
        and existing["account_type"]
        and new["account_type"] == existing["account_type"]
        and new["institution"]
        and existing["institution"]
        and new["institution"] == existing["institution"]
    ):
        score += ACCOUNTS_SCORE_TYPE_INSTITUTION

    if (
        new["account_type"]
        and existing["account_type"]
        and new["account_type"] == existing["account_type"]
        and _values_close(new["current_value"], existing["current_value"], NUMERIC_CLOSE_PCT)
    ):
        score += ACCOUNTS_SCORE_TYPE_VALUE_CLOSE

    return score


def _score_goals(new: dict[str, Any], existing: dict[str, Any]) -> int:
    score = 0
    if new["name_key"] and existing["name_key"] and new["name_key"] == existing["name_key"]:
        score += GOALS_SCORE_NAME

    if (
        new["time_horizon_years"] is not None
        and existing["time_horizon_years"] is not None
        and new["time_horizon_years"] == existing["time_horizon_years"]
        and _values_close(new["target_amount"], existing["target_amount"], NUMERIC_CLOSE_PCT)
    ):
        score += GOALS_SCORE_TARGET_HORIZON

    return score


def _threshold_for(prefix: str) -> int:
    return {
        "people": PEOPLE_THRESHOLD,
        "accounts": ACCOUNTS_THRESHOLD,
        "goals": GOALS_THRESHOLD,
    }[prefix]


# ---------------------------------------------------------------------------
# Tier-2 merge-candidate emission (Round 18 #1).
#
# After Tier-1 greedy clustering completes, scan every same-prefix pair
# of canonical entities. Pairs that score in the Tier-2 band AND carry
# NO contradicting identity field become merge candidates the advisor
# adjudicates. This is purely additive — Tier-1 thresholds are
# unchanged (Round 13 #2 LOCKED).
# ---------------------------------------------------------------------------


_TIER2_BAND: dict[str, tuple[int, int]] = {
    "people": (PEOPLE_TIER2_FLOOR, PEOPLE_TIER2_CEILING),
    "accounts": (ACCOUNTS_TIER2_FLOOR, ACCOUNTS_TIER2_CEILING),
    "goals": (GOALS_TIER2_FLOOR, GOALS_TIER2_CEILING),
}


def _compute_merge_candidates(
    canonical_entities: list[_CanonicalEntity],
) -> tuple[MergeCandidate, ...]:
    """Pairwise-scan canonicals; emit Tier-2 candidates per Round 18 #1.

    For each unordered same-prefix pair (a, b) where a.canonical_index <
    b.canonical_index, score the pair with a Tier-2-specific scorer
    that mirrors the field-weights of `_score` BUT does NOT apply the
    Tier-1 single-field rejection gate (which is what makes weak
    matches drop to 0). Emit a `MergeCandidate` iff:

    1. score lies in the prefix's Tier-2 band (e.g. 60..99 for people).
       Pairs that would Tier-1-auto-merge under the un-gated scorer
       still land at >= the Tier-1 threshold, so the band ceiling
       (one less than the Tier-1 threshold) excludes them. Tier-1 + Tier-2
       are disjoint on any single pair.
    2. no contradicting identity field is present on either canonical
       (different DOB, different last_name, different
       account_number_hash, different institution, different
       target_amount-with-same-horizon — see the per-prefix contradicts
       helpers). A contradiction signals "definitely different
       entities" regardless of how strong other signals are.

    The resulting tuple is deterministically ordered:
      score DESC, canonical_a_index ASC, canonical_b_index ASC.
    Highest-confidence candidates surface first.
    """
    candidates: list[MergeCandidate] = []
    for prefix, (floor, ceiling) in _TIER2_BAND.items():
        same_prefix = sorted(
            (e for e in canonical_entities if e.prefix == prefix),
            key=lambda e: e.canonical_index,
        )
        for i, a in enumerate(same_prefix):
            for b in same_prefix[i + 1 :]:
                contradictions = _contradicts_for_prefix(prefix, a.features, b.features)
                if contradictions:
                    continue
                score = _score_tier2(prefix, a.features, b.features)
                if score < floor or score > ceiling:
                    continue
                matched = _matched_fields_for_prefix(prefix, a.features, b.features)
                candidates.append(
                    MergeCandidate(
                        prefix=prefix,  # type: ignore[arg-type]
                        canonical_a_index=a.canonical_index,
                        canonical_b_index=b.canonical_index,
                        score=score,
                        matched_fields=matched,
                        contradicting_fields=(),
                        confidence="medium",
                    )
                )
    candidates.sort(key=lambda c: (-c.score, c.canonical_a_index, c.canonical_b_index))
    return tuple(candidates)


def _score_tier2(
    prefix: str, features_a: dict[str, Any], features_b: dict[str, Any]
) -> int:
    """Score a candidate pair WITHOUT Tier-1's single-field rejection gate.

    For people: identical to `_score_people` but with the `field_count
    < 2` early-return removed. The Tier-1 gate is what makes single-name
    matches return 0 and thus stay separate; Tier-2 needs to *surface*
    those exact pairs for advisor adjudication.

    For accounts and goals: the existing scorer has no single-field gate
    and works as-is, so we delegate.
    """
    if prefix == "people":
        score = 0
        if features_a.get("name_tokens") and features_b.get("name_tokens"):
            if features_a["name_tokens"] & features_b["name_tokens"]:
                score += PEOPLE_SCORE_NAME_TOKEN
        if (
            features_a.get("dob")
            and features_b.get("dob")
            and features_a["dob"] == features_b["dob"]
        ):
            score += PEOPLE_SCORE_DOB
        if (
            features_a.get("last_name")
            and features_b.get("last_name")
            and features_a["last_name"] == features_b["last_name"]
        ):
            score += PEOPLE_SCORE_LAST_NAME
        a_last4 = set(features_a.get("account_last4") or set())
        b_last4 = set(features_b.get("account_last4") or set())
        if a_last4 and b_last4 and (a_last4 & b_last4):
            score += PEOPLE_SCORE_LAST4_BOOST
        return score
    return _score(prefix, features_a, features_b)


def _contradicts_for_prefix(
    prefix: str, features_a: dict[str, Any], features_b: dict[str, Any]
) -> tuple[str, ...]:
    if prefix == "people":
        return _contradicts_for_people(features_a, features_b)
    if prefix == "accounts":
        return _contradicts_for_accounts(features_a, features_b)
    return _contradicts_for_goals(features_a, features_b)


def _contradicts_for_people(
    features_a: dict[str, Any], features_b: dict[str, Any]
) -> tuple[str, ...]:
    """Identity contradictions for people canonicals.

    Signals "definitely different real-world humans": both have a DOB
    and they differ; both have a last_name and they differ; both have
    an account_number_hash on file (via account_last4 overlap) and they
    fully disagree.
    """
    contradictions: list[str] = []
    if features_a.get("dob") and features_b.get("dob") and features_a["dob"] != features_b["dob"]:
        contradictions.append("dob")
    if (
        features_a.get("last_name")
        and features_b.get("last_name")
        and features_a["last_name"] != features_b["last_name"]
    ):
        contradictions.append("last_name")
    a_last4 = set(features_a.get("account_last4") or set())
    b_last4 = set(features_b.get("account_last4") or set())
    if a_last4 and b_last4 and not (a_last4 & b_last4):
        # Both canonicals have last4 evidence and NONE overlap — different
        # account holders. (Partial overlap is not a contradiction; that's
        # joint accounts / shared family financial picture.)
        contradictions.append("account_last4")
    return tuple(contradictions)


def _contradicts_for_accounts(
    features_a: dict[str, Any], features_b: dict[str, Any]
) -> tuple[str, ...]:
    """Identity contradictions for account canonicals.

    Signals "definitely different accounts": both have an
    account_number_hash and they differ; both have an institution and
    the institutions differ.
    """
    contradictions: list[str] = []
    if (
        features_a.get("account_number_hash")
        and features_b.get("account_number_hash")
        and features_a["account_number_hash"] != features_b["account_number_hash"]
    ):
        contradictions.append("account_number_hash")
    if (
        features_a.get("institution")
        and features_b.get("institution")
        and features_a["institution"] != features_b["institution"]
    ):
        contradictions.append("institution")
    return tuple(contradictions)


def _contradicts_for_goals(
    features_a: dict[str, Any], features_b: dict[str, Any]
) -> tuple[str, ...]:
    """Identity contradictions for goal canonicals.

    Signals "definitely different goals": both have a time_horizon AND
    a target_amount; horizons match BUT target_amounts are not close
    (>5% apart). When two goals have the same horizon, divergent
    targets are a strong "different goal" signal.
    """
    contradictions: list[str] = []
    a_horizon = features_a.get("time_horizon_years")
    b_horizon = features_b.get("time_horizon_years")
    a_target = features_a.get("target_amount")
    b_target = features_b.get("target_amount")
    if (
        a_horizon is not None
        and b_horizon is not None
        and a_horizon == b_horizon
        and a_target is not None
        and b_target is not None
        and not _values_close(a_target, b_target, NUMERIC_CLOSE_PCT)
    ):
        contradictions.append("target_amount")
    return tuple(contradictions)


def _matched_fields_for_prefix(
    prefix: str, features_a: dict[str, Any], features_b: dict[str, Any]
) -> tuple[str, ...]:
    """Which signals carried the Tier-2 score? Used for advisor display."""
    if prefix == "people":
        matched: list[str] = []
        if features_a.get("name_tokens") and features_b.get("name_tokens"):
            if features_a["name_tokens"] & features_b["name_tokens"]:
                matched.append("name_token")
        if (
            features_a.get("dob")
            and features_b.get("dob")
            and features_a["dob"] == features_b["dob"]
        ):
            matched.append("dob")
        if (
            features_a.get("last_name")
            and features_b.get("last_name")
            and features_a["last_name"] == features_b["last_name"]
        ):
            matched.append("last_name")
        a_last4 = set(features_a.get("account_last4") or set())
        b_last4 = set(features_b.get("account_last4") or set())
        if a_last4 and b_last4 and (a_last4 & b_last4):
            matched.append("account_last4")
        return tuple(matched)
    if prefix == "accounts":
        matched_acc: list[str] = []
        if (
            features_a.get("account_number_hash")
            and features_b.get("account_number_hash")
            and features_a["account_number_hash"] == features_b["account_number_hash"]
        ):
            matched_acc.append("account_number_hash")
        if (
            features_a.get("account_type")
            and features_b.get("account_type")
            and features_a["account_type"] == features_b["account_type"]
        ):
            matched_acc.append("account_type")
        if (
            features_a.get("institution")
            and features_b.get("institution")
            and features_a["institution"] == features_b["institution"]
        ):
            matched_acc.append("institution")
        if _values_close(
            features_a.get("current_value"), features_b.get("current_value"), NUMERIC_CLOSE_PCT
        ):
            matched_acc.append("current_value_close")
        return tuple(matched_acc)
    # goals
    matched_g: list[str] = []
    if (
        features_a.get("name_key")
        and features_b.get("name_key")
        and features_a["name_key"] == features_b["name_key"]
    ):
        matched_g.append("name_key")
    if (
        features_a.get("time_horizon_years") is not None
        and features_b.get("time_horizon_years") is not None
        and features_a["time_horizon_years"] == features_b["time_horizon_years"]
        and _values_close(
            features_a.get("target_amount"), features_b.get("target_amount"), NUMERIC_CLOSE_PCT
        )
    ):
        matched_g.append("target_horizon_close")
    return tuple(matched_g)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_PREFIX_RANK: dict[str, int] = {prefix: i for i, prefix in enumerate(ENTITY_PREFIXES)}


def _triple_sort_key(triple: tuple[Any, str, int]) -> tuple[str, int, int]:
    document_key, prefix, local_index = triple
    return (str(document_key), _PREFIX_RANK.get(prefix, 99), local_index)


def _next_canonical_index(prefix: str, entities: list[_CanonicalEntity]) -> int:
    used = {e.canonical_index for e in entities if e.prefix == prefix}
    n = 0
    while n in used:
        n += 1
    return n


def _document_key(fact: Any) -> Any:
    document = getattr(fact, "document", None)
    if document is not None:
        doc_id = getattr(document, "id", None)
        if doc_id is not None:
            return doc_id
        filename = getattr(document, "original_filename", None)
        if filename:
            return filename
    # Fallback so single-doc unit tests with no `.document` still group
    # facts under a stable key. We deliberately do NOT fall back to id(fact)
    # because that would split two facts from the same source into
    # different docs.
    document_id = getattr(fact, "document_id", None)
    if document_id is not None:
        return document_id
    return None


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _name_tokens(value: str) -> set[str]:
    """Lowercased alphanumeric tokens, with length >= 2 to skip
    initials like "J." that frequently match across unrelated people."""
    tokens = {tok for tok in re.split(r"[^a-z0-9]+", value.lower()) if len(tok) >= 2}
    return tokens


def _last_name_token(value: str) -> str | None:
    tokens = [tok for tok in re.split(r"[^a-z0-9]+", value.lower()) if len(tok) >= 2]
    if not tokens:
        return None
    return tokens[-1]


def _iso_date(value: Any) -> str | None:
    """Best-effort ISO-date normalization. Returns YYYY-MM-DD or None."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        try:
            iso = value.isoformat()
            if isinstance(iso, str) and len(iso) >= 10:
                return iso[:10]
        except Exception:
            return None
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T.*", text):
        return text[:10]
    return None


def _hash_account_number(value: str) -> str | None:
    """SHA-256 hex of the digit-stripped account number, truncated to
    16 hex chars. Real-PII discipline: the matcher never sees raw
    account numbers."""
    digits = re.sub(r"[^0-9]", "", value)
    if not digits:
        return None
    return hashlib.sha256(digits.encode("utf-8")).hexdigest()[:16]


def _last4_digits(value: str) -> str | None:
    digits = re.sub(r"[^0-9]", "", value)
    if len(digits) < 4:
        return None
    return digits[-4:]


def _maybe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        try:
            cleaned = re.sub(r"[^0-9.\-]", "", str(value))
            if not cleaned or cleaned in ("-", ".", "-."):
                return None
            return float(cleaned)
        except (TypeError, ValueError):
            return None


def _maybe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        match = re.search(r"-?\d+", str(value))
        if match:
            try:
                return int(match.group(0))
            except ValueError:
                return None
        return None


def _values_close(a: float | None, b: float | None, pct: float) -> bool:
    if a is None or b is None:
        return False
    if a == 0 and b == 0:
        return True
    denominator = max(abs(a), abs(b))
    if denominator == 0:
        return False
    return abs(a - b) / denominator <= pct


__all__ = [
    "ENTITY_PREFIXES",
    "PEOPLE_THRESHOLD",
    "ACCOUNTS_THRESHOLD",
    "GOALS_THRESHOLD",
    "PEOPLE_TIER2_FLOOR",
    "PEOPLE_TIER2_CEILING",
    "ACCOUNTS_TIER2_FLOOR",
    "ACCOUNTS_TIER2_CEILING",
    "GOALS_TIER2_FLOOR",
    "GOALS_TIER2_CEILING",
    "EntityAlignment",
    "MergeCandidate",
    "align_facts",
]
