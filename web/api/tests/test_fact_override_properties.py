"""Hypothesis property tests — FactOverride append-only invariants.

Properties asserted:
  1. N edits to the same (workspace, field) ⇒ exactly N rows; never UPDATE.
  2. Latest-row-wins per (workspace, field): _latest_overrides() returns
     the row with the highest created_at.
  3. Audit emission is 1:1 with FactOverride rows
     (count(review_fact_overridden) == count(FactOverride rows)).
  4. Latest-row-wins applies independently per field group.
"""

from __future__ import annotations

import uuid

import hypothesis.strategies as st
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from hypothesis import HealthCheck, given, settings
from rest_framework.test import APIClient
from web.api import models
from web.api.review_state import _latest_overrides
from web.audit.models import AuditEvent

CANONICAL_FIELDS = [
    "people[0].date_of_birth",
    "people[0].marital_status",
    "accounts[0].current_value",
    "goals[0].name",
]

# ASCII-only strategies sidestep unrelated Postgres unicode-JSON edge cases;
# the properties under test are character-set independent.
SAFE_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-:."

field_strategy = st.sampled_from(CANONICAL_FIELDS)
value_strategy = st.text(alphabet=SAFE_CHARS, min_size=1, max_size=20).map(
    lambda s: s.strip() or "x"
)
rationale_strategy = st.text(alphabet=SAFE_CHARS, min_size=4, max_size=80).map(
    lambda s: s if len(s.strip()) >= 4 else "rationale_min"
)

HYPO_SETTINGS = dict(
    max_examples=50,
    deadline=2000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


def _user() -> object:
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="advisor@example.com",
        defaults={"email": "advisor@example.com", "is_active": True},
    )
    return user


def _fresh_workspace(user) -> models.ReviewWorkspace:
    """Each Hypothesis example gets a brand-new workspace so per-workspace
    counts (rows/audit events) are independent of prior examples.
    """
    return models.ReviewWorkspace.objects.create(label=f"WS-{uuid.uuid4()}", owner=user)


def _post_override(client: APIClient, workspace, *, field, value, rationale):
    return client.post(
        reverse("review-workspace-fact-override", args=[workspace.external_id]),
        {"field": field, "value": value, "rationale": rationale, "is_added": False},
        format="json",
    )


@pytest.mark.django_db
@given(edits=st.lists(st.tuples(value_strategy, rationale_strategy), min_size=1, max_size=10))
@settings(**HYPO_SETTINGS)
def test_property_n_edits_yield_n_rows_never_update(edits) -> None:
    """N successful POSTs to the same (workspace, field) ⇒ exactly N
    append-only rows. Locks the canon §11.4 + locked-2026-05-02
    append-only invariant.
    """
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = _fresh_workspace(user)

    field = "people[0].date_of_birth"
    successful_posts = 0
    for value, rationale in edits:
        response = _post_override(client, workspace, field=field, value=value, rationale=rationale)
        if response.status_code == 200:
            successful_posts += 1
        else:
            assert response.status_code == 400, response.content

    rows = list(workspace.fact_overrides.filter(field=field))
    assert len(rows) == successful_posts
    assert len({row.pk for row in rows}) == len(rows)  # distinct pks ⇒ no UPDATE


@pytest.mark.django_db
@given(values=st.lists(value_strategy, min_size=2, max_size=10))
@settings(**HYPO_SETTINGS)
def test_property_latest_row_wins_per_field(values) -> None:
    """Edit sequence A → B → C ⇒ _latest_overrides()[field].value == C."""
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = _fresh_workspace(user)

    field = "people[0].marital_status"
    last_accepted_value: str | None = None
    for value in values:
        response = _post_override(
            client, workspace, field=field, value=value, rationale="advisor edit per review"
        )
        if response.status_code == 200:
            last_accepted_value = value
        else:
            assert response.status_code == 400, response.content

    if last_accepted_value is None:
        assert field not in _latest_overrides(workspace)
        return

    latest = _latest_overrides(workspace)
    assert field in latest
    assert latest[field].value == last_accepted_value


@pytest.mark.django_db
@given(
    posts=st.lists(
        st.tuples(field_strategy, value_strategy, rationale_strategy), min_size=1, max_size=12
    )
)
@settings(**HYPO_SETTINGS)
def test_property_audit_event_count_matches_row_count(posts) -> None:
    """count(AuditEvent[review_fact_overridden]) == count(FactOverride rows).

    Locks decision #37 (one audit event per state-changing action)
    plus PII discipline (rationale_len in metadata; never the text).
    """
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = _fresh_workspace(user)

    successful_posts = 0
    for field, value, rationale in posts:
        response = _post_override(client, workspace, field=field, value=value, rationale=rationale)
        if response.status_code == 200:
            successful_posts += 1
        else:
            assert response.status_code == 400, response.content

    row_count = workspace.fact_overrides.count()
    audit_count = AuditEvent.objects.filter(
        action="review_fact_overridden", entity_id=workspace.external_id
    ).count()
    assert row_count == successful_posts
    assert audit_count == row_count

    for event in AuditEvent.objects.filter(
        action="review_fact_overridden", entity_id=workspace.external_id
    ):
        metadata = event.metadata or {}
        assert "rationale" not in metadata
        assert "rationale_len" in metadata


@pytest.mark.django_db
@given(edit_plan=st.lists(st.tuples(field_strategy, value_strategy), min_size=1, max_size=12))
@settings(**HYPO_SETTINGS)
def test_property_latest_row_wins_per_field_group(edit_plan) -> None:
    """Across multiple fields, _latest_overrides() returns the latest
    row PER field group — independent of cross-field interleaving.
    """
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = _fresh_workspace(user)

    expected_latest: dict[str, str] = {}
    for field, value in edit_plan:
        response = _post_override(
            client, workspace, field=field, value=value, rationale="advisor edit"
        )
        if response.status_code == 200:
            expected_latest[field] = value
        else:
            assert response.status_code == 400, response.content

    latest = _latest_overrides(workspace)
    for field, expected_value in expected_latest.items():
        assert field in latest
        assert latest[field].value == expected_value
    assert set(latest.keys()) == set(expected_latest.keys())


@pytest.mark.django_db
def test_model_save_raises_on_existing_pk() -> None:
    """Append-only model guard: save() on an existing pk raises.

    Deterministic check — the model invariant is unconditional, so a
    single trip through the guard is enough.
    """
    user = _user()
    workspace = models.ReviewWorkspace.objects.create(label="WS", owner=user)
    override = models.FactOverride.objects.create(
        workspace=workspace,
        field="people[0].date_of_birth",
        value="1985-03-12",
        rationale="initial",
        is_added=False,
        created_by=user,
    )
    override.value = "1985-03-15"
    with pytest.raises(Exception, match="append-only"):
        override.save()
