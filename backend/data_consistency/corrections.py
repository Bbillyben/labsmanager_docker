"""Date corrections shared by the single and batch consistency actions."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from expense.contract_hub_api_v1 import visible_contracts
from expense.models import Expense
from fund.api_v1 import FundWriteSerializer, fund_capabilities
from fund.financial_tools_api_v1 import visible_funds
from fund.models import Fund
from project.api_v1 import (ProjectParticipantWriteV1Serializer, ProjectWriteV1Serializer,
                            project_capabilities, project_child_capabilities)
from project.models import Participant, Project
from staff.models import Employee
from staff.permissions_v1 import employee_detail_capabilities
from staff.serializers_v1 import EmployeeDetailWriteV1Serializer
from staff.team_api_v1 import validate_model as validate_team_model

from .lifecycle import (ACTIVE_EMPLOYEE_PAST_EXIT, EMPLOYEE_MISSING_EXIT,
                        LIFECYCLE_DEFINITIONS, can_correct_item, correction_values,
                        visible_employees, visible_project_participants, visible_team_mates)
from .service import (CONTRACT_DATES_RULE_KEY, CONTRACT_EMPLOYEE_DATES_RULE_KEY,
                      CONTRACT_FUND_DATES_RULE_KEY, EXPENSE_FUND_DATES_RULE_KEY,
                      FUND_DATES_RULE_KEY, MILESTONE_DATES_RULE_KEY, TASK_DATES_RULE_KEY,
                      CONTRACT_PARTICIPANT_RULE_KEY,
                      active_issues, issue_identity, visible_milestones, visible_projects)


def correction_kind(rule):
    if rule.key == EMPLOYEE_MISSING_EXIT:
        return None
    if rule.key in {definition[0] for definition in LIFECYCLE_DEFINITIONS}:
        return "lifecycle"
    if rule.key == CONTRACT_PARTICIPANT_RULE_KEY:
        return "participant"
    if rule.key == CONTRACT_EMPLOYEE_DATES_RULE_KEY:
        return "employee"
    if rule.key in (CONTRACT_FUND_DATES_RULE_KEY, EXPENSE_FUND_DATES_RULE_KEY):
        return "fund"
    return "project" if rule.key in (CONTRACT_DATES_RULE_KEY, FUND_DATES_RULE_KEY,
                                      MILESTONE_DATES_RULE_KEY, TASK_DATES_RULE_KEY) else None


def extended_bounds(start, end, child_start, child_end):
    # Null bounds are open, as in the existing React correction.
    return (None if start is None or child_start is None else min(start, child_start),
            None if end is None or child_end is None else max(end, child_end))


def can_correct_rule(user, rule):
    kind = correction_kind(rule)
    if kind is None:
        return False
    if kind == "lifecycle":
        return any(can_correct_item(user, rule, item)
                   for item in active_issues(user, rule).iterator(chunk_size=200))
    if kind == "participant":
        employees = Employee.get_instances_for_user("view", user, Employee.objects.all())
        project_ids = (active_issues(user, rule).filter(employee__in=employees).order_by()
                       .values_list("fund__project_id", flat=True).distinct())
        for project in visible_projects(user).filter(pk__in=project_ids).iterator(chunk_size=200):
            if project_child_capabilities(user, project, "participant")["can_add"]:
                return True
        return False
    if kind == "employee":
        parent_path = "employee_id"
    elif kind == "fund":
        parent_path = "fund_item_id" if rule.object_type == "expense" else "fund_id"
    elif rule.object_type == "contract":
        parent_path = "fund__project_id"
    elif rule.object_type == "fund":
        parent_path = "project_id"
    else:
        parent_path = "project_id"
    parent_ids = active_issues(user, rule).order_by().values_list(parent_path, flat=True).distinct().iterator(chunk_size=200)
    for parent_id in parent_ids:
        if kind == "employee":
            parent = Employee.objects.filter(pk=parent_id).first()
            allowed = parent and employee_detail_capabilities(user, parent)["can_change"]
        elif kind == "fund":
            parent = Fund.objects.select_related("project").filter(pk=parent_id).first()
            allowed = (parent and visible_projects(user).filter(pk=parent.project_id).exists()
                       and fund_capabilities(user, parent.project, parent)["can_change"])
        else:
            parent = Project.objects.filter(pk=parent_id).first()
            allowed = (parent and visible_projects(user).filter(pk=parent.pk).exists()
                       and project_capabilities(user, parent)["can_change"])
        if allowed:
            return True
    return False


@transaction.atomic
def correct_lifecycle_issue(request, rule, object_id, expected=None):
    """Shared single/batch correction for deterministic lifecycle checks."""
    visible = {
        "employee": visible_employees,
        "teammate": visible_team_mates,
        "participant": visible_project_participants,
    }[rule.object_type](request.user)
    item = visible.select_for_update(of=("self",)).filter(pk=object_id).first()
    if item is None:
        return "ignored"
    identity = issue_identity(rule, item)
    if expected and any(field in expected and expected[field] != value
                        for field, value in identity.items()):
        return "ignored"
    if not rule.issues(request.user).filter(pk=object_id).exists():
        return "resolved"
    if not active_issues(request.user, rule).filter(pk=object_id).exists():
        return "ignored"
    # Reload after the row lock; serializers use the same current object state
    # as the individual Employee, TeamMate and Participant mutation paths.
    item.refresh_from_db()
    if rule.object_type in ("teammate", "participant"):
        item.employee = get_object_or_404(Employee.objects.select_for_update(), pk=item.employee_id)
    if rule.object_type == "participant":
        item.project = get_object_or_404(Project.objects.select_for_update(), pk=item.project_id)
    if not can_correct_item(request.user, rule, item):
        return "ignored"
    values = correction_values(rule.key, item)
    if rule.object_type == "employee":
        serializer = EmployeeDetailWriteV1Serializer(item, data=values, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    elif rule.object_type == "teammate":
        for field, value in values.items():
            setattr(item, field, value)
        validate_team_model(item)
        item.save(update_fields=list(values))
    else:
        serializer = ProjectParticipantWriteV1Serializer(
            item, data=values, partial=True,
            context={"request": request, "project": item.project},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
    return "corrected"


@transaction.atomic
def correct_participant_issue(request, rule, object_id, expected=None):
    """Create via the same Participant serializer as the individual form."""
    contract = visible_contracts(request.user).select_related("fund", "employee").filter(pk=object_id).first()
    if contract is None:
        return "ignored"
    project_id = contract.fund.project_id
    if not visible_projects(request.user).filter(pk=project_id).exists():
        return "ignored"
    if not Employee.get_instances_for_user(
            "view", request.user, Employee.objects.filter(pk=contract.employee_id)).exists():
        return "ignored"
    if expected and (expected["project_id"] != project_id or
                     expected.get("employee_id") != contract.employee_id or
                     ("fund_id" in expected and expected["fund_id"] != contract.fund_id)):
        return "ignored"
    if not rule.issues(request.user).filter(pk=object_id).exists():
        return "resolved"
    if not active_issues(request.user, rule).filter(pk=object_id).exists():
        return "ignored"
    # Lock the shared Project so concurrent contracts cannot create the same
    # Employee–Project participation between the check and serializer.save().
    project = get_object_or_404(visible_projects(request.user).select_for_update(), pk=project_id)
    if not project_child_capabilities(request.user, project, "participant")["can_add"]:
        return "ignored"
    contract = (visible_contracts(request.user).select_for_update(of=("self",))
                .select_related("fund").filter(pk=object_id).first())
    if contract is None or contract.fund.project_id != project_id:
        return "ignored"
    if expected and (expected["project_id"] != contract.fund.project_id or
                     expected.get("employee_id") != contract.employee_id or
                     ("fund_id" in expected and expected["fund_id"] != contract.fund_id)):
        return "ignored"
    if not rule.issues(request.user).filter(pk=object_id).exists():
        return "resolved"
    if not active_issues(request.user, rule).filter(pk=object_id).exists():
        return "ignored"
    serializer = ProjectParticipantWriteV1Serializer(data={
        "employee_id": contract.employee_id,
        "status": Participant._meta.get_field("status").get_default(),
        "quotity": str(Participant._meta.get_field("quotity").get_default()),
        "start_date": contract.start_date,
        "end_date": contract.end_date,
    }, context={"request": request, "project": project})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return "corrected"


@transaction.atomic
def correct_date_issue(request, rule, object_id, expected=None):
    """Recheck one selected occurrence against fresh, locked parent data."""
    kind = correction_kind(rule)
    if kind is None:
        return "ignored"
    visible = {
        "contract": lambda: visible_contracts(request.user),
        "fund": lambda: visible_funds(request.user),
        "milestone": lambda: visible_milestones(request.user),
        "expense": lambda: Expense.objects.filter(fund_item__in=visible_funds(request.user)),
    }[rule.object_type]()
    source = visible.filter(pk=object_id).first()
    if source is None:
        return "ignored"
    if kind == "employee" and not Employee.get_instances_for_user(
            "view", request.user, Employee.objects.filter(pk=source.employee_id)).exists():
        return "ignored"
    if kind == "fund":
        fund_id = source.fund_item_id if rule.object_type == "expense" else source.fund_id
        if not visible_funds(request.user).filter(pk=fund_id).exists():
            return "ignored"
    if kind in ("project", "fund"):
        project_id = (source.fund_item.project_id if rule.object_type == "expense" else
                      source.fund.project_id if rule.object_type == "contract" else source.project_id)
        if not visible_projects(request.user).filter(pk=project_id).exists():
            return "ignored"
    if not rule.issues(request.user).filter(pk=object_id).exists():
        return "resolved"
    item = active_issues(request.user, rule).filter(pk=object_id).first()
    if item is None:
        return "ignored"
    identity = issue_identity(rule, item)
    if expected and (identity["project_id"] != expected["project_id"] or
                     (rule.object_type == "contract" and identity["employee_id"] != expected.get("employee_id")) or
                     ("fund_id" in expected and rule.serialize(item).get("fund_id") != expected["fund_id"])):
        return "ignored"
    issue = rule.serialize(item)
    parent_id = issue.get("employee_id") if kind == "employee" else issue.get("fund_id") if kind == "fund" else issue["project_id"]
    if kind == "employee":
        parent = get_object_or_404(Employee.objects.select_for_update(), pk=parent_id)
        allowed = employee_detail_capabilities(request.user, parent)["can_change"]
        start_field, end_field = "entry_date", "exit_date"
    elif kind == "fund":
        parent = get_object_or_404(Fund.objects.select_for_update().select_related("project"), pk=parent_id)
        allowed = (visible_projects(request.user).filter(pk=parent.project_id).exists()
                   and fund_capabilities(request.user, parent.project, parent)["can_change"])
        start_field, end_field = "start_date", "end_date"
    else:
        parent = get_object_or_404(Project.objects.select_for_update(), pk=parent_id)
        allowed = (visible_projects(request.user).filter(pk=parent.pk).exists()
                   and project_capabilities(request.user, parent)["can_change"])
        start_field, end_field = "start_date", "end_date"
    if not allowed:
        return "ignored"
    # Another correction may have resolved this issue while the parent lock was acquired.
    item = active_issues(request.user, rule).filter(pk=object_id).first()
    if item is None:
        return "resolved"
    issue = rule.serialize(item)
    from datetime import date
    child_start = date.fromisoformat(issue["child_start_date"]) if issue["child_start_date"] else None
    child_end = date.fromisoformat(issue["child_end_date"]) if issue["child_end_date"] else None
    start, end = extended_bounds(getattr(parent, start_field), getattr(parent, end_field), child_start, child_end)
    fields = {start_field: start, end_field: end}
    if kind == "employee":
        serializer = EmployeeDetailWriteV1Serializer(parent, data=fields, partial=True)
    elif kind == "fund":
        serializer = FundWriteSerializer(parent, data=fields, partial=True,
                                         context={"project": parent.project, "request": request})
    else:
        serializer = ProjectWriteV1Serializer(parent, data=fields, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return "corrected"
