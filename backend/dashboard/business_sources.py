"""Read-only Dashboard providers built on the existing domain visibility rules."""

from datetime import timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.db.models import Case, Count, IntegerField, Q, Sum, Value, When
from django.db.models.functions import Abs
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


def project_queryset(context, config):
    from project.models import Project
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
        qs = qs.filter(status=True, end_date__lt=timezone.localdate())
    return qs


def project_portfolio(context, config, qs=None):
    from collections import defaultdict
    from endpoints.models import Milestones
    from settings.models import LMUserSetting
    from .financial_sources import advancement_for_funds, visible_funds

    qs = qs if qs is not None else project_queryset(context, config)
    today = timezone.localdate()
    soon_months = LMUserSetting.get_setting("DASHBOARD_PROJECT_STALE_TO_MONTH", user=context.user, backup_value=3)
    soon_date = today + relativedelta(months=int(soon_months))
    project_ids = qs.values("pk")
    overdue = Milestones.objects.filter(project_id__in=project_ids, status=False, end_date__lt=today)
    overdue_tasks = dict(overdue.filter(start_date__isnull=False).values("project_id").annotate(total=Count("pk")).values_list("project_id", "total"))
    overdue_milestones = set(overdue.filter(start_date__isnull=True).values_list("project_id", flat=True).distinct())
    ending_ids = set(qs.filter(status=True, end_date__gte=today, end_date__lte=soon_date).values_list("pk", flat=True))
    ended_ids = set(qs.filter(status=True, end_date__lt=today).values_list("pk", flat=True))
    attention_ids = set(overdue_tasks) | overdue_milestones | ending_ids | ended_ids
    summary = {"count": qs.count(), "active_count": qs.filter(status=True).count(),
               "ending_soon_count": len(ending_ids), "attention_count": len(attention_ids)}
    rows = list(qs.order_by("name", "pk")[:config.get("limit", 5)])
    row_ids = {item.pk for item in rows}
    funds_by_project = defaultdict(list)
    for fund in visible_funds(context, config).filter(project_id__in=row_ids).only(
        "project_id", "amount", "expense", "start_date", "end_date"
    ):
        funds_by_project[fund.project_id].append(fund)
    next_milestones = {}
    for milestone in Milestones.objects.filter(
        project_id__in=row_ids, start_date__isnull=True, status=False, end_date__gte=today
    ).order_by("project_id", "end_date", "pk"):
        next_milestones.setdefault(milestone.project_id, milestone)
    items = []
    for project in rows:
        temporal_percent = None
        if project.start_date and project.end_date and project.end_date > project.start_date:
            duration = (project.end_date - project.start_date).days
            elapsed = max(0, min(duration, (today - project.start_date).days))
            temporal_percent = round(elapsed / duration * 100, 1)
        state = ("ended" if project.end_date and project.end_date < today else
                 "upcoming" if project.start_date and project.start_date > today else
                 "ending_soon" if project.pk in ending_ids else
                 "active" if project.status else "unknown")
        financial = advancement_for_funds(funds_by_project[project.pk], today=today)
        milestone = next_milestones.get(project.pk)
        signals = (["overdue_tasks"] if project.pk in overdue_tasks else []) + (
            ["overdue_milestones"] if project.pk in overdue_milestones else []) + (
            ["project_ending_soon"] if project.pk in ending_ids else []) + (
            ["project_ended"] if project.pk in ended_ids else [])
        items.append({"key": str(project.pk), "name": project.name, "href": f"/app/projects/{project.pk}",
                      "start_date": project.start_date.isoformat() if project.start_date else None,
                      "end_date": project.end_date.isoformat() if project.end_date else None,
                      "temporal_percent": temporal_percent, "temporal_state": state,
                      "financial": {"amount": financial["amount"], "spent": financial["spent"],
                                    "percent": financial["budget_percent"]} if financial else None,
                      "next_milestone": {"title": milestone.name, "date": milestone.end_date.isoformat(),
                                         "days_until": (milestone.end_date - today).days,
                                         "href": f"/app/projects/{project.pk}/tasks"} if milestone else None,
                      "overdue_task_count": overdue_tasks.get(project.pk, 0), "attention_signals": signals})
    return {"summary": summary, "items": items}


def projects(context, config):
    today = timezone.localdate()
    qs = project_queryset(context, config)
    count = qs.count()
    items = [{"key": str(item.pk), "label": item.name,
              "date": item.end_date.isoformat() if item.end_date else None,
              "status": _("Active") if item.status else _("Inactive"),
              "href": f"/app/projects/{item.pk}/",
              "tone": "danger" if item.status and item.end_date and item.end_date < today else "neutral"}
             for item in qs.order_by("end_date", "name", "pk")[:config.get("limit", 5)]]
    alerts = [{**item, "severity": "danger" if item["tone"] == "danger" else "info"} for item in items]
    payload = _payload(count, _("Projects"), items, alerts=alerts)
    payload["__renderers__"]["project-portfolio"] = project_portfolio(context, config, qs)
    if context.scope == "project" and config.get("project_scope", "context") == "context" and count == 1:
        project = qs.first()
        payload["__renderers__"]["kpi"] = {
            "value": _("Active") if project.status else _("Inactive"),
            "label": _("Project status"),
            "context": _("End date: %(date)s") % {"date": project.end_date.isoformat()} if project.end_date else None,
            "tone": "success" if project.status else "muted",
        }
    return payload


def planning_queryset(context, config, *, tasks=False):
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
    return qs


def planning(context, config, *, tasks=False):
    from settings.models import LMUserSetting
    stale_setting=LMUserSetting.get_setting("DASHBOARD_MILESTONES_STALE_TO_MONTH", user=context.user, backup_value=1)
    stale_setting*=30

    today = timezone.localdate()
    qs = planning_queryset(context, config, tasks=tasks)
    due_within = config.get("due_within_days", "0")
    count = qs.count()
    milestone_summary = None
    if not tasks:
        milestone_summary = {
            "count": count,
            "overdue_count": qs.filter(status=False, end_date__lt=today).count(),
            "due_soon_count": qs.filter(status=False, end_date__gte=today,
                                        end_date__lte=today + timedelta(days=stale_setting)).count(),
        }
    task_summary = None
    if tasks:
        task_soon_days = int(due_within) if due_within != "0" else stale_setting
        task_soon_cutoff = today + timedelta(days=task_soon_days)
        task_summary = {
            "count": count,
            "overdue_count": qs.filter(status=False, end_date__lt=today).count(),
            "due_soon_count": qs.filter(status=False, end_date__gte=today, end_date__lte=task_soon_cutoff).count(),
        }
    ordered = qs.select_related("project")
    if not tasks:
        ordered = ordered.annotate(_deadline_priority=Case(
            When(status=False, end_date__lt=today, then=Value(0)),
            When(status=False, end_date__gte=today,
                 end_date__lte=today + timedelta(days=stale_setting), then=Value(1)),
            When(status=False, end_date__isnull=False, then=Value(2)),
            When(status=True, then=Value(3)), default=Value(4), output_field=IntegerField(),
        )).order_by("_deadline_priority", "end_date", "pk")
    else:
        ordered = ordered.order_by("end_date", "pk")
    rows = ordered[:config.get("limit", 5)]
    items, deadline_items = [], []
    for item in rows:
        date = item.end_date.isoformat() if item.end_date else None
        href = f"/app/projects/{item.project_id}/tasks"
        items.append({"key": str(item.pk), "label": item.name, "secondary": item.project.name,
                      "date": date, "status": _("Completed") if item.status else _("Open"),
                      "href": href,
                      "tone": "danger" if item.end_date and item.end_date < today and not item.status else "neutral"})
        if not tasks:
            days_until = (item.end_date - today).days if item.end_date else None
            state = ("completed" if item.status else "unscheduled" if days_until is None else
                     "overdue" if days_until < 0 else "today" if days_until == 0 else
                     "due_soon" if days_until <= stale_setting else "upcoming")
            deadline_items.append({"key": str(item.pk), "label": item.name,
                                   "project_name": item.project.name, "date": date, "href": href,
                                   "days_until": days_until, "state": state})
    alerts = [{**item, "severity": "danger" if item["tone"] == "danger" else "warning"} for item in items]
    payload = _payload(count, _("Tasks") if tasks else _("Milestones"), items, alerts=alerts)
    if milestone_summary is not None:
        deadline = {"summary": milestone_summary, "items": deadline_items}
        payload["__renderers__"]["deadline-list"] = deadline
    if task_summary is not None:
        from staff.models import Employee
        prioritized_tasks = qs.select_related("project").prefetch_related("employee").annotate(
            _attention_priority=Case(
                When(status=False, end_date__lt=today, then=Value(0)),
                When(status=False, end_date__gte=today, end_date__lte=task_soon_cutoff, then=Value(1)),
                When(status=False, end_date__isnull=False, then=Value(2)),
                When(status=True, then=Value(3)),
                default=Value(4), output_field=IntegerField(),
            )
        ).order_by("_attention_priority", "end_date", "pk")
        task_rows = list(prioritized_tasks[:config.get("limit", 5)])
        assignee_ids = {employee.pk for item in task_rows for employee in item.employee.all()}
        visible_assignee_ids = set(Employee.get_instances_for_user(
            "view", context.user, Employee.objects.filter(pk__in=assignee_ids)
        ).values_list("pk", flat=True))
        task_items = []
        for item in task_rows:
            days_until = (item.end_date - today).days if item.end_date else None
            state = ("done" if item.status else "unscheduled" if days_until is None else
                     "overdue" if days_until < 0 else "today" if days_until == 0 else
                     "due_soon" if days_until <= task_soon_days else "later")
            task_items.append({
                "key": str(item.pk), "title": item.name,
                "href": f"/app/projects/{item.project_id}/tasks",
                "project_name": item.project.name,
                "project_href": f"/app/projects/{item.project_id}",
                "assignees": [{"id": employee.pk, "name": str(employee),
                               "href": f"/app/employees/{employee.pk}" if employee.pk in visible_assignee_ids else None}
                              for employee in item.employee.all()],
                "date": item.end_date.isoformat() if item.end_date else None,
                "days_until": days_until, "state": state,
            })
        payload["__renderers__"]["task-workload"] = {"summary": task_summary, "items": task_items}
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
    from settings.models import LMUserSetting
    today = timezone.localdate()
    qs = Fund.get_instances_for_user("view", context.user, Fund.objects.all())
    stale_setting=LMUserSetting.get_setting("DASHBOARD_FUND_STALE_TO_MONTH", user=context.user, backup_value=1)
    stale_setting*=30
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
    totals = qs.aggregate(amount=Sum("amount"), spent=Sum(Abs("expense")))
    total_amount = totals["amount"] or Decimal("0")
    total_spent = totals["spent"] or Decimal("0")
    attention_count = qs.filter(end_date__lte=today + timedelta(days=30)).count()
    items, progress, overview_items = [], [], []
    for item in qs.select_related("project").order_by("end_date", "pk")[:config.get("limit", 5)]:
        amount = item.amount or Decimal("0")
        expense = item.expense or Decimal("0")
        available = amount + expense  # Fund's historical signed-expense convention.
        base = {"key": str(item.pk), "label": f'{item.ref} - {item.project.name}',
                "secondary": item.project.name, "date": item.end_date.isoformat() if item.end_date else None,
                "href": f"/app/projects/{item.project_id}/funding",
                "tone": "warning" if item.end_date and item.end_date <= today + timedelta(days=stale_setting) else "neutral"}
        items.append(base)
        progress.append({**base, "current": float(abs(expense)), "total": float(amount),
                         "percent": float(min(100, max(0, abs(expense) / amount * 100))) if amount > 0 else 0,
                         "secondary": _("Available: %(amount)s") % {"amount": available}})
        remaining_days = (item.end_date - today).days if item.end_date else None
        overview_items.append({
            "key": str(item.pk),  "label": f'{item.ref} - {item.project.name}',
            "secondary": item.project.name if item.ref else None,
            "href": base["href"], "date": base["date"],
            "current": float(abs(expense)), "total": float(amount),
            "percent": float(abs(expense) / amount * 100) if amount > 0 else None,
            "remaining_days": remaining_days,
            "status": "expired" if remaining_days is not None and remaining_days < 0 else
                      "ending_soon" if remaining_days is not None and remaining_days <= stale_setting else "normal",
        })
    alerts = [{**item, "severity": "warning"} for item in items]
    overview = {"summary": {"amount": float(total_amount), "spent": float(total_spent),
                            "percent": float(total_spent / total_amount * 100) if total_amount > 0 else None,
                            "count": count, "count_label": _("Funds"), "attention_count": attention_count},
                "items": overview_items}
    payload = _payload(count, _("Funds"), items, alerts=alerts, progress=progress)
    payload["__renderers__"]["overview-list"] = overview
    return payload


def contracts(context, config):
    from expense.contract_hub_api_v1 import visible_contracts
    from project.models import Project
    from staff.models import Employee
    from settings.models import LMUserSetting
    today = timezone.localdate()
    stale_months = LMUserSetting.get_setting("DASHBOARD_CONTRACT_STALE_TO_MONTH", user=context.user, backup_value=3)
    stale_cutoff = today + relativedelta(months=stale_months)
    soon_cutoff = today + timedelta(days=30)
    qs = visible_contracts(context.user)
    if context.scope == "project" or "project_scope" in config:
        qs = qs.filter(fund__project_id__in=visible_projects(context, config).values("pk"))
    if config.get("active_only", False):
        qs = qs.filter(is_active=True)
    if config.get("current_only", False):
        qs = qs.filter(start_date__lte=today, end_date__gte=today)
    if config.get("stale_only", False):
        qs = qs.filter(is_active=True, end_date__lte=stale_cutoff)
    days = config.get("ending_within_days", "0")
    if days != "0":
        qs = qs.filter(end_date__gte=today, end_date__lte=today + timedelta(days=int(days)))
    count = qs.count()
    stale_count = qs.filter(is_active=True, end_date__lte=stale_cutoff).count()
    ending_soon_count = qs.filter(end_date__gte=today, end_date__lte=soon_cutoff).count()
    ordered = qs.select_related("employee", "contract_type", "fund__project").annotate(
        _priority=Case(
            When(end_date__lt=today, then=Value(0)),
            When(end_date__gte=today, end_date__lte=soon_cutoff, then=Value(1)),
            When(is_active=True, end_date__lte=stale_cutoff, then=Value(2)),
            default=Value(3), output_field=IntegerField(),
        )
    ).order_by("_priority", "end_date", "pk")
    rows = list(ordered[:config.get("limit", 5)])
    employee_ids = set(Employee.get_instances_for_user(
        "view", context.user, Employee.objects.filter(pk__in=[row.employee_id for row in rows])
    ).values_list("pk", flat=True))
    project_ids = set(Project.get_instances_for_user(
        "view", context.user, Project.objects.filter(pk__in=[row.fund.project_id for row in rows])
    ).values_list("pk", flat=True))
    items, contract_items = [], []
    for item in rows:
        date = item.end_date.isoformat() if item.end_date else None
        days_until = (item.end_date - today).days if item.end_date else None
        state = ("no_date" if days_until is None else "ended" if days_until < 0 else
                 "ending_soon" if days_until <= 30 else
                 "stale" if item.is_active and item.end_date <= stale_cutoff else "current")
        employee_name = str(item.employee)
        project_name = item.fund.project.name
        contract_type = str(item.contract_type) if item.contract_type else ""
        items.append({"key": str(item.pk), "label": employee_name,
                      "secondary": " · ".join(filter(None, [contract_type, project_name])),
                      "date": date, "status": item.get_status_display(), "href": "/app/tools/contracts",
                      "tone": "warning" if item.is_active and item.end_date and item.end_date <= stale_cutoff else "neutral"})
        contract_items.append({"key": str(item.pk), "employee_name": employee_name,
                               "employee_href": f"/app/employees/{item.employee_id}" if item.employee_id in employee_ids else None,
                               "contract_type": contract_type, "project_name": project_name,
                               "project_href": f"/app/projects/{item.fund.project_id}" if item.fund.project_id in project_ids else None,
                               "date": date, "days_until": days_until, "state": state})
    alerts = [{**item, "severity": "warning"} for item in items]
    payload = _payload(count, _("Contracts"), items, alerts=alerts)
    contracts_data = {"summary": {"count": count, "ending_soon_count": ending_soon_count,
                                  "stale_count": stale_count}, "items": contract_items}
    payload["__renderers__"]["contract-list"] = contracts_data
    return payload


def employees(context, config):
    from staff.models import Employee, Employee_Status, Employee_Superior, Team, TeamMate
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
    horizon = today + timedelta(days=days)
    arrivals = Q(entry_date__gte=today, entry_date__lte=horizon)
    departures = Q(exit_date__gte=today, exit_date__lte=horizon)
    arrivals_count = qs.filter(arrivals).count()
    departures_count = qs.filter(departures).count()
    items = [{"key": str(item.pk), "label": str(item),
              "date": (item.entry_date if movement == "arrivals" else item.exit_date).isoformat()
              if (item.entry_date if movement == "arrivals" else item.exit_date) else None,
              "href": f"/app/employees/{item.pk}",
              "status": _("Active") if item.is_active else _("Inactive"), "tone": "neutral"}
             for item in qs.order_by("last_name", "first_name", "pk")[:config.get("limit", 5)]]
    alerts = [{**item, "severity": "info"} for item in items]
    prioritized = qs.annotate(_movement_priority=Case(
        When(departures, then=Value(0)), When(arrivals, then=Value(1)),
        default=Value(2), output_field=IntegerField(),
    )).order_by("_movement_priority", "exit_date", "entry_date", "last_name", "first_name", "pk")
    rows = list(prioritized[:config.get("limit", 5)])
    row_ids = [item.pk for item in rows]
    roles = {}
    for status in Employee_Status.current.select_related("type").filter(employee_id__in=row_ids).order_by("type__name", "pk"):
        roles.setdefault(status.employee_id, status.type.name)
    visible_teams = list(Team.get_instances_for_user(
        "view", context.user,
        Team.objects.filter(Q(leader_id__in=row_ids) | Q(pk__in=TeamMate.objects.filter(employee_id__in=row_ids).values("team_id")))
    ).order_by("name", "pk"))
    teams = {team.leader_id: team for team in visible_teams if team.leader_id in row_ids}
    for membership in TeamMate.objects.filter(employee_id__in=row_ids, team_id__in=[team.pk for team in visible_teams]).filter(
        TeamMate.get_active_filter()
    ).select_related("team").order_by("team__name", "pk"):
        teams.setdefault(membership.employee_id, membership.team)
    employee_items = []
    for item in rows:
        arriving = item.entry_date is not None and today <= item.entry_date <= horizon
        leaving = item.exit_date is not None and today <= item.exit_date <= horizon
        if movement == "arrivals" and arriving:
            state, date = "arriving", item.entry_date
        elif leaving:
            state, date = "leaving", item.exit_date
        elif arriving:
            state, date = "arriving", item.entry_date
        elif item.exit_date is not None and item.exit_date < today:
            state, date = "departed", item.exit_date
        elif item.entry_date is not None and today - timedelta(days=days) <= item.entry_date < today:
            state, date = "arrived_recently", item.entry_date
        else:
            state, date = ("active" if item.is_active else "inactive"), None
        team = teams.get(item.pk)
        employee_items.append({
            "key": str(item.pk), "name": str(item), "href": f"/app/employees/{item.pk}",
            "role": roles.get(item.pk), "team_name": team.name if team else None,
            "team_href": f"/app/teams/{team.pk}" if team else None,
            "state": state, "date": date.isoformat() if date else None,
            "days_until": (date - today).days if date else None,
        })
    payload = _payload(count, _("Employees"), items, alerts=alerts)
    payload["__renderers__"]["employee-movements"] = {
        "summary": {"count": count, "arrivals_count": arrivals_count, "departures_count": departures_count},
        "items": employee_items,
    }
    return payload


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
