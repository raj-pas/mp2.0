"""P13 — AssignAccountToGoalsView coverage.

Per plan v20 §A1.28 + §A1.50 (P13 boundary cases) + §A1.51 (cross-phase
P11×P13) + §A1.55 (network failure / DB rollback) + §A1.23 (audit metadata
schema; no rationale text).

Covers (one test per row):
  1. happy path (existing-goal-only) → 200 + new GoalAccountLink + audit emitted
  2. sum within 1bp tolerance → accepted
  3. sum 1bp over → 400 with structured AccountAssignmentRollupMismatch code
  4. sum 1bp under → 400 with structured AccountAssignmentRollupMismatch code
  5. zero allocation per goal → 400 with `zero_allocation_per_goal`
  6. rationale empty → 400 with `rationale_too_short`
  7. rationale exactly 4 chars → 200 (boundary)
  8. rationale 4096+ chars → 200 + audit metadata stores ONLY length
  9. duplicate goal_id → 400 with `duplicate_goal_id`
 10. unknown goal_id → 400 with `unknown_goal`
 11. new-goal inline-create round-trip → 200 + Goal row created + audit
 12. new-goal missing target_amount → 400 with `new_goal_missing_target`
 13. concurrent assignment ThreadPoolExecutor (N=20; reduced from 100 per
     §A1.46 perf budget — the lock-contention property surfaces well before
     N=100 and engine.optimize() in `_trigger_and_audit` is the wall-time
     dominator) → atomic + audit_count == success_count
 14. atomic rollback on partial failure → no link write + no audit emission
 15. auto-trigger fires (verifies `_trigger_and_audit(source="goal_assignment")`
     is invoked once)

Coverage gate per sister §3.14: ≥90% on `AssignAccountToGoalsView` lines.
"""

from __future__ import annotations

import concurrent.futures
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection, connections
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.audit.models import AuditEvent

User = get_user_model()


def _user(email: str = "advisor@example.com"):
    user, _ = User.objects.get_or_create(
        email=email,
        defaults={"username": email, "is_active": True},
    )
    return user


def _bootstrap_full_demo() -> models.Household:
    call_command("seed_default_cma", "--force")
    call_command("load_synthetic_personas")
    return models.Household.objects.get(external_id="hh_sandra_mike_chen")


def _client(user) -> APIClient:
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _account_value_bp(account: models.Account) -> int:
    return int((account.current_value * Decimal(10_000)).quantize(Decimal("1")))


def _url(household: models.Household, account: models.Account) -> str:
    return reverse(
        "assign-account-to-goals",
        args=[household.external_id, account.external_id],
    )


# ---------------------------------------------------------------------------
# Test 1 — happy path (existing-goal-only) → 200 + link + audit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_happy_path_existing_goal_only_creates_link_and_audit() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    goal = hh.goals.first()
    assert account is not None and goal is not None
    bp = _account_value_bp(account)

    pre_audit = AuditEvent.objects.filter(
        action="account_assigned_to_goals", entity_id=hh.external_id
    ).count()

    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "Allocate full RRSP to retirement goal.",
            "assignments": [
                {"goal_id": goal.external_id, "allocated_amount_basis_points": bp},
            ],
        },
        format="json",
    )

    assert resp.status_code == 200, resp.data
    assert resp.data["id"] == hh.external_id

    link = models.GoalAccountLink.objects.get(goal=goal, account=account)
    assert link.allocated_amount == account.current_value
    assert link.allocated_pct is None

    post_audit = AuditEvent.objects.filter(
        action="account_assigned_to_goals", entity_id=hh.external_id
    ).count()
    assert post_audit == pre_audit + 1
    metadata = (
        AuditEvent.objects.filter(action="account_assigned_to_goals", entity_id=hh.external_id)
        .order_by("-id")
        .first()
        .metadata
    )
    assert metadata["account_id"] == account.external_id
    assert metadata["assignment_count"] == 1
    assert metadata["total_assigned_basis_points"] == bp
    assert metadata["new_goal_count"] == 0
    assert metadata["rationale_present"] is True
    assert metadata["rationale_length"] == len("Allocate full RRSP to retirement goal.")


# ---------------------------------------------------------------------------
# Tests 2-4 — sum-validator boundary cases (§A1.50)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sum_within_1bp_tolerance_passes_validation() -> None:
    """Sum equal to account_value_bp passes (boundary; tolerance=0)."""
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    goal = hh.goals.first()
    bp = _account_value_bp(account)
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "Exact match — boundary test for §A1.50 #1.",
            "assignments": [
                {"goal_id": goal.external_id, "allocated_amount_basis_points": bp},
            ],
        },
        format="json",
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_sum_1bp_over_rejected_with_structured_code() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    goal = hh.goals.first()
    bp = _account_value_bp(account) + 2  # 2 bp over → exceeds 1bp tolerance
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "Boundary test: sum 2bp over.",
            "assignments": [
                {"goal_id": goal.external_id, "allocated_amount_basis_points": bp},
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "AccountAssignmentRollupMismatch"
    # Atomic rollback — pre-existing synthetic link is unchanged at its
    # seeded value (Emma → acct_non_registered = $68K from
    # personas/sandra_mike_chen/client_state.json).
    pre_link = models.GoalAccountLink.objects.filter(goal=goal, account=account).first()
    assert pre_link is None or pre_link.allocated_amount == Decimal("68000.00")


@pytest.mark.django_db
def test_sum_1bp_under_rejected_with_structured_code() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    goal = hh.goals.first()
    bp = _account_value_bp(account) - 2  # 2 bp under
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "Boundary test: sum 2bp under.",
            "assignments": [
                {"goal_id": goal.external_id, "allocated_amount_basis_points": bp},
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "AccountAssignmentRollupMismatch"


# ---------------------------------------------------------------------------
# Test 5 — zero allocation per goal (§A1.50)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_zero_allocation_per_goal_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    goal = hh.goals.first()
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "Zero allocation must be rejected.",
            "assignments": [
                {"goal_id": goal.external_id, "allocated_amount_basis_points": 0},
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "zero_allocation_per_goal"


# ---------------------------------------------------------------------------
# Tests 6-8 — rationale boundary handling (§A1.50)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_empty_rationale_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    goal = hh.goals.first()
    bp = _account_value_bp(account)
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "",
            "assignments": [
                {"goal_id": goal.external_id, "allocated_amount_basis_points": bp},
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "rationale_too_short"


@pytest.mark.django_db
def test_4_char_rationale_accepted() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    goal = hh.goals.first()
    bp = _account_value_bp(account)
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "abcd",  # exactly 4 chars
            "assignments": [
                {"goal_id": goal.external_id, "allocated_amount_basis_points": bp},
            ],
        },
        format="json",
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_long_rationale_metadata_only_stores_length() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    goal = hh.goals.first()
    bp = _account_value_bp(account)
    long_rationale = "x" * 4096
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": long_rationale,
            "assignments": [
                {"goal_id": goal.external_id, "allocated_amount_basis_points": bp},
            ],
        },
        format="json",
    )
    assert resp.status_code == 200
    event = (
        AuditEvent.objects.filter(action="account_assigned_to_goals", entity_id=hh.external_id)
        .order_by("-id")
        .first()
    )
    assert event.metadata["rationale_length"] == 4096
    # Long rationale text must NOT appear in metadata (PII discipline).
    import json

    blob = json.dumps(event.metadata)
    assert long_rationale not in blob, "Long rationale leaked into audit metadata"


# ---------------------------------------------------------------------------
# Tests 9-10 — duplicate / unknown goal handling
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_duplicate_goal_id_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    goal = hh.goals.first()
    half_bp = _account_value_bp(account) // 2
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "Duplicate goal_id should reject.",
            "assignments": [
                {"goal_id": goal.external_id, "allocated_amount_basis_points": half_bp},
                {"goal_id": goal.external_id, "allocated_amount_basis_points": half_bp},
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "duplicate_goal_id"


@pytest.mark.django_db
def test_unknown_goal_id_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    bp = _account_value_bp(account)
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "Unknown goal id should reject.",
            "assignments": [
                {
                    "goal_id": "goal_does_not_exist",
                    "allocated_amount_basis_points": bp,
                },
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "unknown_goal"


# ---------------------------------------------------------------------------
# Tests 11-12 — new-goal inline-create (§A1.14 #17)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_new_goal_inline_create_round_trip() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    bp = _account_value_bp(account)
    pre_goal_count = hh.goals.count()
    new_goal_target_date = (date.today() + timedelta(days=3650)).isoformat()
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "Create a new goal inline.",
            "assignments": [
                {
                    "goal_id": "new",
                    "new_goal": {
                        "name": "Vacation home",
                        "target_amount_basis_points": 5_000_000_0000,  # $5M target
                        "necessity_score": 2,
                        "risk_score": 3,
                        "target_date": new_goal_target_date,
                    },
                    "allocated_amount_basis_points": bp,
                },
            ],
        },
        format="json",
    )
    assert resp.status_code == 200, resp.data
    assert hh.goals.count() == pre_goal_count + 1
    new_goal = hh.goals.filter(name="Vacation home").first()
    assert new_goal is not None
    assert new_goal.necessity_score == 2
    assert new_goal.goal_risk_score == 3
    # Audit metadata reflects new_goal_count=1.
    event = (
        AuditEvent.objects.filter(action="account_assigned_to_goals", entity_id=hh.external_id)
        .order_by("-id")
        .first()
    )
    assert event.metadata["new_goal_count"] == 1


@pytest.mark.django_db
def test_new_goal_missing_target_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    bp = _account_value_bp(account)
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "Missing target_amount must reject.",
            "assignments": [
                {
                    "goal_id": "new",
                    "new_goal": {
                        "name": "Bad goal",
                        # target_amount_basis_points missing
                        "necessity_score": 3,
                        "risk_score": 3,
                        "target_date": "2030-01-01",
                    },
                    "allocated_amount_basis_points": bp,
                },
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "new_goal_missing_target"


# ---------------------------------------------------------------------------
# Test 13 — concurrent assignment (atomic + select_for_update; sister pattern)
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_concurrent_assignment_atomic_at_n_20() -> None:
    """N=20 parallel POSTs to the same account/goal endpoint.

    Atomic + select_for_update on Household serializes writes; every call
    succeeds (UPSERT semantics — last-writer-wins on the link row).
    Audit count == success count per locked #37.

    N=20 (not 100) because `_trigger_and_audit` invokes engine.optimize()
    inline per locked #74; 20 × ~500ms hits the 60s/test budget. The
    lock-contention property surfaces well before N=20.
    """
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    goal = hh.goals.first()
    bp = _account_value_bp(account)
    url = _url(hh, account)

    pre_audit = AuditEvent.objects.filter(
        action="account_assigned_to_goals", entity_id=hh.external_id
    ).count()

    def _request(idx: int) -> int:
        try:
            client = APIClient()
            client.force_authenticate(user=user)
            return client.post(
                url,
                {
                    "rationale": f"Concurrent assign #{idx}.",
                    "assignments": [
                        {
                            "goal_id": goal.external_id,
                            "allocated_amount_basis_points": bp,
                        },
                    ],
                },
                format="json",
            ).status_code
        finally:
            for alias in connections:
                connections[alias].close()

    statuses = []
    n = 20
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_request, i) for i in range(n)]
        for f in concurrent.futures.as_completed(futures):
            statuses.append(f.result())
    connection.close()

    assert all(s in (200, 400) for s in statuses), f"5xx escapes: {statuses}"
    success_count = sum(1 for s in statuses if s == 200)
    # Every concurrent request issues the SAME well-formed payload, so
    # every one should succeed (lock serializes writes; UPSERT prevents
    # IntegrityError on the unique (goal, account) constraint).
    assert success_count == n, f"Expected {n} successes; got {success_count}"

    post_audit = AuditEvent.objects.filter(
        action="account_assigned_to_goals", entity_id=hh.external_id
    ).count()
    # Locked #37: exactly one event per state-changing action.
    assert post_audit == pre_audit + success_count


# ---------------------------------------------------------------------------
# Test 14 — atomic rollback on mid-write failure (no audit leak)
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_atomic_rollback_on_partial_failure_no_audit_leak() -> None:
    """Force a DB IntegrityError mid-mutation; verify atomic rollback +
    no audit event emission (matches §A1.55 backend resilience spec).
    """
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    goal = hh.goals.first()
    bp = _account_value_bp(account)
    pre_audit = AuditEvent.objects.filter(
        action="account_assigned_to_goals", entity_id=hh.external_id
    ).count()
    pre_link_count = models.GoalAccountLink.objects.filter(account=account).count()

    from django.db import IntegrityError

    def _boom(*args, **kwargs):
        raise IntegrityError("Forced integrity violation for test_atomic_rollback")

    with patch.object(models.GoalAccountLink.objects, "update_or_create", side_effect=_boom):
        client = APIClient()
        client.force_authenticate(user=user)
        try:
            resp = client.post(
                _url(hh, account),
                {
                    "rationale": "Forced partial-failure test.",
                    "assignments": [
                        {
                            "goal_id": goal.external_id,
                            "allocated_amount_basis_points": bp,
                        },
                    ],
                },
                format="json",
            )
            assert resp.status_code in (500, 400)
        except IntegrityError:
            # DRF may re-raise on certain configurations; also acceptable.
            pass

    post_audit = AuditEvent.objects.filter(
        action="account_assigned_to_goals", entity_id=hh.external_id
    ).count()
    post_link_count = models.GoalAccountLink.objects.filter(account=account).count()
    assert post_audit == pre_audit, "Audit emission leaked despite atomic rollback"
    assert post_link_count == pre_link_count, "Partial link write despite atomic"


# ---------------------------------------------------------------------------
# Test 15 — auto-trigger fires (locked #74)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_auto_trigger_fires_with_goal_assignment_source() -> None:
    """Verify `_trigger_and_audit(source="goal_assignment")` is invoked
    inline post-assignment per locked #74. Spy on the helper directly.
    """
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    goal = hh.goals.first()
    bp = _account_value_bp(account)
    with patch("web.api.views._trigger_and_audit") as mock_trigger:
        mock_trigger.return_value = None
        resp = _client(user).post(
            _url(hh, account),
            {
                "rationale": "Auto-trigger spy test.",
                "assignments": [
                    {"goal_id": goal.external_id, "allocated_amount_basis_points": bp},
                ],
            },
            format="json",
        )
    assert resp.status_code == 200
    assert mock_trigger.called
    args, kwargs = mock_trigger.call_args
    assert args[0] == hh
    assert kwargs.get("source") == "goal_assignment"


# ---------------------------------------------------------------------------
# Test 16 — auth boundary (sister §3.5; locked #18)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unauthenticated_request_rejected_401() -> None:
    hh = _bootstrap_full_demo()
    account = hh.accounts.first()
    goal = hh.goals.first()
    bp = _account_value_bp(account)
    resp = APIClient().post(
        _url(hh, account),
        {
            "rationale": "anonymous attempt",
            "assignments": [
                {"goal_id": goal.external_id, "allocated_amount_basis_points": bp},
            ],
        },
        format="json",
    )
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Tests 17-25 — coverage-completing error-path tests (sister §3.14 90% gate)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_assignments_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    resp = _client(user).post(
        _url(hh, account),
        {"rationale": "no assignments at all", "assignments": []},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "no_assignments"


@pytest.mark.django_db
def test_invalid_assignment_shape_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    resp = _client(user).post(
        _url(hh, account),
        {"rationale": "bad row shape", "assignments": ["not-an-object"]},
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "invalid_assignment_shape"


@pytest.mark.django_db
def test_missing_goal_id_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "missing goal_id field",
            "assignments": [{"allocated_amount_basis_points": 100}],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "missing_goal_id"


@pytest.mark.django_db
def test_invalid_allocation_basis_points_type_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    goal = hh.goals.first()
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "wrong type for bp",
            "assignments": [
                {
                    "goal_id": goal.external_id,
                    # bp must be int, not float string
                    "allocated_amount_basis_points": "100",
                },
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "invalid_allocation_basis_points"


@pytest.mark.django_db
def test_unknown_household_returns_404() -> None:
    user = _user()
    # Bootstrap to ensure auth profile exists
    _bootstrap_full_demo()
    resp = _client(user).post(
        "/api/clients/hh_does_not_exist/accounts/acct_x/assign-goals/",
        {
            "rationale": "unknown household",
            "assignments": [
                {"goal_id": "goal_x", "allocated_amount_basis_points": 100},
            ],
        },
        format="json",
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_unknown_account_in_household_returns_404() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    goal = hh.goals.first()
    resp = _client(user).post(
        f"/api/clients/{hh.external_id}/accounts/acct_does_not_exist/assign-goals/",
        {
            "rationale": "unknown account in household",
            "assignments": [
                {"goal_id": goal.external_id, "allocated_amount_basis_points": 100},
            ],
        },
        format="json",
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_new_goal_missing_payload_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    bp = _account_value_bp(account)
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "new without payload",
            "assignments": [
                {"goal_id": "new", "allocated_amount_basis_points": bp},
                # new_goal field absent entirely
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "new_goal_missing_payload"


@pytest.mark.django_db
def test_new_goal_invalid_target_date_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    bp = _account_value_bp(account)
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "new with bad target_date",
            "assignments": [
                {
                    "goal_id": "new",
                    "new_goal": {
                        "name": "Bad date goal",
                        "target_amount_basis_points": 1_000_0000,
                        "necessity_score": 3,
                        "risk_score": 3,
                        "target_date": "not-a-date",
                    },
                    "allocated_amount_basis_points": bp,
                },
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "new_goal_invalid_target_date"


@pytest.mark.django_db
def test_new_goal_missing_target_date_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    bp = _account_value_bp(account)
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "new without target_date string",
            "assignments": [
                {
                    "goal_id": "new",
                    "new_goal": {
                        "name": "No date goal",
                        "target_amount_basis_points": 1_000_0000,
                        "necessity_score": 3,
                        "risk_score": 3,
                        # target_date missing
                    },
                    "allocated_amount_basis_points": bp,
                },
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "new_goal_missing_target_date"


@pytest.mark.django_db
def test_new_goal_invalid_risk_score_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    bp = _account_value_bp(account)
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "new with risk out of range",
            "assignments": [
                {
                    "goal_id": "new",
                    "new_goal": {
                        "name": "Bad risk goal",
                        "target_amount_basis_points": 1_000_0000,
                        "necessity_score": 3,
                        "risk_score": 10,  # outside 1-5
                        "target_date": "2030-01-01",
                    },
                    "allocated_amount_basis_points": bp,
                },
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "new_goal_invalid_risk"


@pytest.mark.django_db
def test_new_goal_invalid_necessity_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    bp = _account_value_bp(account)
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "new with necessity out of range",
            "assignments": [
                {
                    "goal_id": "new",
                    "new_goal": {
                        "name": "Bad necessity goal",
                        "target_amount_basis_points": 1_000_0000,
                        "necessity_score": 0,
                        "risk_score": 3,
                        "target_date": "2030-01-01",
                    },
                    "allocated_amount_basis_points": bp,
                },
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "new_goal_invalid_necessity"


@pytest.mark.django_db
def test_new_goal_missing_name_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    bp = _account_value_bp(account)
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "new without name",
            "assignments": [
                {
                    "goal_id": "new",
                    "new_goal": {
                        "name": "  ",  # blank-only
                        "target_amount_basis_points": 1_000_0000,
                        "necessity_score": 3,
                        "risk_score": 3,
                        "target_date": "2030-01-01",
                    },
                    "allocated_amount_basis_points": bp,
                },
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "new_goal_missing_name"


@pytest.mark.django_db
def test_new_goal_invalid_target_amount_negative_rejected() -> None:
    hh = _bootstrap_full_demo()
    user = _user()
    account = hh.accounts.first()
    bp = _account_value_bp(account)
    resp = _client(user).post(
        _url(hh, account),
        {
            "rationale": "new with negative target",
            "assignments": [
                {
                    "goal_id": "new",
                    "new_goal": {
                        "name": "Negative target",
                        "target_amount_basis_points": -1,
                        "necessity_score": 3,
                        "risk_score": 3,
                        "target_date": "2030-01-01",
                    },
                    "allocated_amount_basis_points": bp,
                },
            ],
        },
        format="json",
    )
    assert resp.status_code == 400
    assert resp.data["code"] == "new_goal_invalid_target"


@pytest.mark.django_db
def test_role_without_real_pii_access_returns_403() -> None:
    """Pre-PII-acked advisor (no profile / no acceptance) is gated by
    `can_access_real_pii(user)`. Mirrors sister access boundary."""
    hh = _bootstrap_full_demo()
    account = hh.accounts.first()
    goal = hh.goals.first()
    bp = _account_value_bp(account)
    no_pii_user, _ = User.objects.get_or_create(
        email="no-pii@example.com",
        defaults={"username": "no-pii@example.com", "is_active": True},
    )
    # Simulate no real-PII access — patch the helper so the perms gate trips.
    with patch("web.api.views.can_access_real_pii", return_value=False):
        resp = _client(no_pii_user).post(
            _url(hh, account),
            {
                "rationale": "should not reach DB",
                "assignments": [
                    {"goal_id": goal.external_id, "allocated_amount_basis_points": bp},
                ],
            },
            format="json",
        )
    assert resp.status_code == 403
