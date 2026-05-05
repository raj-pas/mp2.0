"""Plan v20 §A1.36 (P8) — every ``Readiness.missing[]`` row carries a
canonical ``field_path`` so the frontend P3.3 inline-fix CTA can deep-link
to the affected field.

Field-path conventions match ``extraction/prompts/base.py``
``CANONICAL_FIELD_INVENTORY``: ``household.<field>``, ``people[N].<field>``,
``accounts[N].<field>``, ``goals[N].<field>``, ``goal_account_links[N].<field>``,
``risk.<field>``.

Backwards-compat (sister §3.16): pre-tag households without ``field_path``
must continue to render. Frontend treats the empty-string field_path as
"no inline-fix CTA available".
"""

from __future__ import annotations

from web.api.review_state import readiness_for_state


def _state_missing_section(*, drop: str) -> dict:
    """A baseline engine_ready state with one section deliberately broken."""
    state = {
        "household": {
            "display_name": "Field Path Test",
            "household_type": "couple",
            "household_risk_score": 3,
        },
        "people": [{"id": "person_1", "name": "Lead Member", "age": 60}],
        "accounts": [
            {
                "id": "acct_1",
                "type": "RRSP",
                "current_value": 100000,
                "missing_holdings_confirmed": True,
                "is_held_at_purpose": True,
            }
        ],
        "goals": [
            {
                "id": "goal_1",
                "name": "Retirement",
                "time_horizon_years": 5,
                "goal_risk_score": 3,
            }
        ],
        "goal_account_links": [
            {"goal_id": "goal_1", "account_id": "acct_1", "allocated_amount": 100000}
        ],
        "risk": {"household_score": 3},
    }

    if drop == "household.display_name":
        state["household"]["display_name"] = ""
    elif drop == "household.household_type":
        state["household"]["household_type"] = "neither"
    elif drop == "people.empty":
        state["people"] = []
    elif drop == "people[0].date_of_birth":
        state["people"] = [{"id": "person_1", "name": "Lead"}]
    elif drop == "accounts.empty":
        state["accounts"] = []
    elif drop == "accounts[0].current_value":
        state["accounts"][0]["current_value"] = 0
    elif drop == "accounts[0].holdings":
        state["accounts"][0]["missing_holdings_confirmed"] = False
        state["accounts"][0]["holdings"] = []
    elif drop == "goals.empty":
        state["goals"] = []
    elif drop == "goals[0].time_horizon_years":
        state["goals"][0].pop("time_horizon_years", None)
        state["goals"][0].pop("target_date", None)
    elif drop == "goal_account_links.empty":
        state["goal_account_links"] = []
    elif drop == "goal_account_links[0].allocated_amount":
        state["goal_account_links"] = [{"goal_id": "goal_1", "account_id": "acct_1"}]
    elif drop == "risk.household_score":
        state["risk"] = {}
        state["household"]["household_risk_score"] = None
    return state


def _find(missing: list[dict], section: str) -> dict | None:
    for item in missing:
        if item.get("section") == section:
            return item
    return None


def test_field_path_household_display_name() -> None:
    state = _state_missing_section(drop="household.display_name")
    readiness = readiness_for_state(state)
    row = _find(readiness.missing, "household")
    assert row is not None
    assert row["field_path"] == "household.display_name"
    assert "label" in row


def test_field_path_household_household_type() -> None:
    state = _state_missing_section(drop="household.household_type")
    readiness = readiness_for_state(state)
    row = _find(readiness.missing, "household")
    assert row is not None
    assert row["field_path"] == "household.household_type"


def test_field_path_people_dob() -> None:
    state = _state_missing_section(drop="people[0].date_of_birth")
    readiness = readiness_for_state(state)
    row = _find(readiness.missing, "people")
    assert row is not None
    assert row["field_path"] == "people[0].date_of_birth"


def test_field_path_people_empty() -> None:
    state = _state_missing_section(drop="people.empty")
    readiness = readiness_for_state(state)
    row = _find(readiness.missing, "people")
    assert row is not None
    # Section-level blocker with no specific index — frontend renders no CTA.
    assert row["field_path"] == "people[0]"


def test_field_path_accounts_current_value() -> None:
    state = _state_missing_section(drop="accounts[0].current_value")
    readiness = readiness_for_state(state)
    rows = [r for r in readiness.missing if r["section"] == "accounts"]
    assert any(r["field_path"] == "accounts[0].current_value" for r in rows)


def test_field_path_accounts_holdings() -> None:
    state = _state_missing_section(drop="accounts[0].holdings")
    readiness = readiness_for_state(state)
    rows = [r for r in readiness.missing if r["section"] == "accounts"]
    assert any(r["field_path"] == "accounts[0].holdings" for r in rows)


def test_field_path_goals_time_horizon() -> None:
    state = _state_missing_section(drop="goals[0].time_horizon_years")
    readiness = readiness_for_state(state)
    row = _find(readiness.missing, "goals")
    assert row is not None
    assert row["field_path"] == "goals[0].time_horizon_years"


def test_field_path_goal_account_mapping_missing() -> None:
    state = _state_missing_section(drop="goal_account_links.empty")
    readiness = readiness_for_state(state)
    row = _find(readiness.missing, "goal_account_mapping")
    assert row is not None
    assert row["field_path"] == "goal_account_links"


def test_field_path_goal_account_mapping_allocated_amount() -> None:
    state = _state_missing_section(drop="goal_account_links[0].allocated_amount")
    readiness = readiness_for_state(state)
    rows = [r for r in readiness.missing if r["section"] == "goal_account_mapping"]
    assert any(r["field_path"] == "goal_account_links[0].allocated_amount" for r in rows)


def test_field_path_risk_household_score() -> None:
    state = _state_missing_section(drop="risk.household_score")
    readiness = readiness_for_state(state)
    row = _find(readiness.missing, "risk")
    assert row is not None
    assert row["field_path"] == "risk.household_score"


def test_field_path_present_on_every_row() -> None:
    """Sister §3.16 backwards-compat — every row carries a ``field_path`` key
    (even if empty), so the frontend never has a missing key crash."""
    state = _state_missing_section(drop="people.empty")
    state["accounts"] = []
    state["goals"] = []
    state["risk"] = {}
    state["household"]["household_risk_score"] = None
    readiness = readiness_for_state(state)
    assert readiness.missing  # non-empty
    for row in readiness.missing:
        assert "field_path" in row, f"Row missing field_path: {row!r}"
        assert isinstance(row["field_path"], str)


def test_field_path_full_assignment_blocker_targets_specific_account_index() -> None:
    """``_full_assignment_blockers`` field_path targets the specific account
    by index so the inline-fix CTA lands on the broken account."""
    # Two purpose accounts with mismatched allocations
    state = {
        "household": {
            "display_name": "Two Account Test",
            "household_type": "couple",
            "household_risk_score": 3,
        },
        "people": [{"id": "person_1", "name": "Lead", "age": 60}],
        "accounts": [
            {
                "id": "acct_1",
                "type": "RRSP",
                "current_value": 100000,
                "missing_holdings_confirmed": True,
                "is_held_at_purpose": True,
            },
            {
                "id": "acct_2",
                "type": "TFSA",
                "current_value": 50000,
                "missing_holdings_confirmed": True,
                "is_held_at_purpose": True,
            },
        ],
        "goals": [
            {
                "id": "goal_1",
                "name": "Retirement",
                "time_horizon_years": 5,
                "goal_risk_score": 3,
            }
        ],
        # Both accounts allocate to goal_1, but acct_2 is 50% short
        "goal_account_links": [
            {"goal_id": "goal_1", "account_id": "acct_1", "allocated_amount": 100000},
            {"goal_id": "goal_1", "account_id": "acct_2", "allocated_amount": 25000},
        ],
        "risk": {"household_score": 3},
    }
    readiness = readiness_for_state(state)
    rows = [r for r in readiness.missing if r["section"] == "goal_account_mapping"]
    # acct_2 (index 1) is the broken account; field_path should reflect that.
    assert any(r["field_path"] == "accounts[1].goal_account_links" for r in rows)


def test_field_path_construction_blocker_account_type() -> None:
    """``construction_missing[]`` rows also carry ``field_path``."""
    state = _state_missing_section(drop="household.display_name")
    state["household"]["display_name"] = "Construction Test"
    state["accounts"][0]["type"] = "Crypto"  # Unsupported type → construction blocker
    readiness = readiness_for_state(state)
    rows = [r for r in readiness.construction_missing if r["section"] == "accounts"]
    assert any(r["field_path"] == "accounts[0].account_type" for r in rows)
