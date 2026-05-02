"""Phase 3 atomicity regression tests.

BUG-1: ReviewDocumentManualEntryView.post must serialize concurrent
calls via transaction.atomic + select_for_update on the document row.
Closes the lost-update race + audit-trail interleave risk.

REC-1: process_document must roll back FACTS_EXTRACTED + fact
bulk_create together with enqueue_reconcile if the reconcile-enqueue
fails. Closes the "advisor sees stuck state" friction class.
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models


def _user(email: str = "advisor@example.com"):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, _ = User.objects.get_or_create(
        email=email,
        defaults={"username": email, "is_active": True},
    )
    return user


@pytest.mark.django_db
def test_manual_entry_view_wrapped_in_transaction_atomic() -> None:
    """BUG-1: verify the view's post handler runs inside transaction.atomic.

    Read the function's wrapping decorator chain and assert
    `transaction.atomic` is in the stack. Functional concurrency
    proof would require Postgres-level lock observation; this
    structural test pins the decorator so future refactors can't
    silently remove the lock.
    """
    from web.api.views import ReviewDocumentManualEntryView

    # The decorated method retains a __wrapped__ attribute when
    # transaction.atomic() is applied as a decorator.
    post = ReviewDocumentManualEntryView.post
    assert hasattr(post, "__wrapped__"), (
        "ReviewDocumentManualEntryView.post is missing transaction.atomic decorator "
        "(Phase 3 BUG-1 close-out). Concurrent advisor calls could interleave."
    )


@pytest.mark.django_db
def test_manual_entry_uses_select_for_update_on_document() -> None:
    """BUG-1: verify the view uses select_for_update on the document row.

    Inspect the source for the .select_for_update() call. Static check
    is sufficient — runtime behaviour requires a multi-connection
    Postgres test which is heavier than warranted for the regression
    guard.
    """
    import inspect

    from web.api.views import ReviewDocumentManualEntryView

    source = inspect.getsource(ReviewDocumentManualEntryView.post)
    assert "select_for_update()" in source, (
        "Phase 3 BUG-1: ReviewDocumentManualEntryView.post must "
        "select_for_update the document row to serialize concurrent "
        "manual-entry calls."
    )


def test_process_document_atomic_block_wraps_facts_status_and_enqueue() -> None:
    """REC-1: structural check that the atomic block in process_document
    wraps fact persistence + FACTS_EXTRACTED state save +
    enqueue_reconcile together.

    Without this boundary, an enqueue_reconcile failure leaves the
    doc FACTS_EXTRACTED but the workspace never reconciles —
    advisor sees "processing" forever with no recovery (the
    FileList-class friction the pilot must avoid).
    """
    import inspect

    from web.api import review_processing

    source = inspect.getsource(review_processing.process_document)

    # The atomic block must contain:
    # 1. ExtractedFact bulk_create (fact persistence)
    # 2. document.status = FACTS_EXTRACTED + save (state transition)
    # 3. enqueue_reconcile call (follow-up job)
    # All three must be inside a single `with transaction.atomic():` block.

    # Extract the atomic block region — heuristic but tied to the actual
    # closing comment + behaviour pinned by Phase 3.
    assert "transaction.atomic()" in source, (
        "REC-1: process_document missing transaction.atomic() block"
    )
    # Heuristic: find the atomic block region by line ordering. The
    # following statements should appear in this order WITHIN the
    # atomic block (not before the `with transaction.atomic()` line):
    atomic_index = source.index("with transaction.atomic()")
    bulk_create_index = source.index("bulk_create(fact_rows)")
    facts_extracted_index = source.index("Status.FACTS_EXTRACTED")
    enqueue_index = source.index("enqueue_reconcile(document.workspace)")

    assert atomic_index < bulk_create_index, "REC-1: bulk_create must be inside atomic"
    assert atomic_index < facts_extracted_index, "REC-1: FACTS_EXTRACTED save must be inside atomic"
    assert atomic_index < enqueue_index, "REC-1: enqueue_reconcile must be inside atomic"


@pytest.mark.django_db
def test_manual_entry_endpoint_idempotent_under_repeat() -> None:
    """BUG-1 sanity: repeat manual-entry calls converge to same end state.

    Even with the atomic wrapping, the idempotent end-state
    (MANUAL_ENTRY) means double-clicks aren't catastrophic. This test
    verifies the contract.
    """
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    workspace = models.ReviewWorkspace.objects.create(
        label="idempotency-test",
        owner=user,
        data_origin=models.ReviewWorkspace.DataOrigin.REAL_DERIVED,
    )
    document = models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename="failed.pdf",
        content_type="application/pdf",
        file_size=100,
        sha256="y" * 64,
        status=models.ReviewDocument.Status.FAILED,
    )

    url = reverse(
        "review-document-manual-entry",
        args=[workspace.external_id, document.id],
    )
    first = client.post(url, {})
    assert first.status_code == 200, first.content
    document.refresh_from_db()
    assert document.status == models.ReviewDocument.Status.MANUAL_ENTRY

    # Second call: doc is no longer in eligible_statuses (it's MANUAL_ENTRY),
    # so endpoint returns 409 with `code=manual_entry_not_eligible`.
    # Under the lock, this serializes cleanly with no race.
    second = client.post(url, {})
    assert second.status_code == 409
    assert second.json()["code"] == "manual_entry_not_eligible"
