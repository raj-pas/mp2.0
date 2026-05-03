"""Phase 6.9 — Performance budget gate (locked decision #18).

Pin endpoint latency under the canon SLO:
  - P50 (mean) < 250ms
  - P99 (max approximation via pytest-benchmark) < 1000ms

pytest-benchmark runs each scenario `--benchmark-min-rounds=20`
times to get statistically meaningful measurements. Thresholds
are intentionally conservative: a Bedrock-bound real-PII workspace
spends most of its time on the upload/extraction path (out of scope
for these benchmarks); the endpoints under test here are the
synchronous in-process write/read paths that an advisor hits
during interactive review.

Run via:
    DATABASE_URL=postgres://mp20:mp20@localhost:5432/mp20 \\
      uv run python -m pytest web/api/tests/test_perf_budgets.py \\
      --benchmark-only --benchmark-min-rounds=20

If any endpoint exceeds budget, the test fails. Halt + investigate
the regression instead of bumping the threshold.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from web.api import models


@pytest.fixture(autouse=True)
def _skip_when_benchmark_disabled(request) -> None:
    """Skip perf-budget tests when pytest-benchmark is disabled.

    The full-suite gate run uses `--benchmark-disable` so benchmarks
    don't slow down developer feedback loops; the perf gate runs
    separately via `--benchmark-only`. Without this guard, the
    benchmark fixture returns a no-op stub that doesn't populate
    `.stats`, causing AttributeError in `_assert_within_budget`.
    """
    bench = request.node.get_closest_marker("benchmark")  # noqa: F841 — referenced for clarity
    benchmark_obj = request.getfixturevalue("benchmark")
    if getattr(benchmark_obj, "disabled", False):
        pytest.skip("pytest-benchmark disabled (run with --benchmark-only)")


# Locked decision #18 budgets in seconds.
P50_BUDGET_S = 0.250
P99_BUDGET_S = 1.000


def _user():
    User = get_user_model()
    return User.objects.create_user(
        username="perf@example.com", email="perf@example.com", password="pw"
    )


def _workspace(user):
    return models.ReviewWorkspace.objects.create(label="Perf WS", owner=user)


def _doc(workspace, *, filename: str = "kyc.pdf"):
    digest = (filename.encode().hex() + "0" * 64)[:64]
    return models.ReviewDocument.objects.create(
        workspace=workspace,
        original_filename=filename,
        content_type="application/pdf",
        extension="pdf",
        file_size=1024,
        sha256=digest,
        storage_path=f"workspace_{workspace.external_id}/{filename}",
        document_type="kyc",
        status=models.ReviewDocument.Status.RECONCILED,
        processing_metadata={
            "extraction_version": "extraction.v2",
            "review_schema_version": "reviewed_client_state.v1",
        },
    )


def _assert_within_budget(benchmark) -> None:
    """Assert mean (P50 approx) < 250ms and max (P99 approx) < 1s.

    pytest-benchmark exposes stats via attribute access: `mean`,
    `max`, `median`, etc., on `benchmark.stats.stats`.
    """
    stats = benchmark.stats.stats
    mean_s = stats.mean
    max_s = stats.max
    assert mean_s < P50_BUDGET_S, (
        f"P50 (mean) latency {mean_s * 1000:.1f}ms exceeds "
        f"{P50_BUDGET_S * 1000:.0f}ms budget (locked #18)"
    )
    assert max_s < P99_BUDGET_S, (
        f"P99 (max) latency {max_s * 1000:.1f}ms exceeds "
        f"{P99_BUDGET_S * 1000:.0f}ms budget (locked #18)"
    )


@pytest.mark.django_db
def test_perf_disclaimer_acknowledge(benchmark) -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    def _post():
        # First call writes, subsequent calls hit the same row + emit
        # an audit event; both paths exercise the endpoint's hot path.
        response = client.post(
            reverse("disclaimer-acknowledge"),
            {"version": "v1"},
            format="json",
        )
        assert response.status_code == 200
        return response

    benchmark.pedantic(_post, rounds=20, iterations=1)
    _assert_within_budget(benchmark)


@pytest.mark.django_db
def test_perf_tour_complete(benchmark) -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    def _post():
        response = client.post(reverse("tour-complete"), {}, format="json")
        assert response.status_code == 200
        return response

    benchmark.pedantic(_post, rounds=20, iterations=1)
    _assert_within_budget(benchmark)


@pytest.mark.django_db
def test_perf_feedback_submit(benchmark) -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)

    def _post():
        response = client.post(
            reverse("feedback-submit"),
            {
                "severity": "friction",
                "description": (
                    "Advisor friction note for the perf benchmark "
                    "covering at least the 20-character minimum."
                ),
            },
            format="json",
        )
        assert response.status_code in {200, 201}
        return response

    benchmark.pedantic(_post, rounds=20, iterations=1)
    _assert_within_budget(benchmark)


@pytest.mark.django_db
def test_perf_doc_detail(benchmark) -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = _workspace(user)
    doc = _doc(workspace)

    def _get():
        response = client.get(
            reverse("review-document-detail", args=[workspace.external_id, doc.id]),
        )
        assert response.status_code == 200
        return response

    benchmark.pedantic(_get, rounds=20, iterations=1)
    _assert_within_budget(benchmark)


@pytest.mark.django_db
def test_perf_review_workspace_detail(benchmark) -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = _workspace(user)
    _doc(workspace)

    def _get():
        response = client.get(
            reverse("review-workspace-detail", args=[workspace.external_id]),
        )
        assert response.status_code == 200
        return response

    benchmark.pedantic(_get, rounds=20, iterations=1)
    _assert_within_budget(benchmark)


@pytest.mark.django_db
def test_perf_fact_override(benchmark) -> None:
    user = _user()
    client = APIClient()
    client.force_authenticate(user=user)
    workspace = _workspace(user)
    counter = {"n": 0}

    def _post():
        counter["n"] += 1
        response = client.post(
            reverse("review-workspace-fact-override", args=[workspace.external_id]),
            {
                "field": f"people[0].marital_status_{counter['n']}",
                "value": "married",
                "rationale": "Perf benchmark — append-only insert path.",
            },
            format="json",
        )
        assert response.status_code == 200
        return response

    benchmark.pedantic(_post, rounds=20, iterations=1)
    _assert_within_budget(benchmark)
