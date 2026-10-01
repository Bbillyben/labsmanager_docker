"""Shared Planning queryset and read context; callers authorize their root scope."""

from datetime import timedelta

from django.db.models import Prefetch, Q
from django.utils import timezone

from project.models import Project
from settings.models import LMUserSetting
from staff.models import Employee

from .models import MilestoneDependency


def filter_planning_items(queryset, params):
    """Apply optional Planning filters before either list or Gantt serialization."""
    search = params.get("search", "").strip()
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(desc__icontains=search))
    kind = params.get("kind")
    if kind == "milestone":
        queryset = queryset.filter(start_date__isnull=True)
    elif kind == "task":
        queryset = queryset.filter(start_date__isnull=False)
    employee = params.get("employee", "")
    if employee:
        queryset = queryset.filter(employee__pk=int(employee)).distinct() if employee.isdecimal() else queryset.none()
    return queryset


def preload_planning_items(queryset):
    """Load relations used by the shared Planning serializer."""
    return queryset.select_related("project").prefetch_related(
        Prefetch("employee", queryset=Employee.objects.order_by("first_name", "last_name", "pk")),
        Prefetch(
            "incoming_dependencies",
            queryset=MilestoneDependency.objects.select_related("predecessor"),
            to_attr="visible_dependencies",
        ),
    ).order_by("pk")


def planning_serializer_context(user, scoped_queryset):
    """Provide viewer visibility and temporal settings for one authorized scope."""
    stale_days = LMUserSetting.get_setting(
        "NOTIFICATION_ENDPOINTS_MILESTONES_STALE", user=user,
    )
    return {
        "user": user,
        "today": timezone.localdate(),
        "stale_delta": timedelta(days=int(stale_days)),
        "visible_employee_ids": set(Employee.get_instances_for_user(
            "view", user, Employee.objects.all(),
        ).values_list("pk", flat=True)),
        "visible_project_ids": set(Project.get_instances_for_user(
            "view", user, Project.objects.all(),
        ).values_list("pk", flat=True).distinct()),
        "visible_work_ids": set(scoped_queryset.values_list("pk", flat=True)),
    }
