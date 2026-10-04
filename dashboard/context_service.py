"""Generic Dashboard context storage and supported runtime resolution."""

from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.shortcuts import get_object_or_404

from .registry import DashboardContext


def context_lookup(context_object, using=None):
    """Identity used consistently for lookup and creation, independent of owner."""
    if context_object.pk is None:
        raise ValueError("Dashboard context object must be saved.")
    return {
        "context_content_type": ContentType.objects.db_manager(using or context_object._state.db or "default").get_for_model(context_object),
        "context_object_id": context_object.pk,
    }


def visible_project(user, project_id):
    from project.models import Project
    visible = Project.get_instances_for_user("view", user, Project.objects.all())
    return get_object_or_404(visible, pk=project_id)


def resolve_context(user, dashboard):
    """Only user/Project are executable; generic storage accepts future models."""
    if dashboard.scope == "user" and dashboard.context_content_type_id is None and dashboard.context_object_id is None:
        return DashboardContext.personal(user)
    if dashboard.scope == "project":
        from project.models import Project
        project_type = ContentType.objects.get_for_model(Project)
        if dashboard.context_content_type_id != project_type.pk or dashboard.context_object_id is None:
            raise Http404("Dashboard context is unavailable.")
        return DashboardContext.for_object(user, visible_project(user, dashboard.context_object_id))
    raise Http404("Dashboard context is unavailable.")
