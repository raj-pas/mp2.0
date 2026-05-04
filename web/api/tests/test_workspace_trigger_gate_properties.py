"""Hypothesis property tests — `_trigger_and_audit_for_workspace` invariants.

Per locked decisions #14 (8 trigger points; 4 NEW workspace-level) +
#27 (workspace mutations no-op when `linked_household_id` is None).

The 4 NEW workspace-level trigger sources operate on
`ReviewWorkspace.reviewed_state` (in-memory scratch). They fire
`_trigger_portfolio_generation` ONLY when `workspace.linked_household`
exists. For un-linked workspaces (the common pre-commit case), the
trigger is a no-op + emits a structured skip audit for observability.

Properties asserted:
  1. Workspace WITHOUT linked_household_id → skip audit emitted with
     canonical action + structured metadata + helper returns None.
  2. Workspace WITH linked_household_id → trigger fires against the
     linked household; same-signature → REUSED PortfolioRunEvent.
  3. Workspace skip audit `entity_type` is "review_workspace" with
     `entity_id` = workspace.external_id (not household.external_id).
"""

from __future__ import annotations

import hypothesis.strategies as st
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from hypothesis import HealthCheck, given, settings
from web.api import models
from web.api.views import _trigger_and_audit_for_workspace
from web.audit.models import AuditEvent

User = get_user_model()

HYPO_SETTINGS = dict(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)

# Per locked #14: the 4 NEW workspace-level trigger sources.
WORKSPACE_TRIGGER_SOURCES = [
    "conflict_resolve",
    "defer_conflict",
    "fact_override",
    "section_approve",
]


def _make_user() -> User:
    user, _ = User.objects.get_or_create(
        username="advisor@example.com",
        defaults={"email": "advisor@example.com"},
    )
    return user


def _bootstrap_full_demo() -> models.Household:
    """Reset state with seed_default_cma + load_synthetic_personas."""
    call_command("seed_default_cma", "--force")
    call_command("load_synthetic_personas")
    return models.Household.objects.get(external_id="hh_sandra_mike_chen")


def _unlinked_workspace(user, *, label: str) -> models.ReviewWorkspace:
    """Bare workspace with linked_household_id=None (the common pre-commit case)."""
    return models.ReviewWorkspace.objects.create(
        label=label,
        owner=user,
        status=models.ReviewWorkspace.Status.DRAFT,
    )


def _linked_workspace(user, household: models.Household, *, label: str) -> models.ReviewWorkspace:
    """Workspace already linked to a committed household (post-commit edits flow).

    Uses `data_origin=SYNTHETIC` so `_portfolio_provenance_hashes` doesn't
    raise MissingProvenance (real-derived path requires
    `status=COMMITTED + reviewed_state non-empty`). Synthetic origin
    matches the synthetic personas the test bootstrap uses.
    """
    return models.ReviewWorkspace.objects.create(
        label=label,
        owner=user,
        linked_household=household,
        status=models.ReviewWorkspace.Status.COMMITTED,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )


# ---------------------------------------------------------------------------
# Property 1 — Unlinked workspace always skips with canonical metadata
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@given(source=st.sampled_from(WORKSPACE_TRIGGER_SOURCES))
@settings(**HYPO_SETTINGS)
def test_property_workspace_no_linked_household_emits_skip_audit_returns_none(
    source,
) -> None:
    """For all 4 NEW workspace-level sources: linked_household_id=None
    → audit emitted with action=`portfolio_generation_skipped_post_<source>`,
      metadata.skipped_no_household=True, metadata.reason_code='no_linked_household',
      metadata.workspace_id=workspace.external_id, metadata.source=<source>.
    → helper returns None.
    """
    # NOTE: do NOT bootstrap full demo; we want a clean workspace gate test
    # without the synthetic-load PortfolioRun side effect on Sandra/Mike.
    user = _make_user()
    workspace = _unlinked_workspace(user, label=f"WS-skip-{source}")

    result = _trigger_and_audit_for_workspace(workspace, user, source=source)
    assert result is None

    expected_action = f"portfolio_generation_skipped_post_{source}"
    skip_events = AuditEvent.objects.filter(
        action=expected_action,
        entity_id=workspace.external_id,
    )
    assert skip_events.count() == 1, (
        f"Expected exactly 1 skip audit for action {expected_action!r}; got {skip_events.count()}"
    )
    event = skip_events.first()
    assert event.entity_type == "review_workspace"
    metadata = event.metadata
    assert metadata["source"] == source
    assert metadata["skipped_no_household"] is True
    assert metadata["workspace_id"] == workspace.external_id
    assert metadata["reason_code"] == "no_linked_household"


# ---------------------------------------------------------------------------
# Property 2 — Linked workspace fires + REUSED on same-signature
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@given(source=st.sampled_from(WORKSPACE_TRIGGER_SOURCES))
@settings(**HYPO_SETTINGS)
def test_property_workspace_with_linked_household_fires_trigger(source) -> None:
    """Linked workspace → falls through to `_trigger_and_audit` against
    the linked household → returns a PortfolioRun + emits a generated OR
    reused audit (NOT a workspace-skip audit).

    Verifies the workspace gate per #27 DOES fire when linked.

    Subtle note: linking a fresh workspace to the household causes
    `_portfolio_provenance_hashes` to compute a different
    `approval_snapshot_hash` than the synthetic-load auto-seed (which
    had no workspace yet). The signature differs → expect GENERATED
    rather than REUSED. We assert the helper succeeds AND the workspace-
    skip audit is absent.
    """
    hh = _bootstrap_full_demo()
    user = _make_user()
    workspace = _linked_workspace(user, hh, label=f"WS-linked-{source}")

    starting_audit_count = AuditEvent.objects.filter(
        action__in=["portfolio_run_generated", "portfolio_run_reused"],
        metadata__household_id=hh.external_id,
    ).count()

    result = _trigger_and_audit_for_workspace(workspace, user, source=source)

    # Helper falls through and returns a PortfolioRun for the linked household.
    assert isinstance(result, models.PortfolioRun), (
        f"Expected PortfolioRun, got {result!r} for source {source!r}"
    )
    assert result.household_id == hh.id

    # Exactly one canonical audit (generated OR reused) emitted for the
    # underlying household.
    ending_audit_count = AuditEvent.objects.filter(
        action__in=["portfolio_run_generated", "portfolio_run_reused"],
        metadata__household_id=hh.external_id,
    ).count()
    assert ending_audit_count - starting_audit_count == 1

    # No workspace-level skip audit emitted (the gate fell through).
    skip_events = AuditEvent.objects.filter(
        action=f"portfolio_generation_skipped_post_{source}",
        entity_id=workspace.external_id,
    )
    assert skip_events.count() == 0


# ---------------------------------------------------------------------------
# Property 3 — Skip-audit entity_type is review_workspace, not household
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_workspace_skip_audit_entity_type_is_review_workspace() -> None:
    """For the un-linked workspace skip path: entity_type must be
    'review_workspace' and entity_id must be workspace.external_id —
    NOT 'household' / household.external_id.

    This pins the audit-trail attribution boundary: workspace-level
    skips are attributed to the workspace; downstream household-level
    triggers (linked workspaces) attribute to the household.
    """
    user = _make_user()
    workspace = _unlinked_workspace(user, label="WS-attribution")
    source = "conflict_resolve"

    _trigger_and_audit_for_workspace(workspace, user, source=source)

    skip_events = AuditEvent.objects.filter(
        action=f"portfolio_generation_skipped_post_{source}",
        entity_id=workspace.external_id,
    )
    assert skip_events.count() == 1
    event = skip_events.first()
    assert event.entity_type == "review_workspace"
    assert event.entity_id == workspace.external_id

    # Cross-attribution check: NO audit row attributes this skip to a
    # household entity_type.
    cross_attributed = AuditEvent.objects.filter(
        action=f"portfolio_generation_skipped_post_{source}",
        entity_type="household",
        entity_id=workspace.external_id,
    )
    assert cross_attributed.count() == 0
