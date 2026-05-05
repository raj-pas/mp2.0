"""Auth + RBAC matrix tests across the review/disclaimer/tour/feedback surface.

For every state-changing endpoint listed in the prompt, this suite
asserts the four-cell role-matrix:

  1. Advisor (PII-able) + valid workspace → 2xx or 4xx-validation
     (`PASS_THROUGH`) — auth let the request through, validation
     happened downstream. NEVER 401/403.
  2. Advisor (PII-able) + nonexistent workspace → 404.
  3. Financial analyst (NO PII access) + ANY workspace → 403.
  4. Anonymous (no auth) → 401 or 403.

For non-workspace endpoints (disclaimer, tour, feedback): both
roles are allowed (no PII gate). feedback/report is FA-only by
design — advisor gets 403, FA gets 200.

Pattern: parametrize (route, method, needs_doc, body_factory) so
each endpoint × role-cell yields one test case. PASS_THROUGH
includes 404 because conflict-* endpoints return
`conflict_not_found` when the inner conflict slot doesn't match —
that's a domain 404, not a role-leak. The workspace-level 404 is
covered by a separate test cell.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models
from web.api.access import FINANCIAL_ANALYST_GROUP
from web.api.review_state import reviewed_state_from_workspace as _rebuild_state

# Auth-passes status codes (NOT 401/403). 404 included for inner-
# entity-not-found responses on workspace-scoped routes.
PASS_THROUGH = {200, 201, 202, 204, 400, 404, 409, 422, 503}


# --- Fixtures / helpers ---------------------------------------------


def _advisor(email: str = "advisor@example.com"):
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        email=email, defaults={"username": email, "is_active": True}
    )
    return user


def _analyst(email: str = "analyst@example.com"):
    user = _advisor(email)
    group, _ = Group.objects.get_or_create(name=FINANCIAL_ANALYST_GROUP)
    user.groups.add(group)
    return user


def _workspace(owner) -> models.ReviewWorkspace:
    return models.ReviewWorkspace.objects.create(
        label="auth-matrix-ws",
        owner=owner,
        data_origin=models.ReviewWorkspace.DataOrigin.SYNTHETIC,
    )


def _doc(workspace, *, status: str = "failed") -> models.ReviewDocument:
    return models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="auth-matrix.pdf",
        content_type="application/pdf",
        extension="pdf",
        file_size=128,
        sha256="d" * 64,
        storage_path=f"workspace_{workspace.external_id}/auth-matrix.pdf",
        status=status,
    )


def _client_for(user=None) -> APIClient:
    """user=None returns an anonymous client."""
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


def _bogus_workspace_id() -> str:
    return "00000000-0000-0000-0000-000000000000"


# --- Workspace-scoped endpoint table --------------------------------
#
# (test_id, route_name, method, needs_doc, body). Each row is
# parametrized into 3 role-cells (advisor-valid, FA-blocked,
# anonymous-blocked). The 404 cell uses a subset (no list/create).

_RESOLVE_BODY = {
    "field": "people[0].age",
    "chosen_fact_id": 1,
    "rationale": "matrix",
    "evidence_ack": True,
}
_BULK_BODY = {
    "resolutions": [{"field": "x", "chosen_fact_id": 1}],
    "rationale": "matrix",
    "evidence_ack": True,
}
_DEFER_BODY = {"field": "x", "rationale": "matrix matrix"}
_OVERRIDE_BODY = {
    "field": "people[0].dob",
    "value": "1985-03-12",
    "rationale": "matrix matrix",
    "is_added": False,
}
_APPROVE_BODY = {"section": "people", "status": "approved"}
_LIST_POST_BODY = {"label": "matrix-ws", "data_origin": "synthetic"}
_UPLOAD_BODY = {
    "files": [SimpleUploadedFile("a.pdf", b"%PDF-1.4\n%fake\n", content_type="application/pdf")]
}

WORKSPACE_ENDPOINTS = [
    ("review-workspace-detail-get", "review-workspace-detail", "get", False, None),
    ("review-workspace-upload", "review-workspace-upload", "post-multipart", False, _UPLOAD_BODY),
    ("review-document-detail-get", "review-document-detail", "get", True, None),
    ("review-document-retry", "review-document-retry", "post", True, {}),
    ("review-document-manual-entry", "review-document-manual-entry", "post", True, {}),
    ("review-workspace-state-get", "review-workspace-state", "get", False, None),
    ("review-workspace-state-patch", "review-workspace-state", "patch", False, {"state": {}}),
    ("review-conflict-resolve", "review-workspace-conflict-resolve", "post", False, _RESOLVE_BODY),
    (
        "review-conflict-bulk-resolve",
        "review-workspace-conflict-bulk-resolve",
        "post",
        False,
        _BULK_BODY,
    ),
    ("review-conflict-defer", "review-workspace-conflict-defer", "post", False, _DEFER_BODY),
    ("review-fact-override", "review-workspace-fact-override", "post", False, _OVERRIDE_BODY),
    ("review-section-approve", "review-workspace-approve-section", "post", False, _APPROVE_BODY),
    ("review-commit", "review-workspace-commit", "post", False, {}),
    ("review-manual-reconcile", "review-workspace-manual-reconcile", "post", False, {}),
    ("review-workspace-list-get", "review-workspace-list", "get", False, None),
    ("review-workspace-list-post", "review-workspace-list", "post", False, _LIST_POST_BODY),
]


def _call(client, route, method, body, *, ws_id, doc_id):
    """Dispatch the configured route + method via APIClient."""
    if route == "review-workspace-list":
        url = reverse(route)
    elif doc_id is not None:
        url = reverse(route, args=[ws_id, doc_id])
    else:
        url = reverse(route, args=[ws_id])

    if method == "get":
        return client.get(url)
    if method == "post":
        return client.post(url, body or {}, format="json")
    if method == "post-multipart":
        files = (body or {}).get("files") or []
        return client.post(url, {"files": files}, format="multipart")
    if method == "patch":
        return client.patch(url, body or {}, format="json")
    raise AssertionError(f"unknown method: {method}")


# --- 1. Advisor + valid workspace → access permitted ---------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name, route, method, needs_doc, body",
    WORKSPACE_ENDPOINTS,
    ids=[row[0] for row in WORKSPACE_ENDPOINTS],
)
def test_advisor_workspace_endpoint_passes_auth(name, route, method, needs_doc, body) -> None:
    advisor = _advisor()
    workspace = _workspace(advisor)
    doc = _doc(workspace) if needs_doc else None
    client = _client_for(advisor)
    response = _call(
        client,
        route,
        method,
        body,
        ws_id=workspace.external_id if route != "review-workspace-list" else None,
        doc_id=(doc.id if doc else None),
    )
    assert response.status_code in PASS_THROUGH, (
        f"[{name}] advisor + valid workspace blocked at auth/RBAC layer: "
        f"got {response.status_code}; possible role-leak. "
        f"Body: {response.content[:200]!r}"
    )


# --- 2. Advisor + nonexistent workspace → 404 ----------------------

WORKSPACE_404_ENDPOINTS = [row for row in WORKSPACE_ENDPOINTS if row[1] != "review-workspace-list"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name, route, method, needs_doc, body",
    WORKSPACE_404_ENDPOINTS,
    ids=[row[0] for row in WORKSPACE_404_ENDPOINTS],
)
def test_advisor_unknown_workspace_returns_404(name, route, method, needs_doc, body) -> None:
    advisor = _advisor()
    client = _client_for(advisor)
    response = _call(
        client,
        route,
        method,
        body,
        ws_id=_bogus_workspace_id(),
        doc_id=(999_999 if needs_doc else None),
    )
    assert response.status_code == 404, (
        f"[{name}] advisor + unknown workspace must 404 (workspace lookup "
        f"runs BEFORE input parsing). Got {response.status_code}."
    )


# --- 3. Financial analyst + ANY workspace → 403 -------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name, route, method, needs_doc, body",
    WORKSPACE_ENDPOINTS,
    ids=[row[0] for row in WORKSPACE_ENDPOINTS],
)
def test_financial_analyst_workspace_endpoint_returns_403(
    name, route, method, needs_doc, body
) -> None:
    advisor = _advisor()
    analyst = _analyst()
    workspace = _workspace(advisor)
    doc = _doc(workspace) if needs_doc else None
    client = _client_for(analyst)
    response = _call(
        client,
        route,
        method,
        body,
        ws_id=workspace.external_id if route != "review-workspace-list" else None,
        doc_id=(doc.id if doc else None),
    )
    assert response.status_code == 403, (
        f"[{name}] financial_analyst must be denied real-PII review surfaces "
        f"with 403; got {response.status_code} — possible role-leak."
    )


# --- 4. Anonymous → 401 or 403 ------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name, route, method, needs_doc, body",
    WORKSPACE_ENDPOINTS,
    ids=[row[0] for row in WORKSPACE_ENDPOINTS],
)
def test_anonymous_workspace_endpoint_returns_401_or_403(
    name, route, method, needs_doc, body
) -> None:
    advisor = _advisor()
    workspace = _workspace(advisor)
    doc = _doc(workspace) if needs_doc else None
    client = _client_for(None)
    response = _call(
        client,
        route,
        method,
        body,
        ws_id=workspace.external_id if route != "review-workspace-list" else None,
        doc_id=(doc.id if doc else None),
    )
    assert response.status_code in {401, 403}, (
        f"[{name}] anonymous request must be denied with 401 or 403; got {response.status_code}."
    )


# --- 5. Non-workspace endpoints (disclaimer, tour, feedback) -------
#
# Both advisor + analyst pass; anonymous denied. feedback/report is
# the inverse — analyst-only, advisor blocked.

NON_WORKSPACE_ENDPOINTS = [
    ("disclaimer-acknowledge", "disclaimer-acknowledge", "post", {"version": "v1"}),
    ("tour-complete", "tour-complete", "post", {}),
    (
        "feedback-submit",
        "feedback-submit",
        "post",
        {
            "severity": "friction",
            "description": "x" * 30,
            "what_were_you_trying": "matrix test",
            "route": "/auth-matrix",
        },
    ),
]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name, route, method, body",
    NON_WORKSPACE_ENDPOINTS,
    ids=[row[0] for row in NON_WORKSPACE_ENDPOINTS],
)
def test_non_workspace_endpoint_advisor_passes(name, route, method, body) -> None:
    advisor = _advisor()
    client = _client_for(advisor)
    url = reverse(route)
    response = client.post(url, body, format="json") if method == "post" else client.get(url)
    assert response.status_code in PASS_THROUGH, (
        f"[{name}] advisor on non-PII endpoint blocked: {response.status_code}"
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name, route, method, body",
    NON_WORKSPACE_ENDPOINTS,
    ids=[row[0] for row in NON_WORKSPACE_ENDPOINTS],
)
def test_non_workspace_endpoint_analyst_passes(name, route, method, body) -> None:
    """FA can also acknowledge disclaimers, complete tour, submit
    feedback — these aren't PII-gated. The analyst-only filter is
    on feedback/report (below), not the submitters.
    """
    analyst = _analyst()
    client = _client_for(analyst)
    url = reverse(route)
    response = client.post(url, body, format="json") if method == "post" else client.get(url)
    assert response.status_code in PASS_THROUGH


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name, route, method, body",
    NON_WORKSPACE_ENDPOINTS,
    ids=[row[0] for row in NON_WORKSPACE_ENDPOINTS],
)
def test_non_workspace_endpoint_anonymous_blocked(name, route, method, body) -> None:
    client = _client_for(None)
    url = reverse(route)
    response = client.post(url, body, format="json") if method == "post" else client.get(url)
    assert response.status_code in {401, 403}


# --- 6. feedback/report — analyst-only RBAC inversion --------------


@pytest.mark.django_db
def test_feedback_report_advisor_returns_403() -> None:
    client = _client_for(_advisor())
    assert client.get(reverse("feedback-report")).status_code == 403


@pytest.mark.django_db
def test_feedback_report_analyst_returns_200() -> None:
    client = _client_for(_analyst())
    assert client.get(reverse("feedback-report")).status_code == 200


@pytest.mark.django_db
def test_feedback_report_anonymous_returns_401_or_403() -> None:
    response = _client_for(None).get(reverse("feedback-report"))
    assert response.status_code in {401, 403}


# --- 7. Auto-trigger audit emission on the 4 NEW workspace-level triggers ---
#
# Per locked decisions #14 + #27 + #74: the 4 endpoints below NOW fire
# `_trigger_and_audit_for_workspace` after their canonical mutation
# audit. The pre-existing role matrix (anonymous → 401/403, FA → 403,
# advisor-in-team → 2xx) is verified above. This section adds
# assertions that for the 200-success cell, the auto-trigger fires AND
# the workspace-skip audit emits with locked metadata (the test
# workspace is unlinked → workspace-skip path; that's correct per #27).


def _seed_kyc_conflict(workspace) -> tuple[str, int]:
    """Seed a single resolvable kyc-vs-kyc conflict on people[0].dob.

    Phase P1.1 (2026-05-05): cross-document entity alignment requires
    TWO identifying fields to merge two `people[0]` references into a
    single canonical entity. We seed shared display_name + shared
    account_number so the two docs align to canonical people[0],
    exposing the DOB disagreement as a conflict on the canonical
    field. Without this, the matcher would split the two `people[0]`
    references into people[0] + people[1] (no canonical conflict).

    Returns (field, chosen_fact_id) for the resolve/defer endpoints.
    """
    kyc = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="kyc.pdf",
        content_type="application/pdf",
        extension="pdf",
        file_size=1024,
        sha256="a" * 64,
        storage_path=f"workspace_{workspace.external_id}/kyc.pdf",
        document_type="kyc",
        status=models.ReviewDocument.Status.RECONCILED,
    )
    kyc2 = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="kyc-v2.pdf",
        content_type="application/pdf",
        extension="pdf",
        file_size=1024,
        sha256="b" * 64,
        storage_path=f"workspace_{workspace.external_id}/kyc-v2.pdf",
        document_type="kyc",
        status=models.ReviewDocument.Status.RECONCILED,
    )
    # Identity anchors so alignment merges to one canonical person.
    for doc in (kyc, kyc2):
        models.ExtractedFact.objects.create(
            workspace=workspace,
            document=doc,
            field="people[0].display_name",
            value="Sarah Smith",
            confidence="high",
            derivation_method="extracted",
            source_location="page 1",
            source_page=1,
            evidence_quote="Account holder: Sarah Smith",
            extraction_run_id="run-test",
        )
        models.ExtractedFact.objects.create(
            workspace=workspace,
            document=doc,
            field="accounts[0].account_number",
            value="98765432",
            confidence="high",
            derivation_method="extracted",
            source_location="page 1",
            source_page=1,
            evidence_quote="Account: 98765432",
            extraction_run_id="run-test",
        )
    chosen = models.ExtractedFact.objects.create(
        workspace=workspace,
        document=kyc,
        field="people[0].date_of_birth",
        value="1985-03-12",
        confidence="medium",
        derivation_method="extracted",
        source_location="page 1",
        source_page=1,
        evidence_quote="evidence",
        extraction_run_id="run-test",
    )
    models.ExtractedFact.objects.create(
        workspace=workspace,
        document=kyc2,
        field="people[0].date_of_birth",
        value="1985-03-15",
        confidence="medium",
        derivation_method="extracted",
        source_location="page 1",
        source_page=1,
        evidence_quote="evidence",
        extraction_run_id="run-test",
    )
    workspace.reviewed_state = _rebuild_state(workspace)
    workspace.save(update_fields=["reviewed_state"])
    return "people[0].date_of_birth", chosen.id


def _trigger_audit_count_for_workspace(workspace, source: str) -> int:
    """Count of `portfolio_generation_skipped_post_<source>` workspace-skip
    audit rows attributed to this workspace.

    Per locked #27 + the helper at views.py:_trigger_and_audit_for_workspace,
    unlinked workspaces emit this exact action with
    `entity_type='review_workspace'` + `entity_id=workspace.external_id`.
    """
    from web.audit.models import AuditEvent

    return AuditEvent.objects.filter(
        action=f"portfolio_generation_skipped_post_{source}",
        entity_id=workspace.external_id,
        entity_type="review_workspace",
    ).count()


# --- 7a. conflicts/resolve — auto-trigger audit on 200 ---


@pytest.mark.django_db
def test_conflict_resolve_advisor_success_emits_auto_trigger_audit() -> None:
    """Advisor + valid workspace + valid resolve payload → 200 + the
    workspace-skip auto-trigger audit fires. Per locked #14 trigger #5
    + #27 unlinked-skip semantics.
    """
    advisor = _advisor()
    workspace = _workspace(advisor)
    field, fact_id = _seed_kyc_conflict(workspace)
    starting = _trigger_audit_count_for_workspace(workspace, "conflict_resolve")

    response = _client_for(advisor).post(
        reverse("review-workspace-conflict-resolve", args=[workspace.external_id]),
        {
            "field": field,
            "chosen_fact_id": fact_id,
            "rationale": "KYC supersedes statement (auth-rbac auto-trigger probe).",
            "evidence_ack": True,
        },
        format="json",
    )

    assert response.status_code == 200, (
        f"Advisor on conflicts/resolve must succeed; got "
        f"{response.status_code}: {response.content[:200]!r}"
    )
    ending = _trigger_audit_count_for_workspace(workspace, "conflict_resolve")
    assert ending - starting == 1, (
        f"Auto-trigger workspace-skip audit must fire exactly once on "
        f"successful conflicts/resolve; got delta={ending - starting}. "
        f"Per locked #14 + #27."
    )


@pytest.mark.django_db
def test_conflict_resolve_analyst_returns_403_no_auto_trigger() -> None:
    """FA + workspace conflicts/resolve → 403 + NO auto-trigger audit
    (RBAC rejects before the canonical mutation, so the trigger never
    fires).
    """
    advisor = _advisor()
    analyst = _analyst()
    workspace = _workspace(advisor)
    _seed_kyc_conflict(workspace)
    starting = _trigger_audit_count_for_workspace(workspace, "conflict_resolve")

    response = _client_for(analyst).post(
        reverse("review-workspace-conflict-resolve", args=[workspace.external_id]),
        {"field": "x", "chosen_fact_id": 1, "rationale": "matrix", "evidence_ack": True},
        format="json",
    )

    assert response.status_code == 403
    assert _trigger_audit_count_for_workspace(workspace, "conflict_resolve") == starting


@pytest.mark.django_db
def test_conflict_resolve_anonymous_returns_401_or_403_no_auto_trigger() -> None:
    """Anonymous + conflicts/resolve → 401/403 + NO auto-trigger audit."""
    advisor = _advisor()
    workspace = _workspace(advisor)
    _seed_kyc_conflict(workspace)
    starting = _trigger_audit_count_for_workspace(workspace, "conflict_resolve")

    response = _client_for(None).post(
        reverse("review-workspace-conflict-resolve", args=[workspace.external_id]),
        {"field": "x", "chosen_fact_id": 1, "rationale": "matrix", "evidence_ack": True},
        format="json",
    )

    assert response.status_code in {401, 403}
    assert _trigger_audit_count_for_workspace(workspace, "conflict_resolve") == starting


# --- 7b. conflicts/defer — auto-trigger audit on 200 ---


@pytest.mark.django_db
def test_conflict_defer_advisor_success_emits_auto_trigger_audit() -> None:
    """Advisor + valid workspace + valid defer payload → 200 + the
    workspace-skip auto-trigger audit fires. Per locked #14 trigger #6.
    """
    advisor = _advisor()
    workspace = _workspace(advisor)
    field, _ = _seed_kyc_conflict(workspace)
    starting = _trigger_audit_count_for_workspace(workspace, "defer_conflict")

    response = _client_for(advisor).post(
        reverse("review-workspace-conflict-defer", args=[workspace.external_id]),
        {"field": field, "rationale": "Decide later — auth-rbac auto-trigger probe."},
        format="json",
    )

    assert response.status_code == 200, response.content[:200]
    ending = _trigger_audit_count_for_workspace(workspace, "defer_conflict")
    assert ending - starting == 1


@pytest.mark.django_db
def test_conflict_defer_analyst_returns_403_no_auto_trigger() -> None:
    advisor = _advisor()
    analyst = _analyst()
    workspace = _workspace(advisor)
    _seed_kyc_conflict(workspace)
    starting = _trigger_audit_count_for_workspace(workspace, "defer_conflict")

    response = _client_for(analyst).post(
        reverse("review-workspace-conflict-defer", args=[workspace.external_id]),
        {"field": "x", "rationale": "matrix matrix"},
        format="json",
    )

    assert response.status_code == 403
    assert _trigger_audit_count_for_workspace(workspace, "defer_conflict") == starting


@pytest.mark.django_db
def test_conflict_defer_anonymous_returns_401_or_403_no_auto_trigger() -> None:
    advisor = _advisor()
    workspace = _workspace(advisor)
    _seed_kyc_conflict(workspace)
    starting = _trigger_audit_count_for_workspace(workspace, "defer_conflict")

    response = _client_for(None).post(
        reverse("review-workspace-conflict-defer", args=[workspace.external_id]),
        {"field": "x", "rationale": "matrix matrix"},
        format="json",
    )

    assert response.status_code in {401, 403}
    assert _trigger_audit_count_for_workspace(workspace, "defer_conflict") == starting


# --- 7c. facts/override — auto-trigger audit on 200 ---


@pytest.mark.django_db
def test_fact_override_advisor_success_emits_auto_trigger_audit() -> None:
    """Advisor + valid workspace + valid override payload → 200 + the
    workspace-skip auto-trigger audit fires. Per locked #14 trigger #7.
    """
    advisor = _advisor()
    workspace = _workspace(advisor)
    starting = _trigger_audit_count_for_workspace(workspace, "fact_override")

    response = _client_for(advisor).post(
        reverse("review-workspace-fact-override", args=[workspace.external_id]),
        {
            "field": "people[0].date_of_birth",
            "value": "1985-03-12",
            "rationale": "Auth-rbac auto-trigger probe override.",
            "is_added": False,
        },
        format="json",
    )

    assert response.status_code == 200, response.content[:200]
    ending = _trigger_audit_count_for_workspace(workspace, "fact_override")
    assert ending - starting == 1


@pytest.mark.django_db
def test_fact_override_analyst_returns_403_no_auto_trigger() -> None:
    advisor = _advisor()
    analyst = _analyst()
    workspace = _workspace(advisor)
    starting = _trigger_audit_count_for_workspace(workspace, "fact_override")

    response = _client_for(analyst).post(
        reverse("review-workspace-fact-override", args=[workspace.external_id]),
        {
            "field": "people[0].dob",
            "value": "1985-03-12",
            "rationale": "matrix matrix",
            "is_added": False,
        },
        format="json",
    )

    assert response.status_code == 403
    assert _trigger_audit_count_for_workspace(workspace, "fact_override") == starting


@pytest.mark.django_db
def test_fact_override_anonymous_returns_401_or_403_no_auto_trigger() -> None:
    advisor = _advisor()
    workspace = _workspace(advisor)
    starting = _trigger_audit_count_for_workspace(workspace, "fact_override")

    response = _client_for(None).post(
        reverse("review-workspace-fact-override", args=[workspace.external_id]),
        {
            "field": "people[0].dob",
            "value": "1985-03-12",
            "rationale": "matrix matrix",
            "is_added": False,
        },
        format="json",
    )

    assert response.status_code in {401, 403}
    assert _trigger_audit_count_for_workspace(workspace, "fact_override") == starting


# --- 7d. sections/<key>/approve — auto-trigger audit on 200 ---


def _engine_ready_state_for_approval() -> dict:
    """Minimal reviewed-state where the `risk` section has no blockers,
    so plain APPROVED succeeds. Mirrors the canonical
    `_engine_ready_state` shape from test_review_ingestion.py inline.
    """
    return {
        "schema_version": "reviewed_client_state.v1",
        "household": {
            "display_name": "Auth-RBAC Auto-trigger",
            "household_type": "couple",
            "household_risk_score": 3,
        },
        "people": [{"id": "person_1", "name": "A", "age": 60}],
        "accounts": [
            {
                "id": "acct_1",
                "type": "RRSP",
                "current_value": 100000,
                "missing_holdings_confirmed": True,
            }
        ],
        "goals": [{"id": "goal_1", "name": "Retirement", "time_horizon_years": 5}],
        "goal_account_links": [
            {"goal_id": "goal_1", "account_id": "acct_1", "allocated_amount": 100000}
        ],
        "risk": {"household_score": 3},
    }


@pytest.mark.django_db
def test_section_approve_advisor_success_emits_auto_trigger_audit() -> None:
    """Advisor + valid workspace + clean reviewed_state → section
    approval succeeds → workspace-skip auto-trigger audit fires.
    Per locked #14 trigger #8.
    """
    advisor = _advisor()
    workspace = _workspace(advisor)
    workspace.reviewed_state = _engine_ready_state_for_approval()
    workspace.save(update_fields=["reviewed_state"])
    starting = _trigger_audit_count_for_workspace(workspace, "section_approve")

    response = _client_for(advisor).post(
        reverse("review-workspace-approve-section", args=[workspace.external_id]),
        {"section": "risk", "status": "approved"},
        format="json",
    )

    assert response.status_code == 200, response.content[:200]
    ending = _trigger_audit_count_for_workspace(workspace, "section_approve")
    assert ending - starting == 1


@pytest.mark.django_db
def test_section_approve_analyst_returns_403_no_auto_trigger() -> None:
    advisor = _advisor()
    analyst = _analyst()
    workspace = _workspace(advisor)
    workspace.reviewed_state = _engine_ready_state_for_approval()
    workspace.save(update_fields=["reviewed_state"])
    starting = _trigger_audit_count_for_workspace(workspace, "section_approve")

    response = _client_for(analyst).post(
        reverse("review-workspace-approve-section", args=[workspace.external_id]),
        {"section": "risk", "status": "approved"},
        format="json",
    )

    assert response.status_code == 403
    assert _trigger_audit_count_for_workspace(workspace, "section_approve") == starting


@pytest.mark.django_db
def test_section_approve_anonymous_returns_401_or_403_no_auto_trigger() -> None:
    advisor = _advisor()
    workspace = _workspace(advisor)
    workspace.reviewed_state = _engine_ready_state_for_approval()
    workspace.save(update_fields=["reviewed_state"])
    starting = _trigger_audit_count_for_workspace(workspace, "section_approve")

    response = _client_for(None).post(
        reverse("review-workspace-approve-section", args=[workspace.external_id]),
        {"section": "risk", "status": "approved"},
        format="json",
    )

    assert response.status_code in {401, 403}
    assert _trigger_audit_count_for_workspace(workspace, "section_approve") == starting
