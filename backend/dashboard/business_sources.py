"""Read-only Dashboard providers built on the existing domain visibility rules."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _

from .financial_sources import visible_projects


def _payload(count, label, items, *, alerts=None, progress=None):
    data = {"kpi": {"value": count, "label": label, "tone": "neutral"},
            "compact-list": {"items": items}}
    if alerts is not None:
        data["alert-list"] = {"items": alerts}
    if progress is not None:
        data["progress-list"] = {"items": progress}
    return {"__renderers__": data}


def _participant_projects(user, statuses=None):
    from project.models import Participant
    qs = Participant.objects.filter(employee__user=user).filter(Participant.get_active_filter())
    if statuses:
        qs = qs.filter(status__in=statuses)
    return qs.values("project_id")


def _managed_projects(user):
    return _participant_projects(user, ("l", "cl"))


def projects(context, config):
    from project.models import Project
    today = timezone.localdate()
    qs = Project.get_instances_for_user("view", context.user, Project.objects.all())
    if context.scope == "project" or "project_scope" in config:
        qs = qs.filter(pk__in=visible_projects(context, config).values("pk"))
    scope = config.get("scope", "all_visible")
    if scope == "participated":
        qs = qs.filter(pk__in=_participant_projects(context.user))
    elif scope == "managed":
        qs = qs.filter(pk__in=_managed_projects(context.user))
    if config.get("active_only", False):
        qs = qs.filter(status=True)
    if config.get("late_only", False):
        qs = qs.filter(status=True, end_date__lt=today)
    count = qs.count()
    items = [{"key": str(item.pk), "label": item.name,
              "date": item.end_date.isoformat() if item.end_date else None,
              "status": _("Active") if item.status else _("Inactive"),
              "href": f"/app/projects/{item.pk}/",
              "tone": "danger" if item.status and item.end_date and item.end_date < today else "neutral"}
             for item in qs.order_by("end_date", "name", "pk")[:config.get("limit", 5)]]
    alerts = [{**item, "severity": "danger" if item["tone"] == "danger" else "info"} for item in items]
    payload = _payload(count, _("Projects"), items, alerts=alerts)
    if context.scope == "project" and config.get("project_scope", "context") == "context" and count == 1:
        project = qs.first()
        payload["__renderers__"]["kpi"] = {
            "value": _("Active") if project.status else _("Inactive"),
            "label": _("Project status"),
            "context": _("End date: %(date)s") % {"date": project.end_date.isoformat()} if project.end_date else None,
            "tone": "success" if project.status else "muted",
        }
    return payload


def planning(context, config, *, tasks=False):
    from endpoints.models import Milestones
    from project.models import Project
    today = timezone.localdate()
    project_ids = Project.get_instances_for_user("view", context.user, Project.objects.all()).values("pk")
    if context.scope == "project" or "project_scope" in config:
        project_ids = project_ids.filter(pk__in=visible_projects(context, config).values("pk"))
    qs = Milestones.objects.filter(project_id__in=project_ids, start_date__isnull=not tasks)
    scope = config.get("scope", "all_visible")
    if scope == "mine":
        qs = qs.filter(employee__user=context.user)
    elif scope == "participated":
        qs = qs.filter(project_id__in=_participant_projects(context.user))
    elif scope == "managed_projects":
        qs = qs.filter(project_id__in=_managed_projects(context.user))
    elif scope == "subordinates" and tasks:
        from staff.models import Employee_Superior
        subordinate_ids = Employee_Superior.objects.filter(superior__user=context.user).filter(
            Employee_Superior.get_active_filter()).values("employee_id")
        qs = qs.filter(employee__in=subordinate_ids)
    qs = qs.distinct()
    status = config.get("status", "open")
    if status != "all":
        qs = qs.filter(status=(status == "done"))
    if config.get("overdue_only", False):
        qs = qs.filter(status=False, end_date__lt=today)
    due_within = config.get("due_within_days", "0")
    if due_within != "0":
        qs = qs.filter(end_date__gte=today, end_date__lte=today + timedelta(days=int(due_within)))
    count = qs.count()
    items = [{"key": str(item.pk), "label": item.name, "secondary": item.project.name,
              "date": item.end_date.isoformat() if item.end_date else None,
              "status": _("Completed") if item.status else _("Open"),
              "href": f"/app/projects/{item.project_id}/tasks",
              "tone": "danger" if item.end_date and item.end_date < today and not item.status else "neutral"}
             for item in qs.select_related("project").order_by("end_date", "pk")[:config.get("limit", 5)]]
    alerts = [{**item, "severity": "danger" if item["tone"] == "danger" else "warning"} for item in items]
    payload = _payload(count, _("Tasks") if tasks else _("Milestones"), items, alerts=alerts)
    if context.scope == "project" and not tasks and config.get("project_scope", "context") == "context":
        next_item = qs.filter(status=False, end_date__gte=today).order_by("end_date", "pk").first()
        payload["__renderers__"]["kpi"] = {
            "value": next_item.end_date.isoformat() if next_item else "—",
            "label": _("Next milestone"),
            "context": next_item.name if next_item else None,
            "tone": "neutral" if next_item else "muted",
        }
    return payload


def milestones(context, config):
    return planning(context, config)


def tasks(context, config):
    return planning(context, config, tasks=True)


def funds(context, config):
    from fund.models import Fund
    today = timezone.localdate()
    qs = Fund.get_instances_for_user("view", context.user, Fund.objects.all())
    if context.scope == "project" or "project_scope" in config:
        qs = qs.filter(project_id__in=visible_projects(context, config).values("pk"))
    if config.get("scope", "all_visible") == "managed_projects":
        qs = qs.filter(project_id__in=_managed_projects(context.user))
    if config.get("active_only", False):
        qs = qs.filter(Fund.get_active_filter(), project__status=True)
    days = config.get("ending_within_days", "0")
    if days != "0":
        qs = qs.filter(end_date__gte=today, end_date__lte=today + timedelta(days=int(days)))
    count = qs.count()
    items, progress = [], []
    for item in qs.select_related("project").order_by("end_date", "pk")[:config.get("limit", 5)]:
        amount = item.amount or Decimal("0")
        expense = item.expense or Decimal("0")
        available = amount + expense  # Fund's historical signed-expense convention.
        base = {"key": str(item.pk), "label": f'{item.ref} - {item.project.name}',
                "secondary": item.project.name, "date": item.end_date.isoformat() if item.end_date else None,
                "href": f"/app/projects/{item.project_id}/funding",
                "tone": "warning" if item.end_date and item.end_date <= today + timedelta(days=30) else "neutral"}
        items.append(base)
        progress.append({**base, "current": float(abs(expense)), "total": float(amount),
                         "percent": float(min(100, max(0, abs(expense) / amount * 100))) if amount > 0 else 0,
                         "secondary": _("Available: %(amount)s") % {"amount": available}})
    alerts = [{**item, "severity": "warning"} for item in items]
    return _payload(count, _("Funds"), items, alerts=alerts, progress=progress)


def contracts(context, config):
    from expense.contract_hub_api_v1 import visible_contracts
    from expense.models import Contract
    today = timezone.localdate()
    qs = visible_contracts(context.user)
    if context.scope == "project" or "project_scope" in config:
        qs = qs.filter(fund__project_id__in=visible_projects(context, config).values("pk"))
    if config.get("active_only", False):
        qs = qs.filter(is_active=True)
    if config.get("current_only", False):
        qs = qs.filter(start_date__lte=today, end_date__gte=today)
    if config.get("stale_only", False):
        qs = qs.filter(Contract.staleFilter())
    days = config.get("ending_within_days", "0")
    if days != "0":
        qs = qs.filter(end_date__gte=today, end_date__lte=today + timedelta(days=int(days)))
    count = qs.count()
    items = [{"key": str(item.pk), "label": str(item.employee),
              "secondary": " · ".join(filter(None, [str(item.contract_type) if item.contract_type else "", item.fund.project.name])),
              "date": item.end_date.isoformat() if item.end_date else None,
              "status": item.get_status_display(), "href": "/app/tools/contracts",
              "tone": "warning" if item.end_date and item.end_date <= today + timedelta(days=30) else "neutral"}
             for item in qs.select_related("employee", "contract_type", "fund__project").order_by("end_date", "pk")[:config.get("limit", 5)]]
    alerts = [{**item, "severity": "warning"} for item in items]
    return _payload(count, _("Contracts"), items, alerts=alerts)


def employees(context, config):
    from staff.models import Employee, Employee_Superior
    today = timezone.localdate()
    qs = Employee.get_instances_for_user("view", context.user, Employee.objects.all())
    if context.scope == "project" or "project_scope" in config:
        from project.models import Participant
        qs = qs.filter(pk__in=Participant.objects.filter(
            project_id__in=visible_projects(context, config).values("pk")
        ).values("employee_id"))
    scope = config.get("scope", "all_visible")
    if scope == "self":
        qs = qs.filter(user=context.user)
    elif scope == "subordinates":
        subordinate_ids = Employee_Superior.objects.filter(superior__user=context.user).filter(
            Employee_Superior.get_active_filter()).values("employee_id")
        qs = qs.filter(pk__in=subordinate_ids)
    if config.get("active_only", False):
        qs = qs.filter(is_active=True)
    movement = config.get("movement", "all")
    days = int(config.get("within_days", "30"))
    if movement == "arrivals":
        qs = qs.filter(entry_date__gte=today, entry_date__lte=today + timedelta(days=days))
    elif movement == "departures":
        qs = qs.filter(exit_date__gte=today, exit_date__lte=today + timedelta(days=days))
    count = qs.count()
    items = [{"key": str(item.pk), "label": str(item),
              "date": (item.entry_date if movement == "arrivals" else item.exit_date).isoformat()
              if (item.entry_date if movement == "arrivals" else item.exit_date) else None,
              "href": f"/app/employees/{item.pk}",
              "status": _("Active") if item.is_active else _("Inactive"), "tone": "neutral"}
             for item in qs.order_by("last_name", "first_name", "pk")[:config.get("limit", 5)]]
    alerts = [{**item, "severity": "info"} for item in items]
    return _payload(count, _("Employees"), items, alerts=alerts)


def leaves(context, config):
    from leave.models import Leave
    from staff.models import Employee, Employee_Superior
    today = timezone.localdate()
    visible = Employee.get_instances_for_user("view", context.user, Employee.objects.all())
    scope = config.get("scope", "all_visible")
    if scope == "mine":
        visible = visible.filter(user=context.user)
    elif scope == "subordinates":
        subordinate_ids = Employee_Superior.objects.filter(superior__user=context.user).filter(
            Employee_Superior.get_active_filter()).values("employee_id")
        visible = visible.filter(pk__in=subordinate_ids)
    qs = Leave.objects.filter(employee__in=visible)
    if config.get("current_only", False):
        qs = qs.filter(start_date__lte=today, end_date__gte=today)
    else:
        days = int(config.get("upcoming_days", "30"))
        qs = qs.filter(start_date__gte=today, start_date__lte=today + timedelta(days=days))
    count = qs.count()
    items = [{"key": str(item.pk), "label": item.type.name,
              "secondary": str(item.employee), "date": item.start_date.isoformat() if item.start_date else None,
              "href": f"/app/employees/{item.employee_id}/leaves", "tone": "neutral"}
             for item in qs.select_related("type", "employee").order_by("start_date", "pk")[:config.get("limit", 5)]]
    return _payload(count, _("Leaves"), items)
