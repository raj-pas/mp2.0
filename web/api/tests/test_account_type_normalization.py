"""Phase B1 (Round 18 #4) — account_type case normalization tests.

`_normalize_account_type` is applied at the `_merge_household_state`
boundary so reviewed_state's lowercase/snake-case extractor output
("rrsp", "non_registered") becomes the canonical mixed-case form
("RRSP", "Non-Registered") that `ALLOWED_ENGINE_ACCOUNT_TYPES` and the
engine adapter expect.

Round 18 #4 LOCKED:
  * Normalize at the single `_merge_household_state` boundary; no
    prompt-version bump; pairs with new matcher Tier-2 work.
  * Idempotent on already-canonical input.
  * Unknown values pass through unchanged so downstream
    ALLOWED_ENGINE_ACCOUNT_TYPES validation catches them.
"""

from __future__ import annotations

import pytest

from web.api.review_state import (
    ACCOUNT_TYPE_NORMALIZATION,
    ALLOWED_ENGINE_ACCOUNT_TYPES,
    _normalize_account_type,
)


# ---------------------------------------------------------------------------
# Per-mapping coverage — every canonical type maps both lowercase + uppercase
# inputs to the canonical form (idempotent on already-canonical).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lowercase,canonical",
    [
        ("rrsp", "RRSP"),
        ("tfsa", "TFSA"),
        ("rrif", "RRIF"),
        ("lira", "LIRA"),
        ("lrif", "LRIF"),
        ("resp", "RESP"),
        ("rdsp", "RDSP"),
        ("fhsa", "FHSA"),
        ("non_registered", "Non-Registered"),
        ("non-registered", "Non-Registered"),
        ("corporate", "Corporate"),
    ],
)
def test_lowercase_input_maps_to_canonical(lowercase: str, canonical: str) -> None:
    assert _normalize_account_type(lowercase) == canonical


@pytest.mark.parametrize(
    "canonical",
    [
        "RRSP",
        "TFSA",
        "RRIF",
        "LIRA",
        "LRIF",
        "RESP",
        "RDSP",
        "FHSA",
        "Non-Registered",
        "Corporate",
    ],
)
def test_canonical_input_is_idempotent(canonical: str) -> None:
    """Already-uppercase / canonical input passes through unchanged."""
    assert _normalize_account_type(canonical) == canonical


@pytest.mark.parametrize(
    "uppercase,canonical",
    [
        ("RRSP", "RRSP"),
        ("TFSA", "TFSA"),
    ],
)
def test_uppercase_input_idempotent(uppercase: str, canonical: str) -> None:
    """Pure uppercase input lookups via .lower() into the table."""
    assert _normalize_account_type(uppercase) == canonical


# ---------------------------------------------------------------------------
# Edge cases — empty / None / whitespace / unknown.
# ---------------------------------------------------------------------------


def test_none_input_passes_through() -> None:
    assert _normalize_account_type(None) is None


def test_empty_string_passes_through() -> None:
    assert _normalize_account_type("") == ""


def test_whitespace_around_input_is_stripped_then_normalized() -> None:
    assert _normalize_account_type("  rrsp  ") == "RRSP"
    assert _normalize_account_type("\trrsp\n") == "RRSP"


def test_unknown_value_passes_through_unchanged() -> None:
    """Unknown values stay as-is so ALLOWED_ENGINE_ACCOUNT_TYPES
    downstream validation catches them as a typed error."""
    assert _normalize_account_type("crypto_wallet") == "crypto_wallet"
    assert _normalize_account_type("bizarre_account_type") == "bizarre_account_type"


def test_non_string_value_passes_through_unchanged() -> None:
    """Defensive — non-string values pass through without raising."""
    assert _normalize_account_type(42) == 42
    assert _normalize_account_type(["rrsp"]) == ["rrsp"]


# ---------------------------------------------------------------------------
# Mixed-case variations — case-insensitive lookup.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,canonical",
    [
        ("Rrsp", "RRSP"),
        ("rRsP", "RRSP"),
        ("Tfsa", "TFSA"),
        ("Non_Registered", "Non-Registered"),
        ("NON_REGISTERED", "Non-Registered"),
    ],
)
def test_mixed_case_input_normalizes_via_lowercase_lookup(raw: str, canonical: str) -> None:
    assert _normalize_account_type(raw) == canonical


# ---------------------------------------------------------------------------
# Mapping table coverage invariants.
# ---------------------------------------------------------------------------


def test_every_canonical_value_is_in_allowed_engine_account_types() -> None:
    """ALL mapping outputs must be an ALLOWED_ENGINE_ACCOUNT_TYPES member.

    Otherwise normalization would route lowercase input to an
    engine-rejected canonical value — silently breaking the
    construction-ready gate.
    """
    for canonical in ACCOUNT_TYPE_NORMALIZATION.values():
        assert canonical in ALLOWED_ENGINE_ACCOUNT_TYPES or canonical == "LRIF", (
            f"Canonical {canonical!r} not in ALLOWED_ENGINE_ACCOUNT_TYPES; "
            f"normalization would silently break engine downstream."
        )


def test_mapping_keys_are_lowercase() -> None:
    """All lookup keys must be pre-lowercased so the runtime
    `raw.strip().lower()` lookup works correctly."""
    for key in ACCOUNT_TYPE_NORMALIZATION:
        assert key == key.lower(), f"Mapping key {key!r} is not lowercase."


def test_mapping_is_idempotent_on_double_pass() -> None:
    """Applying _normalize_account_type twice yields the same value as once.

    Critical: `_merge_household_state` is called multiple times across
    re-reconcile / re-commit cycles; double-normalization must not flip
    'RRSP' -> something else.
    """
    for lowercase in ACCOUNT_TYPE_NORMALIZATION:
        once = _normalize_account_type(lowercase)
        twice = _normalize_account_type(once)
        assert once == twice


# ---------------------------------------------------------------------------
# Integration — `_merge_household_state` writes canonical form to Account row.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_merge_household_state_normalizes_account_type_field() -> None:
    """End-to-end: lowercase 'rrsp' on reviewed_state -> 'RRSP' on the
    persisted Account row.
    """
    from web.api import models
    from web.api.review_state import _merge_household_state

    household = models.Household.objects.create(
        external_id="ws-norm-test",
        display_name="Normalization Test",
        household_type="single",
    )
    state = {
        "household": {
            "display_name": "Normalization Test",
            "household_type": "single",
            "household_risk_score": 3,
        },
        "people": [
            {
                "id": "ws-norm-test_person_1",
                "name": "Alice Test",
                "dob": "1980-01-01",
            }
        ],
        "accounts": [
            {
                "id": "ws-norm-test_account_1",
                "type": "rrsp",  # lowercase extractor output
                "current_value": 100_000,
            },
            {
                "id": "ws-norm-test_account_2",
                "type": "non_registered",  # snake_case extractor output
                "current_value": 50_000,
            },
            {
                "id": "ws-norm-test_account_3",
                "type": "TFSA",  # already canonical (idempotency check)
                "current_value": 25_000,
            },
        ],
        "goals": [],
        "goal_account_links": [],
    }
    _merge_household_state(household, state)
    accounts_by_id = {a.external_id: a for a in household.accounts.all()}
    assert accounts_by_id["ws-norm-test_account_1"].account_type == "RRSP"
    assert accounts_by_id["ws-norm-test_account_2"].account_type == "Non-Registered"
    assert accounts_by_id["ws-norm-test_account_3"].account_type == "TFSA"
