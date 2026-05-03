"""Sanity tests for the factory_boy fixtures (web/api/tests/factories.py).

These don't exercise production code; they verify the factories
themselves stay in shape so the rest of the new test suites can rely
on them.
"""

from __future__ import annotations

import factory
import factory.random
import pytest
from faker import Faker
from web.api.tests.factories import (
    ExtractedFactFactory,
    FactOverrideFactory,
    FeedbackFactory,
    ReviewDocumentFactory,
    ReviewWorkspaceFactory,
    UserFactory,
)


@pytest.mark.django_db
def test_factory_creates_valid_user() -> None:
    """UserFactory must produce a saved auth.User with a non-null pk."""
    user = UserFactory()
    assert user.pk is not None
    assert user.username == user.email
    assert user.is_active is True


@pytest.mark.django_db
def test_factory_seed_reproducible() -> None:
    """Faker seed determinism — set the seed, generate twice, identical.

    Lets future test authors pin a synthetic value (DOB, name) and
    rely on the same factory generating identical content across runs.

    The user-factory's ``username`` is a Sequence (monotonic), so we
    pin reproducibility by re-running the Faker-driven `label` /
    `description` paths instead.
    """
    Faker.seed(20260503)
    factory.random.reseed_random(20260503)
    workspace1 = ReviewWorkspaceFactory.build()
    feedback1 = FeedbackFactory.build()

    Faker.seed(20260503)
    factory.random.reseed_random(20260503)
    workspace2 = ReviewWorkspaceFactory.build()
    feedback2 = FeedbackFactory.build()

    assert workspace1.label == workspace2.label
    assert feedback1.description == feedback2.description


@pytest.mark.django_db
def test_factory_workspace_defaults_to_synthetic_origin() -> None:
    """Real-PII discipline: a stray factory-built workspace is synthetic."""
    workspace = ReviewWorkspaceFactory()
    assert workspace.data_origin == "synthetic"
    assert workspace.owner is not None


@pytest.mark.django_db
def test_factory_review_document_sha_deterministic_per_filename() -> None:
    """Per-workspace sha256 unique constraint is satisfied by the
    filename-derived digest in ReviewDocumentFactory.
    """
    workspace = ReviewWorkspaceFactory()
    doc1 = ReviewDocumentFactory(workspace=workspace, original_filename="kyc.pdf")
    doc2 = ReviewDocumentFactory(workspace=workspace, original_filename="statement.pdf")
    assert doc1.sha256 != doc2.sha256
    # Same filename -> same digest -> would violate the unique
    # constraint, which proves determinism. (Don't actually try
    # to create the duplicate — the test verifies the function.)
    expected = (b"kyc.pdf".hex() + "0" * 64)[:64]
    assert doc1.sha256 == expected


@pytest.mark.django_db
def test_factory_extracted_fact_carries_workspace_and_document() -> None:
    """ExtractedFactFactory composes via SubFactory; workspace match."""
    fact = ExtractedFactFactory()
    assert fact.workspace is not None
    assert fact.document is not None
    assert fact.document.workspace_id == fact.workspace_id
    # The post-generation hook serializes Faker's date to ISO string.
    assert isinstance(fact.value, str)
    assert len(fact.value) == 10  # YYYY-MM-DD


@pytest.mark.django_db
def test_factory_feedback_creates_valid_row() -> None:
    feedback = FeedbackFactory()
    assert feedback.pk is not None
    assert feedback.advisor is not None
    assert feedback.severity in {"blocking", "friction", "suggestion"}
    assert feedback.status == "new"


@pytest.mark.django_db
def test_factory_fact_override_creates_valid_row() -> None:
    override = FactOverrideFactory()
    assert override.pk is not None
    assert override.workspace is not None
    assert override.created_by is not None
    assert override.field == "people[0].date_of_birth"
    assert override.is_added is False
