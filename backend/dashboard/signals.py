"""Restore the former Project FK cascade for generic Dashboard contexts."""

from django.db.models.signals import post_delete
from django.dispatch import receiver

from project.models import Project

from .context_service import context_lookup
from .models import Dashboard


@receiver(post_delete, sender=Project, dispatch_uid="dashboard_delete_for_project")
def delete_project_dashboards(sender, instance, using, **kwargs):
    Dashboard.objects.using(using).filter(**context_lookup(instance, using=using)).delete()
