"""Tests for engine_adapter case-normalization (Phase 1 ENUM-CASE close-out).

Closes audit finding ENUM-CASE: previously `_normalize_lowercase_enum`
was wired only for `investment_knowledge`; Bedrock-extracted real-PII
docs return capitalized + spaced values like "Growth and Income" for
the three `regulatory_*` engine Literals, which the engine boundary
silently rejected.

Per canon §9.4.5 the new `_normalize_regulatory_enum` helper raises on
unknown non-empty values rather than silently defaulting — surfaces
the gap to the advisor.
"""

from __future__ import annotations

import pytest
from web.api.engine_adapter import _normalize_regulatory_enum


class TestNormalizeRegulatoryEnum:
    """Unit tests for the strict regulatory-enum normalizer.

    Test pair shape per finding: (a) verify capitalized real-PII shape
    normalizes correctly, (b) verify unknown shape raises a structural
    error citing the field name + actual value (canon §9.4.5).
    """

    def test_normalizes_capitalized_regulatory_objective(self) -> None:
        # Bedrock returns "Growth and Income" from a KYC doc.
        result = _normalize_regulatory_enum(
            "Growth and Income",
            ("income", "growth_and_income", "growth"),
            "regulatory_objective",
        )
        assert result == "growth_and_income"

    def test_normalizes_capitalized_regulatory_time_horizon(self) -> None:
        # Time-horizon Literals don't have natural case variants
        # ("<3y", "3-10y", ">10y") but a doc may render them with
        # surrounding whitespace or in mixed positions.
        result = _normalize_regulatory_enum(
            "  3-10y  ",
            ("<3y", "3-10y", ">10y"),
            "regulatory_time_horizon",
        )
        assert result == "3-10y"

    def test_normalizes_capitalized_regulatory_risk_rating(self) -> None:
        result = _normalize_regulatory_enum(
            "Medium",
            ("low", "medium", "high"),
            "regulatory_risk_rating",
        )
        assert result == "medium"

    def test_empty_input_passes_through(self) -> None:
        # Per canon §9.4.5: never default to a value the AI didn't
        # extract. Empty stays empty; downstream Pydantic surfaces the
        # missing-required-field error.
        assert (
            _normalize_regulatory_enum(
                "",
                ("income", "growth_and_income", "growth"),
                "regulatory_objective",
            )
            == ""
        )
        assert (
            _normalize_regulatory_enum(
                None,
                ("income", "growth_and_income", "growth"),
                "regulatory_objective",
            )
            == ""
        )

    def test_raises_on_unknown_regulatory_value(self) -> None:
        # Bedrock returns something the engine doesn't accept; we want
        # a clean structural error citing the field + actual value, not
        # a silent default.
        with pytest.raises(ValueError) as excinfo:
            _normalize_regulatory_enum(
                "Aggressive Growth",
                ("income", "growth_and_income", "growth"),
                "regulatory_objective",
            )
        msg = str(excinfo.value)
        assert "regulatory_objective" in msg
        assert "Aggressive Growth" in msg
        assert "aggressive_growth" in msg  # the normalized form
        # Confirms canon §9.4.5: surfaces the gap, doesn't fabricate.

    def test_growth_alone_normalizes_unchanged(self) -> None:
        # "growth" is a valid value; verify single-word values pass.
        result = _normalize_regulatory_enum(
            "Growth",
            ("income", "growth_and_income", "growth"),
            "regulatory_objective",
        )
        assert result == "growth"
