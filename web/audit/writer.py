from __future__ import annotations

from typing import Any

from web.audit.models import AuditEvent


def record_event(
    *,
    action: str,
    entity_type: str,
    entity_id: str = "",
    actor: str = "system",
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    return AuditEvent.objects.create(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata=metadata or {},
    )
