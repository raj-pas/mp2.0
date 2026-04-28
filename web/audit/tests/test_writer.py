from __future__ import annotations

import pytest
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
