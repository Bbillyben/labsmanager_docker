import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q

from labsmanager.mixin import TimeStampMixin


class Dashboard(TimeStampMixin):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="personal_dashboards")
    context_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True,
                                             related_name="context_dashboards")
    context_object_id = models.PositiveBigIntegerField(null=True, blank=True)
    context_object = GenericForeignKey("context_content_type", "context_object_id")
    name = models.CharField(max_length=120)
    icon = models.CharField(max_length=80, blank=True)
    scope = models.CharField(max_length=20, default="user")
    is_default = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("position", "pk")
        constraints = [
            models.UniqueConstraint(fields=("owner",), condition=Q(is_default=True), name="dashboard_one_default_per_owner"),
            models.UniqueConstraint(fields=("owner", "context_content_type", "context_object_id"),
                                    condition=Q(context_content_type__isnull=False), name="dashboard_one_per_owner_context"),
            models.CheckConstraint(
                check=Q(context_content_type__isnull=True, context_object_id__isnull=True)
                | Q(context_content_type__isnull=False, context_object_id__isnull=False),
                name="dashboard_context_fields_together",
            ),
        ]
        indexes = [models.Index(fields=("context_content_type", "context_object_id"), name="dashboard_context_idx")]


class WidgetInstance(TimeStampMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name="widgets")
    definition_key = models.CharField(max_length=160)
    source_key = models.CharField(max_length=160, blank=True)
    renderer_key = models.CharField(max_length=80)
    title = models.CharField(max_length=160, blank=True)
    config = models.JSONField(default=dict, blank=True)
    x = models.PositiveIntegerField(default=0)
    y = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=4)
    height = models.PositiveIntegerField(default=3)
    logical_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("logical_order", "created_at")
