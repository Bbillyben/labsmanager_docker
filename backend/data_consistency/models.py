from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class DataConsistencyException(models.Model):
    """A human decision about one precise, currently detected occurrence."""

    rule_key = models.CharField(max_length=100)
    contract_id = models.BigIntegerField(null=True, blank=True)
    fund_id = models.BigIntegerField(null=True, blank=True)
    milestone_id = models.BigIntegerField(null=True, blank=True)
    expense_id = models.BigIntegerField(null=True, blank=True)
    employee_id = models.BigIntegerField(null=True, blank=True)
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
                condition=Q(closed_at__isnull=True, contract_id__isnull=False),
                name="unique_open_contract_consistency_exception",
            ),
            models.UniqueConstraint(
                fields=("rule_key", "fund_id", "project_id"),
                condition=Q(closed_at__isnull=True, fund_id__isnull=False),
                name="unique_open_fund_consistency_exception",
            ),
            models.UniqueConstraint(
                fields=("rule_key", "milestone_id", "project_id"),
                condition=Q(closed_at__isnull=True, milestone_id__isnull=False),
                name="unique_open_milestone_consistency_exception",
            ),
            models.UniqueConstraint(
                fields=("rule_key", "expense_id", "project_id"),
                condition=Q(closed_at__isnull=True, expense_id__isnull=False),
                name="unique_open_expense_consistency_exception",
            ),
            models.UniqueConstraint(
                fields=("rule_key", "project_id"),
                condition=Q(closed_at__isnull=True, contract_id__isnull=True,
                            fund_id__isnull=True, milestone_id__isnull=True,
                            expense_id__isnull=True),
                name="unique_open_project_consistency_exception",
            ),
        ]


