from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models


class AuditEvent(models.Model):
    actor = models.CharField(max_length=255, default="system")
    action = models.CharField(max_length=120)
    entity_type = models.CharField(max_length=120)
    entity_id = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.entity_type}:{self.entity_id}"

    def save(self, *args, **kwargs):  # noqa: ANN002, ANN003
        if self.pk and AuditEvent.objects.filter(pk=self.pk).exists():
            raise ValidationError("Audit events are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise ValidationError("Audit events are immutable.")
