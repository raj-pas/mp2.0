"""Hypothesis property tests — conflict state-machine invariants.

States: active → deferred → resurfaced → resolved (and active → resolved).

Properties asserted:
  1. resolved is TERMINAL — defer-after-resolve does not unset resolved.
  2. resurfaced is reachable only from deferred AND only with new
     evidence (a new fact_id for the same field).
  3. Each state-changing API call emits exactly ONE audit event of the
     expected kind (review_conflict_resolved / review_conflict_deferred).
  4. Same field has 0 or 1 conflict entries in reviewed_state.
"""

from __future__ import annotations

import hypothesis.strategies as st
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from hypothesis import HealthCheck, given, settings
from rest_framework.test import APIClient
from web.api import models
from web.api.review_state import reviewed_state_from_workspace
from web.audit.models import AuditEvent

CONFLICT_FIELDS = [
    "people[0].date_of_birth",
    "people[0].marital_status",
    "people[1].name",
]
SAFE_RATIONALE = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789 _-:.", min_size=4, max_size=40
).map(lambda s: s if len(s.strip()) >= 4 else "rationale")
SAFE_VALUE = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=12)
HYPO_SETTINGS = dict(
    max_examples=30,
    deadline=2000,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)


def _user() -> object:
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="advisor@example.com",
        defaults={"email": "advisor@example.com", "is_active": True},
    )
    return user


def _doc(workspace, *, filename: str, document_type: str = "kyc") -> models.ReviewDocument:
    digest = (filename.encode().hex() + "0" * 64)[:64]
    return models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename=filename,
        content_type="application/pdf",
        extension="pdf",
        file_size=1024,
        sha256=digest,
        storage_path=f"workspace_{workspace.external_id}/{filename}",
        document_type=document_type,
        status=models.ReviewDocument.Status.RECONCILED,
    )


def _fact(workspace, document, *, field, value):
    return models.ExtractedFact.objects.create(
        workspace=workspace,
        document=document,
        field=field,
        value=value,
        confidence="medium",
        derivation_method="extracted",
        source_location="page 1",
        source_page=1,
        evidence_quote="evidence",
        extraction_run_id="run-test",
    )


def _seed_conflict(workspace, *, field: str = "people[0].date_of_birth") -> tuple[int, int]:
    """Two same-class kyc docs disagreeing on `field`. Returns fact ids."""
    kyc1 = _doc(workspace, filename=f"{field}-kyc1.pdf", document_type="kyc")
    kyc2 = _doc(workspace, filename=f"{field}-kyc2.pdf", document_type="kyc")
    f1 = _fact(workspace, kyc1, field=field, value="value-a")
    f2 = _fact(workspace, kyc2, field=field, value="value-b")
    workspace.reviewed_state = reviewed_state_from_workspace(workspace)
    workspace.save(update_fields=["reviewed_state"])
    return f1.id, f2.id


def _post_resolve(client, workspace, *, field, chosen_fact_id, rationale="advisor reviewed"):
    return client.post(
        reverse("review-workspace-conflict-resolve", args=[workspace.external_id]),
        {
            "field": field,
            "chosen_fact_id": chosen_fact_id,
            "rationale": rationale,
            "evidence_ack": True,
        },
        format="json",
    )


def _post_defer(client, workspace, *, field, rationale="defer for follow-up"):
    return client.post(
        reverse("review-workspace-conflict-defer", args=[workspace.external_id]),
        {"field": field, "rationale": rationale},
        format="json",
    )


def _conflict(workspace, field):
    return next(
        c for c in workspace.reviewed_state.get("conflicts") or [] if c.get("field") == field
    )


@pytest.mark.django_db
def test_resolved_is_terminal_resolve_then_defer_does_not_unresolve() -> None:
    """Once resolved, defer cannot revert — resolved=True must persist."""
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="WS-terminal", owner=user)
    field = "people[0].date_of_birth"
    fact_a, _ = _seed_conflict(workspace, field=field)

    assert _post_resolve(client, workspace, field=field, chosen_fact_id=fact_a).status_code == 200
    _post_defer(client, workspace, field=field, rationale="try to revert resolution")
    workspace.refresh_from_db()
    target = _conflict(workspace, field)
    assert target.get("resolved") is True
    assert target.get("chosen_fact_id") == fact_a


@pytest.mark.django_db
def test_resurfaced_only_reachable_from_deferred() -> None:
    """A new fact on an ACTIVE (never-deferred) conflict must NOT set
    re_surfaced_at.
    """
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="WS-active", owner=user)
    field = "people[0].date_of_birth"
    _seed_conflict(workspace, field=field)

    new_doc = _doc(workspace, filename="kyc3.pdf", document_type="kyc")
    _fact(workspace, new_doc, field=field, value="value-c")
    fresh_state = reviewed_state_from_workspace(workspace)
    target = next(c for c in fresh_state.get("conflicts") or [] if c.get("field") == field)
    assert target.get("re_surfaced_at") in (None, "")
    assert target.get("deferred") is not True


@pytest.mark.django_db
def test_resurface_requires_new_fact_id() -> None:
    """re_surfaced_at is set only after defer + a NEW fact_id."""
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="WS-resurf", owner=user)
    field = "people[0].date_of_birth"
    _seed_conflict(workspace, field=field)
    assert _post_defer(client, workspace, field=field).status_code == 200

    workspace.refresh_from_db()
    fresh_state = reviewed_state_from_workspace(workspace)
    target = next(c for c in fresh_state.get("conflicts") or [] if c.get("field") == field)
    assert target.get("deferred") is True
    assert target.get("re_surfaced_at") in (None, "")

    new_doc = _doc(workspace, filename="kyc-v3.pdf", document_type="kyc")
    _fact(workspace, new_doc, field=field, value="value-c")
    fresh_state = reviewed_state_from_workspace(workspace)
    target = next(c for c in fresh_state.get("conflicts") or [] if c.get("field") == field)
    assert target.get("re_surfaced_at"), "expected re_surfaced_at after new fact arrives"


@pytest.mark.django_db
@given(transitions=st.lists(st.sampled_from(["resolve", "defer"]), min_size=1, max_size=6))
@settings(**HYPO_SETTINGS)
def test_property_audit_emission_one_event_per_state_transition(transitions) -> None:
    """Each successful POST emits exactly ONE audit event of the
    expected kind. 4xx responses emit nothing.
    """
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="WS-tx", owner=user)
    field = "people[0].date_of_birth"
    fact_a, _ = _seed_conflict(workspace, field=field)

    expected_resolved = 0
    expected_deferred = 0
    for action in transitions:
        if action == "resolve":
            response = _post_resolve(client, workspace, field=field, chosen_fact_id=fact_a)
            if response.status_code == 200:
                expected_resolved += 1
        else:
            response = _post_defer(client, workspace, field=field)
            if response.status_code == 200:
                expected_deferred += 1
        assert response.status_code in {200, 400, 404}, response.content

    assert (
        AuditEvent.objects.filter(
            action="review_conflict_resolved", entity_id=workspace.external_id
        ).count()
        == expected_resolved
    )
    assert (
        AuditEvent.objects.filter(
            action="review_conflict_deferred", entity_id=workspace.external_id
        ).count()
        == expected_deferred
    )


@pytest.mark.django_db
@given(field=st.sampled_from(CONFLICT_FIELDS), values=st.lists(SAFE_VALUE, min_size=2, max_size=4))
@settings(**HYPO_SETTINGS)
def test_property_one_open_conflict_per_field(field, values) -> None:
    """reviewed_state.conflicts has at most ONE entry per field path,
    regardless of how many extracted facts exist for that field.
    """
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="WS-one", owner=user)

    seen_values: set[str] = set()
    for i, value in enumerate(values):
        doc = _doc(workspace, filename=f"kyc{i}.pdf", document_type="kyc")
        _fact(workspace, doc, field=field, value=value)
        seen_values.add(value)

    fresh_state = reviewed_state_from_workspace(workspace)
    field_conflicts = [c for c in fresh_state.get("conflicts") or [] if c.get("field") == field]
    if len(seen_values) >= 2:
        assert len(field_conflicts) == 1
        assert len(field_conflicts[0]["fact_ids"]) >= 2
    else:
        assert field_conflicts == []


@pytest.mark.django_db
@given(rationale=SAFE_RATIONALE)
@settings(**HYPO_SETTINGS)
def test_property_double_resolve_idempotent_resolved_remains_true(rationale) -> None:
    """A second resolve attempt may 200 (rationale revision) or 4xx,
    but resolved must remain True throughout.
    """
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = models.ReviewWorkspace.objects.create(label="WS-double", owner=user)
    field = "people[0].date_of_birth"
    fact_a, fact_b = _seed_conflict(workspace, field=field)

    r1 = _post_resolve(client, workspace, field=field, chosen_fact_id=fact_a, rationale=rationale)
    assert r1.status_code == 200, r1.content
    r2 = _post_resolve(client, workspace, field=field, chosen_fact_id=fact_b, rationale=rationale)
    assert r2.status_code in {200, 400, 409}, r2.content
    workspace.refresh_from_db()
    assert _conflict(workspace, field).get("resolved") is True
