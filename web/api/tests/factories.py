"""factory_boy fixtures for MP2.0 backend tests.

Centralizes entity construction for the new edge-case + PII-adversarial
+ DB-invariant test suites (2026-05-03). Mirrors the ad-hoc helpers
already in `web/api/tests/test_phase5b_*.py` (the `_user`, `_doc`,
`_fact`, `_workspace` helpers) so existing tests can migrate
incrementally.

Conventions:
  * Every factory uses `DjangoModelFactory` + `SubFactory`, never
    `Faker(...)` for FK fields.
  * `ReviewDocumentFactory.sha256` is derived deterministically from
    `original_filename` so multi-doc tests that call
    `ReviewDocumentFactory(workspace=ws)` twice with different filenames
    don't collide on the unique-per-workspace sha256 constraint.
  * `data_origin` defaults to `synthetic` so a stray test never tags
    real-PII discipline accidentally.
  * Faker localization is `en_CA` to keep date/phone shapes plausible
    for Canadian-advisor scenarios; values are still synthetic.
"""

from __future__ import annotations

import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory
from web.api import models


class UserFactory(DjangoModelFactory):
    class Meta:
        model = get_user_model()
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"advisor{n}@example.com")
    email = factory.LazyAttribute(lambda obj: obj.username)
    is_active = True
    password = factory.PostGenerationMethodCall("set_password", "pw")


class ReviewWorkspaceFactory(DjangoModelFactory):
    class Meta:
        model = models.ReviewWorkspace

    label = factory.Faker("sentence", nb_words=3)
    owner = factory.SubFactory(UserFactory)
    # Synthetic by default so tests can't accidentally trip the
    # real-PII discipline. Real-PII suites override explicitly.
    data_origin = models.ReviewWorkspace.DataOrigin.SYNTHETIC
    status = models.ReviewWorkspace.Status.DRAFT


class ReviewDocumentFactory(DjangoModelFactory):
    class Meta:
        model = models.ReviewDocument

    workspace = factory.SubFactory(ReviewWorkspaceFactory)
    original_filename = factory.Sequence(lambda n: f"doc_{n}.pdf")
    content_type = "application/pdf"
    extension = "pdf"
    file_size = 1024
    document_type = "kyc"
    status = models.ReviewDocument.Status.RECONCILED

    # Per-workspace sha256 must be unique (DB constraint). Generate one
    # from the supplied filename so multi-doc tests don't collide.
    sha256 = factory.LazyAttribute(
        lambda obj: (obj.original_filename.encode().hex() + "0" * 64)[:64]
    )
    storage_path = factory.LazyAttribute(
        lambda obj: f"workspace_{obj.workspace.external_id}/{obj.original_filename}"
    )
    processing_metadata = factory.LazyFunction(
        lambda: {
            "extraction_version": "extraction.v2",
            "review_schema_version": "reviewed_client_state.v1",
        }
    )


class ExtractedFactFactory(DjangoModelFactory):
    class Meta:
        model = models.ExtractedFact

    workspace = factory.SubFactory(ReviewWorkspaceFactory)
    document = factory.SubFactory(
        ReviewDocumentFactory,
        workspace=factory.SelfAttribute("..workspace"),
    )
    field = "people[0].date_of_birth"
    # ExtractedFact.value is a JSONField → use a Faker-string so we
    # don't depend on a custom JSON encoder for native date objects.
    value = factory.Faker("date", pattern="%Y-%m-%d")
    confidence = models.ExtractedFact.Confidence.MEDIUM
    derivation_method = models.ExtractedFact.DerivationMethod.EXTRACTED
    source_location = "page 1"
    source_page = 1
    evidence_quote = ""
    extraction_run_id = factory.Sequence(lambda n: f"run-{n}")
    is_current = False


class FeedbackFactory(DjangoModelFactory):
    class Meta:
        model = models.Feedback

    advisor = factory.SubFactory(UserFactory)
    severity = factory.Iterator(
        [
            models.Feedback.Severity.BLOCKING,
            models.Feedback.Severity.FRICTION,
            models.Feedback.Severity.SUGGESTION,
        ]
    )
    description = factory.Faker("paragraph", nb_sentences=2)
    route = "/review/example"
    status = models.Feedback.Status.NEW


class FactOverrideFactory(DjangoModelFactory):
    class Meta:
        model = models.FactOverride

    workspace = factory.SubFactory(ReviewWorkspaceFactory)
    field = "people[0].date_of_birth"
    value = "1985-03-12"
    rationale = factory.Faker("sentence", nb_words=10)
    is_added = False
    created_by = factory.SubFactory(UserFactory)
