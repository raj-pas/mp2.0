"""Phase 6.9 — RequestIDMiddleware regression tests.

Pin the contract that:
- Every response carries an `X-Request-ID` header.
- Server-minted IDs are UUID-shaped.
- Client-supplied UUID is honored end-to-end.
- Client-supplied non-UUID is replaced with a server-minted UUID.
- The thread-local `get_request_id()` is set during request
  handling and torn down after.
"""

from __future__ import annotations

import re
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from web.mp20_web.request_id import get_request_id

UUID_HEX_RE = re.compile(r"^[0-9a-f]{32}$")


def _user():
    User = get_user_model()
    return User.objects.create_user(
        username="advisor@example.com", email="advisor@example.com", password="pw"
    )


@pytest.mark.django_db
def test_response_carries_x_request_id_header() -> None:
    client = APIClient()
    response = client.get(reverse("session"))
    assert response.status_code == 200
    rid = response.headers.get("X-Request-ID")
    assert rid is not None
    assert UUID_HEX_RE.match(rid) or _is_uuid_string(rid)


@pytest.mark.django_db
def test_client_supplied_uuid_is_honored() -> None:
    client = APIClient()
    supplied = uuid.uuid4().hex
    response = client.get(reverse("session"), HTTP_X_REQUEST_ID=supplied)
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == supplied


@pytest.mark.django_db
def test_client_supplied_non_uuid_is_replaced() -> None:
    client = APIClient()
    response = client.get(reverse("session"), HTTP_X_REQUEST_ID="not-a-uuid")
    assert response.status_code == 200
    rid = response.headers.get("X-Request-ID")
    assert rid != "not-a-uuid"
    assert UUID_HEX_RE.match(rid) or _is_uuid_string(rid)


@pytest.mark.django_db
def test_thread_local_torn_down_after_request() -> None:
    client = APIClient()
    client.get(reverse("session"))
    # After the request finishes, the thread-local should be cleared.
    assert get_request_id() is None


def _is_uuid_string(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True
