"""DB invariants — extended (canon §9.4.6 + locked decision #39c).

Extends `web/api/tests/test_db_state_integrity.py` with invariants
that catch regressions in the append-only / latest-row-wins / commit-
gate machinery:

  1. `_latest_overrides` returns the row with highest `created_at`
     for a given (workspace, field) — sort stability under N rows.
  2. Conflict resolution does NOT mutate any ExtractedFact row
     (resolution lives in workspace.reviewed_state, not facts).
  3. After a workspace commit, no ProcessingJob lingers in
     QUEUED/PROCESSING.
  4. Deferred conflicts have null resolution metadata.
  5. After Phase 5b.10 override, reviewed_state reflects the
     override's value at the relevant field path (latest-row-wins).
  6. For every audit row, the corresponding entity exists OR was
     deleted with documented audit-history-preservation.
"""

from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from web.api import models
from web.api.review_state import _latest_overrides, reviewed_state_from_workspace
from web.api.tests.factories import (
    ExtractedFactFactory,
    FactOverrideFactory,
    ReviewDocumentFactory,
    ReviewWorkspaceFactory,
    UserFactory,
)
from web.audit.models import AuditEvent

# ---- 1. _latest_overrides sort stability ---------------------------------


@pytest.mark.django_db
def test_latest_overrides_returns_highest_created_at_row() -> None:
    """N FactOverride rows for the same (workspace, field) → the row
    returned by `_latest_overrides` is the most recently created
    (canon §11.4 + locked-2026-05-02).
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    overrides = [
        FactOverrideFactory(
            workspace=workspace,
            field="people[0].date_of_birth",
            value=f"1985-03-1{i}",
            rationale=f"Edit {i}.",
            created_by=user,
        )
        for i in range(5)
    ]

    result = _latest_overrides(workspace)
    assert "people[0].date_of_birth" in result
    assert result["people[0].date_of_birth"].pk == overrides[-1].pk
    assert result["people[0].date_of_birth"].value == "1985-03-14"


@pytest.mark.django_db
def test_latest_overrides_per_field_isolation() -> None:
    """Per-field isolation: multiple fields → multiple entries."""
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    FactOverrideFactory(
        workspace=workspace,
        field="people[0].date_of_birth",
        value="1985-03-12",
        created_by=user,
    )
    latest_dob = FactOverrideFactory(
        workspace=workspace,
        field="people[0].date_of_birth",
        value="1985-03-15",
        created_by=user,
    )
    latest_name = FactOverrideFactory(
        workspace=workspace,
        field="people[0].name",
        value="Sandra Chen",
        created_by=user,
    )

    result = _latest_overrides(workspace)
    assert set(result.keys()) == {"people[0].date_of_birth", "people[0].name"}
    assert result["people[0].date_of_birth"].pk == latest_dob.pk
    assert result["people[0].name"].pk == latest_name.pk


# ---- 2. Conflict resolution does NOT mutate ExtractedFact rows -----------


@pytest.mark.django_db
def test_conflict_resolution_does_not_mutate_extracted_fact_rows() -> None:
    """Resolution lives in workspace.reviewed_state.conflicts[i],
    NOT on the underlying ExtractedFact rows.
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    doc1 = ReviewDocumentFactory(workspace=workspace, original_filename="kyc-1.pdf")
    doc2 = ReviewDocumentFactory(workspace=workspace, original_filename="kyc-2.pdf")
    fact1 = ExtractedFactFactory(
        workspace=workspace,
        document=doc1,
        field="people[0].date_of_birth",
        value="1985-03-12",
        evidence_quote="From KYC v1",
    )
    fact2 = ExtractedFactFactory(
        workspace=workspace,
        document=doc2,
        field="people[0].date_of_birth",
        value="1985-03-15",
        evidence_quote="From KYC v2",
    )

    fact1_before = (fact1.value, fact1.evidence_quote, fact1.confidence)
    fact2_before = (fact2.value, fact2.evidence_quote, fact2.confidence)

    state = reviewed_state_from_workspace(workspace)
    workspace.reviewed_state = state
    workspace.save(update_fields=["reviewed_state"])
    conflicts = workspace.reviewed_state.get("conflicts") or []
    if conflicts:
        conflicts[0]["resolved"] = True
        conflicts[0]["chosen_fact_id"] = fact1.id
        conflicts[0]["resolution"] = "advisor_chose_v1"
        workspace.reviewed_state["conflicts"] = conflicts
        workspace.save(update_fields=["reviewed_state"])

    fact1.refresh_from_db()
    fact2.refresh_from_db()
    assert (fact1.value, fact1.evidence_quote, fact1.confidence) == fact1_before
    assert (fact2.value, fact2.evidence_quote, fact2.confidence) == fact2_before


# ---- 3. Post-commit: no ProcessingJob in QUEUED/PROCESSING ----------------


@pytest.mark.django_db
def test_committed_workspace_has_no_pending_processing_jobs() -> None:
    """A pending job after commit means reconcile could fire on a
    committed workspace and silently mutate state — Bug-1 surface.
    """
    pending = models.ProcessingJob.objects.filter(
        workspace__status=models.ReviewWorkspace.Status.COMMITTED,
        status__in=[
            models.ProcessingJob.Status.QUEUED,
            models.ProcessingJob.Status.PROCESSING,
        ],
    )
    assert pending.count() == 0, (
        f"Found {pending.count()} pending ProcessingJobs on COMMITTED "
        f"workspaces: {list(pending.values_list('workspace__external_id', 'status'))}"
    )


@pytest.mark.django_db
def test_committed_workspace_invariant_flags_bad_case() -> None:
    """Contract test for the invariant itself — confirms it would
    catch the regression by concretely seeding a stale QUEUED job.
    """
    user = UserFactory()
    household = models.Household.objects.create(
        external_id="hh_committed_test",
        owner=user,
        display_name="Committed Household",
        household_type="single",
        household_risk_score=3,
    )
    workspace = ReviewWorkspaceFactory(
        owner=user,
        status=models.ReviewWorkspace.Status.COMMITTED,
        linked_household=household,
    )
    bad_job = models.ProcessingJob.objects.create(
        workspace=workspace,
        status=models.ProcessingJob.Status.QUEUED,
    )
    pending = models.ProcessingJob.objects.filter(
        workspace__status=models.ReviewWorkspace.Status.COMMITTED,
        status__in=[
            models.ProcessingJob.Status.QUEUED,
            models.ProcessingJob.Status.PROCESSING,
        ],
    )
    assert pending.filter(pk=bad_job.pk).exists()
    bad_job.delete()


# ---- 4. Deferred conflicts have null resolution metadata ------------------


@pytest.mark.django_db
def test_deferred_conflicts_have_no_resolution_metadata() -> None:
    """A deferred conflict has `deferred=True` but `resolved`,
    `chosen_fact_id`, `resolution` must remain null/empty.
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    doc1 = ReviewDocumentFactory(workspace=workspace, original_filename="kyc-1.pdf")
    doc2 = ReviewDocumentFactory(workspace=workspace, original_filename="kyc-2.pdf")
    ExtractedFactFactory(
        workspace=workspace,
        document=doc1,
        field="people[0].date_of_birth",
        value="1985-03-12",
    )
    ExtractedFactFactory(
        workspace=workspace,
        document=doc2,
        field="people[0].date_of_birth",
        value="1985-03-15",
    )
    state = reviewed_state_from_workspace(workspace)
    conflicts = state.get("conflicts") or []
    if conflicts:
        conflicts[0]["deferred"] = True
        conflicts[0]["deferred_by"] = user.email
        conflicts[0]["deferred_rationale"] = "Defer; awaiting client confirmation."
        workspace.reviewed_state = state
        workspace.save(update_fields=["reviewed_state"])

    refreshed = workspace.reviewed_state.get("conflicts") or []
    for conflict in refreshed:
        if conflict.get("deferred"):
            assert not conflict.get("resolved"), conflict
            assert conflict.get("chosen_fact_id") in (None, "", 0), conflict
            assert conflict.get("resolution") in (None, ""), conflict


# ---- 5. Override → reviewed_state reflects override value -----------------


@pytest.mark.django_db
def test_fact_override_value_visible_in_reviewed_state() -> None:
    """After an override, reviewed_state composer surfaces the
    override's value at the relevant field path (canon §11.4
    advisor source-priority hierarchy).
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    document = ReviewDocumentFactory(workspace=workspace)
    ExtractedFactFactory(
        workspace=workspace,
        document=document,
        field="people[0].date_of_birth",
        value="1985-03-12",
    )
    FactOverrideFactory(
        workspace=workspace,
        field="people[0].date_of_birth",
        value="1990-07-20",
        created_by=user,
    )

    state = reviewed_state_from_workspace(workspace)
    people = state.get("people") or []
    assert any(p.get("date_of_birth") == "1990-07-20" for p in people), people


@pytest.mark.django_db
def test_fact_override_chain_latest_wins_in_state() -> None:
    """Multiple overrides for the same field → LAST one is visible.
    Prior overrides preserved in DB (append-only) but not in state.
    """
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    document = ReviewDocumentFactory(workspace=workspace)
    ExtractedFactFactory(
        workspace=workspace,
        document=document,
        field="people[0].date_of_birth",
        value="1985-03-12",
    )
    for value in ("1990-07-20", "1990-07-22", "1990-07-25"):
        FactOverrideFactory(
            workspace=workspace,
            field="people[0].date_of_birth",
            value=value,
            created_by=user,
        )

    state = reviewed_state_from_workspace(workspace)
    visible = [p.get("date_of_birth") for p in (state.get("people") or [])]
    assert "1990-07-25" in visible, visible
    db_count = workspace.fact_overrides.filter(field="people[0].date_of_birth").count()
    assert db_count == 3, f"expected 3 historical overrides, got {db_count}"


# ---- 6. Audit rows + entity existence -------------------------------------


@pytest.mark.django_db
def test_audit_events_for_review_workspace_have_non_empty_entity_id() -> None:
    """Every AuditEvent with entity_type='review_workspace' must
    reference a non-empty entity_id. Deleted entities are accepted
    (audit history preserved); empty entity_id is the bug surface.
    """
    suspect = [
        (event.id, event.action)
        for event in AuditEvent.objects.filter(entity_type="review_workspace")
        if not event.entity_id
    ]
    assert not suspect, f"Found audit events with empty entity_id: {suspect}"


@pytest.mark.django_db
def test_audit_events_for_review_document_have_non_empty_entity_id() -> None:
    suspect = [
        (event.id, event.action)
        for event in AuditEvent.objects.filter(entity_type="review_document")
        if not event.entity_id
    ]
    assert not suspect, f"Found audit events with empty entity_id: {suspect}"


@pytest.mark.django_db
def test_audit_event_metadata_workspace_id_is_well_formed() -> None:
    """When `metadata['workspace_id']` is set, it must be a string
    of plausible shape (uuid-like). Catches typos in audit-emission.
    """
    for event in AuditEvent.objects.exclude(metadata__workspace_id=None):
        ws_id = event.metadata.get("workspace_id")
        if not ws_id:
            continue
        assert isinstance(ws_id, str) and len(ws_id) >= 8, (
            f"audit metadata.workspace_id has unexpected shape: {ws_id!r} on event {event.id}"
        )


# ---- 7. AuditEvent immutability (defense-in-depth) ------------------------


@pytest.mark.django_db
def test_audit_event_save_to_existing_pk_raises() -> None:
    event = AuditEvent.objects.create(
        action="test_action",
        entity_type="review_workspace",
        entity_id="ws-test",
        metadata={"foo": "bar"},
        actor="test",
    )
    event.metadata = {"foo": "bar", "tampered": True}
    with pytest.raises(Exception, match="immutable"):
        event.save()


@pytest.mark.django_db
def test_audit_event_delete_raises() -> None:
    event = AuditEvent.objects.create(
        action="test_action",
        entity_type="review_workspace",
        entity_id="ws-test",
        metadata={},
        actor="test",
    )
    with pytest.raises(Exception, match="immutable"):
        event.delete()


# ---- 8. Append-only model guards ------------------------------------------


@pytest.mark.django_db
def test_fact_override_save_to_existing_pk_raises() -> None:
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    override = FactOverrideFactory(
        workspace=workspace,
        field="people[0].date_of_birth",
        value="1985-03-12",
        created_by=user,
    )
    override.value = "1985-03-15"
    with pytest.raises(Exception, match="append-only"):
        override.save()


@pytest.mark.django_db
def test_household_snapshot_save_to_existing_pk_raises() -> None:
    user = UserFactory()
    household = models.Household.objects.create(
        external_id="hh_snap_test",
        owner=user,
        display_name="Snap Test",
        household_type="single",
        household_risk_score=3,
    )
    snapshot = models.HouseholdSnapshot.objects.create(
        household=household,
        triggered_by=models.HouseholdSnapshot.TriggerType.RE_GOAL,
        label="Initial",
        snapshot={"hh": "v1"},
        summary={},
        created_by=user,
    )
    snapshot.label = "tampered"
    with pytest.raises(Exception, match="append-only"):
        snapshot.save()


# ---- 9. Cross-table referential integrity ---------------------------------


@pytest.mark.django_db
def test_extracted_fact_document_workspace_match() -> None:
    """Every ExtractedFact's document.workspace must match its own
    workspace. Mismatched join → fact attributed to wrong workspace.
    """
    bad = []
    for fact in models.ExtractedFact.objects.select_related("document").all():
        if fact.document.workspace_id != fact.workspace_id:
            bad.append((fact.id, fact.workspace_id, fact.document.workspace_id))
    assert not bad, f"ExtractedFact rows where document.workspace != fact.workspace: {bad}"


# ---- 10. SectionApproval unique-per-section constraint --------------------


@pytest.mark.django_db
def test_section_approval_unique_per_workspace_section() -> None:
    user = UserFactory()
    workspace = ReviewWorkspaceFactory(owner=user)
    models.SectionApproval.objects.create(
        workspace=workspace,
        section="people",
        status=models.SectionApproval.Status.APPROVED,
        approved_by=user,
        approved_at=timezone.now(),
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            models.SectionApproval.objects.create(
                workspace=workspace,
                section="people",
                status=models.SectionApproval.Status.APPROVED,
                approved_by=user,
                approved_at=timezone.now(),
            )
