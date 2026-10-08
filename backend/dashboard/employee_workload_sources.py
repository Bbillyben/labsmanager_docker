"""Visible Employee workload, independent from Contract quotity."""

from django.db.models import Count, Q, Sum
from django.utils import timezone


METRICS = ("project_allocation", "open_tasks", "open_milestones", "open_work_items")


def workload(context, config):
    from endpoints.models import Milestones
    from project.models import Participant, Project
    from staff.models import Employee, Employee_Superior, TeamMate
    from staff.team_api_v1 import visible_teams

    today = timezone.localdate()
    employees = Employee.get_instances_for_user("view", context.user, Employee.objects.all())
    scope = config.get("scope", "single")
    if scope == "single":
        employees = employees.filter(pk=config.get("employee_id"))
    elif scope == "team":
        team_id = config.get("team_id")
        team = visible_teams(context.user).filter(pk=team_id).first()
        if team is None:
            employees = employees.none()
        else:
            members = TeamMate.objects.filter(team_id=team.pk).filter(TeamMate.get_active_filter()).values("employee_id")
            employees = employees.filter(Q(pk=team.leader_id) | Q(pk__in=members))
    elif scope == "subordinates":
        subordinates = Employee_Superior.objects.filter(superior__user=context.user).filter(
            Employee_Superior.get_active_filter()).values("employee_id")
        employees = employees.filter(pk__in=subordinates)
    else:
        employees = employees.none()

    people = list(employees.distinct().order_by("last_name", "first_name", "pk"))
    ids = [person.pk for person in people]
    projects = Project.get_instances_for_user("view", context.user, Project.objects.all())
    active_projects = projects.filter(status=True).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=today),
        Q(end_date__isnull=True) | Q(end_date__gte=today),
    )
    allocation = dict(Participant.objects.filter(employee_id__in=ids, project_id__in=active_projects.values("pk"))
                      .filter(Participant.get_active_filter()).values("employee_id")
                      .annotate(total=Sum("quotity")).values_list("employee_id", "total"))
    work = {
        row["employee"]: row for row in Milestones.objects.filter(
            employee__in=ids, project_id__in=projects.values("pk"), status=False
        ).values("employee").annotate(
            open_tasks=Count("pk", filter=Q(start_date__isnull=False), distinct=True),
            open_milestones=Count("pk", filter=Q(start_date__isnull=True), distinct=True),
        )
    }
    rows = []
    for person in people:
        counts = work.get(person.pk, {})
        tasks = counts.get("open_tasks", 0)
        milestones = counts.get("open_milestones", 0)
        rows.append({"employee_id": person.pk, "employee_name": str(person),
                     "href": f"/app/employees/{person.pk}",
                     "project_allocation": round(float(allocation.get(person.pk, 0) or 0) * 100, 1),
                     "open_tasks": tasks, "open_milestones": milestones,
                     "open_work_items": tasks + milestones})
    if len(rows) == 1:
        person = rows[0]
        return {"mode": "single", "employee": {"id": person["employee_id"],
                "name": person["employee_name"], "href": person["href"]},
                "metrics": [{"key": key, "value": person[key],
                             "unit": "percent" if key == "project_allocation" else "count",
                             "reference_value": 100 if key == "project_allocation" else None}
                            for key in METRICS]}
    metric = config.get("metric", "project_allocation")
    if metric not in METRICS:
        metric = "project_allocation"
    rows.sort(key=lambda row: (-row[metric], row["employee_name"].casefold(), row["employee_id"]))
    return {"mode": "comparison", "metric": metric,
            "unit": "percent" if metric == "project_allocation" else "count",
            "reference_value": 100 if metric == "project_allocation" else None,
            "items": [{"employee_id": row["employee_id"], "employee_name": row["employee_name"],
                       "href": row["href"], "value": row[metric]}
                      for row in rows[:config.get("limit", 5)]]}
