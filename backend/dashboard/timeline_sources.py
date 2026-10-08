"""Small provider registry for the composite Dashboard timeline."""

from datetime import timedelta

from django.utils import timezone
from django.utils.translation import gettext as _

from .business_sources import planning_queryset


def _planning_events(context, config, *, tasks, start, today, end):
    queryset = planning_queryset(context, config, tasks=tasks)
    earlier_overdue_count = queryset.filter(status=False, end_date__lt=start).count()
    rows = queryset.filter(end_date__gte=start, end_date__lte=end).select_related("project")
    if tasks:
        rows = rows.prefetch_related("employee")
    rows = rows.order_by("end_date", "status", "name", "pk")[:config.get("limit", 5)]
    rows = list(rows)
    visible_assignee_ids = set()
    if tasks:
        from staff.models import Employee
        assignee_ids = {employee.pk for item in rows for employee in item.employee.all()}
        visible_assignee_ids = set(Employee.get_instances_for_user(
            "view", context.user, Employee.objects.filter(pk__in=assignee_ids)
        ).values_list("pk", flat=True))
    source_type = "tasks" if tasks else "milestones"
    source_label = str(_("Task") if tasks else _("Milestone"))
    icon = "FolderKanban" if tasks else "Flag"
    events = []
    for item in rows:
        state = ("done" if item.status else "overdue" if item.end_date < today else
                 "today" if item.end_date == today else "soon" if item.end_date <= today + timedelta(days=7) else "future")
        tone = {"done": "muted", "overdue": "danger", "today": "warning", "soon": "warning", "future": "neutral"}[state]
        events.append({
            "id": f"{source_type}:{item.pk}", "source_type": source_type, "source_label": source_label,
            "date": item.end_date.isoformat(), "title": item.name,
            "project_name": item.project.name, "project_href": f"/app/projects/{item.project_id}",
            "secondary": ", ".join(str(employee) for employee in item.employee.all()
                                   if employee.pk in visible_assignee_ids) if tasks else None,
            "href": f"/app/projects/{item.project_id}/tasks", "state": state, "tone": tone, "icon": icon,
        })
    return events, earlier_overdue_count


def _task_events(context, config, start, today, end):
    return _planning_events(context, config, tasks=True, start=start, today=today, end=end)


def _milestone_events(context, config, start, today, end):
    return _planning_events(context, config, tasks=False, start=start, today=today, end=end)


TIMELINE_PROVIDERS = {"tasks": _task_events, "milestones": _milestone_events}


def timeline(context, config):
    today = timezone.localdate()
    start = today - timedelta(days=2)
    end = today + timedelta(days=int(config.get("calendar_days", "14")))
    events = []
    earlier_overdue_count = 0
    for key, provider in TIMELINE_PROVIDERS.items():
        if not config.get(f"include_{key}", True):
            continue
        provider_config = {name[len(key) + 1:]: value for name, value in config.items() if name.startswith(f"{key}_")}
        provider_events, earlier_count = provider(context, provider_config, start, today, end)
        events.extend(provider_events)
        earlier_overdue_count += earlier_count
    events.sort(key=lambda item: (item["date"], item["state"] == "done", item["source_type"], item["title"], item["id"]))
    return {"window_start": start.isoformat(), "today": today.isoformat(), "window_end": end.isoformat(),
            "earlier_overdue_count": earlier_overdue_count, "events": events}
