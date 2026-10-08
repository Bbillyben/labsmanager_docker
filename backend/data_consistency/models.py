from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class DataConsistencyException(models.Model):
    """A human decision about one precise, currently detected occurrence."""

    rule_key = models.CharField(max_length=100)
    contract_id = models.BigIntegerField()
    employee_id = models.BigIntegerField()
    project_id = models.BigIntegerField()
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    accepted_at = models.DateTimeField(default=timezone.now)
    reason = models.TextField(blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_reason = models.CharField(max_length=32, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("rule_key", "contract_id", "employee_id", "project_id"),
                condition=Q(closed_at__isnull=True),
                name="unique_open_consistency_exception",
            ),
        ]


