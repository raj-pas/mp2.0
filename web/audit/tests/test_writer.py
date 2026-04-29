from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from web.audit.models import AuditEvent
from web.audit.writer import record_event


@pytest.mark.django_db
def test_record_event_persists_audit_event() -> None:
    event = record_event(
        action="engine_run",
        entity_type="household",
        entity_id="hh_chen",
        metadata={"source": "test"},
    )

    assert AuditEvent.objects.count() == 1
    assert event.action == "engine_run"
    assert event.metadata == {"source": "test"}


@pytest.mark.django_db
def test_audit_events_are_immutable() -> None:
    event = record_event(action="upload", entity_type="review_workspace")

    with pytest.raises(DatabaseError):  # DB trigger guards bulk updates.
        AuditEvent.objects.filter(pk=event.pk).update(action="changed")
    with pytest.raises(ValidationError):
        event.delete()
