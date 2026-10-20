"""Employee and membership lifecycle checks for the consistency registry."""

from django.db.models import F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from project.models import Participant, Project
from staff.models import Employee, TeamMate
from staff.team_api_v1 import visible_teams
from staff.team_api_v1 import can_change_team
from staff.permissions_v1 import employee_detail_capabilities
from project.api_v1 import project_child_capabilities

EMPLOYEE_MISSING_EXIT = "inactive_employee_without_exit_date"
INACTIVE_TEAM_MATE = "inactive_employee_active_team_mate"
INACTIVE_PROJECT_PARTICIPANT = "inactive_employee_active_project_participant"
ACTIVE_EMPLOYEE_PAST_EXIT = "active_employee_past_exit_date"
TEAM_MATE_BEFORE_EMPLOYEE = "team_mate_before_employee_entry"
PROJECT_PARTICIPANT_BEFORE_EMPLOYEE = "project_participant_before_employee_entry"
TEAM_MATE_AFTER_EMPLOYEE = "team_mate_after_employee_exit"
PROJECT_PARTICIPANT_AFTER_PROJECT = "project_participant_after_project_end"


def visible_employees(user):
    return Employee.get_instances_for_user("view", user, Employee.objects.all())


def visible_team_mates(user):
    return (TeamMate.objects.filter(team__in=visible_teams(user), employee__in=visible_employees(user))
            .select_related("team", "employee"))


def visible_project_participants(user):
    projects = Project.get_instances_for_user("view", user, Project.objects.all())
    return (Participant.objects.filter(project__in=projects, employee__in=visible_employees(user))
            .select_related("project", "employee"))


def active_period(today):
    # ActiveDateMixin uses inclusive endpoints and treats null as open.
    return ((Q(start_date__isnull=True) | Q(start_date__lte=today)) &
            (Q(end_date__isnull=True) | Q(end_date__gte=today)))


def inactive_employees_without_exit(user):
    return visible_employees(user).filter(is_active=False, exit_date__isnull=True).order_by("pk")


def active_employees_past_exit(user):
    return visible_employees(user).filter(is_active=True, exit_date__lt=timezone.localdate()).order_by("pk")


def inactive_team_mates(user):
    return visible_team_mates(user).filter(employee__is_active=False).filter(active_period(timezone.localdate())).order_by("pk")


def inactive_project_participants(user):
    return visible_project_participants(user).filter(employee__is_active=False).filter(active_period(timezone.localdate())).order_by("pk")


def team_mates_before_employee(user):
    return (visible_team_mates(user).filter(employee__entry_date__isnull=False)
            .filter(Q(start_date__isnull=True) | Q(start_date__lt=F("employee__entry_date")))
            .order_by("pk"))


def project_participants_before_employee(user):
    return (visible_project_participants(user).filter(employee__entry_date__isnull=False)
            .filter(Q(start_date__isnull=True) | Q(start_date__lt=F("employee__entry_date")))
            .order_by("pk"))


def team_mates_after_employee(user):
    today = timezone.localdate()
    return (visible_team_mates(user).filter(employee__exit_date__isnull=False)
            .filter(Q(end_date__isnull=True) | Q(end_date__gt=F("employee__exit_date")))
            .exclude(Q(employee__is_active=False) & active_period(today))
            .order_by("pk"))


def project_participants_after_project(user):
    return (visible_project_participants(user).filter(project__end_date__isnull=False)
            .filter(Q(end_date__isnull=True) | Q(end_date__gt=F("project__end_date")))
            .order_by("pk"))


def employee_issue(item, key):
    return {
        "rule_key": key, "category": "employees", "employee_id": item.pk,
        "employee_name": str(item), "project_id": None, "project_name": "",
        "label": str(item), "object_label": str(item),
        "employee_start_date": item.entry_date, "employee_end_date": item.exit_date,
        **({"manual_url": f"/employees/{item.pk}"} if key == EMPLOYEE_MISSING_EXIT else {}),
    }


def relation_issue(item, key, kind):
    employee = item.employee
    result = {
        "rule_key": key, "category": "teams" if kind == "teammate" else "projects",
        "employee_id": employee.pk, "employee_name": str(employee),
        "label": f"{employee} · {item.team.name if kind == 'teammate' else item.project.name}",
        "object_label": item.team.name if kind == "teammate" else item.project.name,
        "child_start_date": item.start_date, "child_end_date": item.end_date,
        "employee_start_date": employee.entry_date, "employee_end_date": employee.exit_date,
    }
    if kind == "teammate":
        result.update(teammate_id=item.pk, team_id=item.team_id,
                      team_name=item.team.name, project_id=None, project_name="")
    else:
        result.update(participant_id=item.pk, project_id=item.project_id,
                      project_name=item.project.name, project_end_date=item.project.end_date)
    return result


LIFECYCLE_DEFINITIONS = (
    (EMPLOYEE_MISSING_EXIT, "employees", inactive_employees_without_exit,
     lambda item: employee_issue(item, EMPLOYEE_MISSING_EXIT), "employee", _("Inactive employee without an exit date")),
    (INACTIVE_TEAM_MATE, "teams", inactive_team_mates,
     lambda item: relation_issue(item, INACTIVE_TEAM_MATE, "teammate"), "teammate", _("Inactive employee with an active team membership")),
    (INACTIVE_PROJECT_PARTICIPANT, "projects", inactive_project_participants,
     lambda item: relation_issue(item, INACTIVE_PROJECT_PARTICIPANT, "participant"), "participant", _("Inactive employee with an active project participation")),
    (ACTIVE_EMPLOYEE_PAST_EXIT, "employees", active_employees_past_exit,
     lambda item: employee_issue(item, ACTIVE_EMPLOYEE_PAST_EXIT), "employee", _("Active employee past the exit date")),
    (TEAM_MATE_BEFORE_EMPLOYEE, "teams", team_mates_before_employee,
     lambda item: relation_issue(item, TEAM_MATE_BEFORE_EMPLOYEE, "teammate"), "teammate", _("Team membership starts before employee entry")),
    (PROJECT_PARTICIPANT_BEFORE_EMPLOYEE, "projects", project_participants_before_employee,
     lambda item: relation_issue(item, PROJECT_PARTICIPANT_BEFORE_EMPLOYEE, "participant"), "participant", _("Project participation starts before employee entry")),
    (TEAM_MATE_AFTER_EMPLOYEE, "teams", team_mates_after_employee,
     lambda item: relation_issue(item, TEAM_MATE_AFTER_EMPLOYEE, "teammate"), "teammate", _("Team membership exceeds employee exit")),
    (PROJECT_PARTICIPANT_AFTER_PROJECT, "projects", project_participants_after_project,
     lambda item: relation_issue(item, PROJECT_PARTICIPANT_AFTER_PROJECT, "participant"), "participant", _("Project participation exceeds project end")),
)


def correction_values(key, item):
    """Return only deterministic, valid date changes; never extend a period."""
    today = timezone.localdate()
    if key == ACTIVE_EMPLOYEE_PAST_EXIT:
        return {"is_active": False} if item.is_active and item.exit_date and item.exit_date < today else None
    if key in (INACTIVE_TEAM_MATE, INACTIVE_PROJECT_PARTICIPANT):
        exit_date = item.employee.exit_date
        # The end is inclusive: an end on or after today remains active.
        if exit_date is None or exit_date >= today:
            return None
        if key == INACTIVE_PROJECT_PARTICIPANT and item.start_date is None:
            return None
        end = min(item.end_date, exit_date) if item.end_date else exit_date
        return {"end_date": end} if not item.start_date or end >= item.start_date else None
    if key in (TEAM_MATE_BEFORE_EMPLOYEE, PROJECT_PARTICIPANT_BEFORE_EMPLOYEE):
        start = item.employee.entry_date
        return {"start_date": start} if start and (not item.end_date or start <= item.end_date) else None
    if key == TEAM_MATE_AFTER_EMPLOYEE:
        end = item.employee.exit_date
        return {"end_date": end} if end and (not item.start_date or end >= item.start_date) else None
    if key == PROJECT_PARTICIPANT_AFTER_PROJECT:
        end = item.project.end_date
        return {"end_date": end} if end and item.start_date and end >= item.start_date else None
    return None


def can_correct_item(user, rule, item):
    if correction_values(rule.key, item) is None:
        return False
    if rule.object_type == "employee":
        return employee_detail_capabilities(user, item)["can_change"]
    if rule.object_type == "teammate":
        return can_change_team(user, item.team)
    return project_child_capabilities(user, item.project, "participant")["can_change"]
