"""Permission-bounded, queryable Data Consistency rules."""

from dataclasses import dataclass

from django.db.models import Exists, F, OuterRef, Q
from django.utils.translation import gettext as _

from endpoints.models import Milestones
from expense.contract_hub_api_v1 import visible_contracts
from expense.models import Expense
from fund.financial_tools_api_v1 import visible_funds
from project.models import Participant, Project
from staff.models import Employee

from .models import DataConsistencyException

CONTRACT_PARTICIPANT_RULE_KEY = "contract_employee_not_project_participant"
CONTRACT_DATES_RULE_KEY = "contract_outside_project_dates"
FUND_DATES_RULE_KEY = "fund_outside_project_dates"
CONTRACT_EMPLOYEE_DATES_RULE_KEY = "contract_outside_employee_dates"
MILESTONE_DATES_RULE_KEY = "milestone_outside_project_dates"
TASK_DATES_RULE_KEY = "task_outside_project_dates"
CONTRACT_FUND_DATES_RULE_KEY = "contract_outside_fund_dates"
EXPENSE_FUND_DATES_RULE_KEY = "expense_outside_fund_dates"
PROJECT_LEADER_RULE_KEY = "project_without_leader"

IDENTITY_PATHS = {
    "contract": {"contract_id": "pk", "employee_id": "employee_id", "project_id": "fund__project_id"},
    "fund": {"fund_id": "pk", "project_id": "project_id"},
    "milestone": {"milestone_id": "pk", "project_id": "project_id"},
    "expense": {"expense_id": "pk", "project_id": "fund_item__project_id"},
    "project": {"project_id": "pk"},
}
OBJECT_ID_FIELDS = {
    "contract": "contract_id", "fund": "fund_id", "milestone": "milestone_id",
    "expense": "expense_id", "project": "project_id",
}


@dataclass(frozen=True)
class ConsistencyRule:
    key: str
    category: str
    issues: object
    serialize: object
    object_type: str = "contract"


def outside_parent_dates(parent_path, start_field="start_date", end_field="end_date",
                         parent_start="start_date", parent_end="end_date"):
    """A null boundary is open; a bounded parent cannot contain an open child."""
    start = f"{parent_path}__{parent_start}"
    end = f"{parent_path}__{parent_end}"
    return (
        Q(**{f"{start}__isnull": False}) &
        (Q(**{f"{start_field}__isnull": True}) | Q(**{f"{start_field}__lt": F(start)}))
    ) | (
        Q(**{f"{end}__isnull": False}) &
        (Q(**{f"{end_field}__isnull": True}) | Q(**{f"{end_field}__gt": F(end)}))
    )


def outside_project_dates(project_path):
    return outside_parent_dates(project_path)


def date_fields(item, parent, start_field="start_date", end_field="end_date",
                parent_start="start_date", parent_end="end_date", parent_kind="project"):
    def iso(value):
        return value.isoformat() if value else None

    child_start, child_end = getattr(item, start_field), getattr(item, end_field)
    bound_start, bound_end = getattr(parent, parent_start), getattr(parent, parent_end)
    before = bound_start is not None and (child_start is None or child_start < bound_start)
    after = bound_end is not None and (child_end is None or child_end > bound_end)
    return {
        "reason": "both" if before and after else "starts_before_project" if before else "ends_after_project",
        "parent_kind": parent_kind,
        "parent_start_date": iso(bound_start), "parent_end_date": iso(bound_end),
        "project_start_date": iso(bound_start) if parent_kind == "project" else None,
        "project_end_date": iso(bound_end) if parent_kind == "project" else None,
        "child_start_date": iso(child_start), "child_end_date": iso(child_end),
    }


def visible_projects(user):
    return Project.get_instances_for_user("view", user, Project.objects.all())


def contracts_without_participant(user):
    participants = Participant.objects.filter(
        project_id=OuterRef("fund__project_id"), employee_id=OuterRef("employee_id"),
    )
    return (visible_contracts(user).alias(_has_participant=Exists(participants))
            .filter(_has_participant=False).select_related("employee", "fund__project")
            .order_by("pk"))


def contract_participant_issue(contract):
    project, employee = contract.fund.project, contract.employee
    return {
        "rule_key": CONTRACT_PARTICIPANT_RULE_KEY, "category": "contracts",
        "contract_id": contract.pk, "employee_id": employee.pk, "project_id": project.pk,
        "label": _("%(employee)s is not a participant in %(project)s") % {
            "employee": str(employee), "project": project.name,
        },
        "employee_name": str(employee), "project_name": project.name,
    }


def contracts_outside_project_dates(user):
    return (visible_contracts(user).filter(fund__project__in=visible_projects(user))
            .filter(outside_project_dates("fund__project"))
            .select_related("employee", "fund__project").order_by("pk"))


def contract_dates_issue(contract):
    project = contract.fund.project
    return {
        "rule_key": CONTRACT_DATES_RULE_KEY, "category": "contracts",
        "contract_id": contract.pk, "employee_id": contract.employee_id, "project_id": project.pk,
        "label": _("Contract #%(contract)s extends beyond project %(project)s") % {
            "contract": contract.pk, "project": project.name,
        },
        "employee_name": str(contract.employee), "project_name": project.name,
        **date_fields(contract, project),
    }


def funds_outside_project_dates(user):
    return (visible_funds(user).filter(outside_project_dates("project"))
            .select_related("project").order_by("pk"))


def fund_dates_issue(fund):
    project = fund.project
    return {
        "rule_key": FUND_DATES_RULE_KEY, "category": "funds",
        "fund_id": fund.pk, "project_id": project.pk,
        "label": _("Fund %(fund)s extends beyond project %(project)s") % {
            "fund": fund.ref or f"#{fund.pk}", "project": project.name,
        },
        "project_name": project.name, **date_fields(fund, project),
    }


def contracts_outside_employee_dates(user):
    employees = Employee.get_instances_for_user("view", user, Employee.objects.all())
    return (visible_contracts(user).filter(employee__in=employees)
            .filter(outside_parent_dates("employee", parent_start="entry_date", parent_end="exit_date"))
            .select_related("employee", "fund__project").order_by("pk"))


def contract_employee_dates_issue(contract):
    employee = contract.employee
    return {
        "rule_key": CONTRACT_EMPLOYEE_DATES_RULE_KEY, "category": "contracts",
        "contract_id": contract.pk, "employee_id": employee.pk,
        "project_id": contract.fund.project_id,
        "label": _("Contract #%(contract)s extends beyond employee %(employee)s") % {
            "contract": contract.pk, "employee": str(employee),
        },
        "employee_name": str(employee), "project_name": contract.fund.project.name,
        **date_fields(contract, employee, parent_start="entry_date", parent_end="exit_date",
                      parent_kind="employee"),
    }


def visible_milestones(user):
    return Milestones.objects.filter(project__in=visible_projects(user))


def milestones_outside_project_dates(user):
    # A missing start denotes a point-in-time milestone; its deadline is its date.
    return (visible_milestones(user).filter(start_date__isnull=True, end_date__isnull=False)
            .filter(outside_parent_dates("project", "end_date", "end_date"))
            .select_related("project").order_by("pk"))


def tasks_outside_project_dates(user):
    return (visible_milestones(user).filter(start_date__isnull=False)
            .filter(outside_parent_dates("project"))
            .select_related("project").order_by("pk"))


def milestone_date_issue(item, rule_key):
    point = rule_key == MILESTONE_DATES_RULE_KEY
    return {
        "rule_key": rule_key, "category": "planning", "milestone_id": item.pk,
        "project_id": item.project_id,
        "label": _("%(kind)s %(name)s extends beyond project %(project)s") % {
            "kind": _("Milestone") if point else _("Task"),
            "name": item.name, "project": item.project.name,
        },
        "project_name": item.project.name,
        **date_fields(item, item.project, "end_date" if point else "start_date", "end_date"),
    }


def milestone_dates_issue(item):
    return milestone_date_issue(item, MILESTONE_DATES_RULE_KEY)


def task_dates_issue(item):
    return milestone_date_issue(item, TASK_DATES_RULE_KEY)


def contracts_outside_fund_dates(user):
    return (visible_contracts(user).filter(fund__in=visible_funds(user))
            .filter(outside_parent_dates("fund"))
            .select_related("employee", "fund__project").order_by("pk"))


def contract_fund_dates_issue(contract):
    fund = contract.fund
    return {
        "rule_key": CONTRACT_FUND_DATES_RULE_KEY, "category": "contracts",
        "contract_id": contract.pk, "employee_id": contract.employee_id,
        "fund_id": fund.pk, "project_id": fund.project_id,
        "label": _("Contract #%(contract)s extends beyond fund %(fund)s") % {
            "contract": contract.pk, "fund": fund.ref or f"#{fund.pk}",
        },
        "employee_name": str(contract.employee), "project_name": fund.project.name,
        **date_fields(contract, fund, parent_kind="fund"),
    }


def expenses_outside_fund_dates(user):
    # Expense.date is the business date; value_date belongs to Expense_point.
    return (Expense.objects.filter(fund_item__in=visible_funds(user))
            .filter(outside_parent_dates("fund_item", "date", "date"))
            .select_related("fund_item__project").order_by("pk"))


def expense_fund_dates_issue(expense):
    fund = expense.fund_item
    return {
        "rule_key": EXPENSE_FUND_DATES_RULE_KEY, "category": "expenses",
        "expense_id": expense.pk, "fund_id": fund.pk, "project_id": fund.project_id,
        "label": _("Expense #%(expense)s is outside fund %(fund)s dates") % {
            "expense": expense.pk, "fund": fund.ref or f"#{fund.pk}",
        },
        "project_name": fund.project.name,
        **date_fields(expense, fund, "date", "date", parent_kind="fund"),
    }


def projects_without_leader(user):
    leaders = Participant.objects.filter(project_id=OuterRef("pk"), status="l")
    return (visible_projects(user).alias(_has_leader=Exists(leaders))
            .filter(_has_leader=False).order_by("pk"))


def project_without_leader_issue(project):
    return {
        "rule_key": PROJECT_LEADER_RULE_KEY, "category": "projects",
        "project_id": project.pk, "project_name": project.name,
        "label": _("Project %(project)s has no leader") % {"project": project.name},
    }


RULES = (
    ConsistencyRule(CONTRACT_PARTICIPANT_RULE_KEY, "contracts", contracts_without_participant,
                    contract_participant_issue),
    ConsistencyRule(CONTRACT_DATES_RULE_KEY, "contracts", contracts_outside_project_dates,
                    contract_dates_issue),
    ConsistencyRule(FUND_DATES_RULE_KEY, "funds", funds_outside_project_dates,
                    fund_dates_issue, "fund"),
    ConsistencyRule(CONTRACT_EMPLOYEE_DATES_RULE_KEY, "contracts", contracts_outside_employee_dates,
                    contract_employee_dates_issue),
    ConsistencyRule(MILESTONE_DATES_RULE_KEY, "planning", milestones_outside_project_dates,
                    milestone_dates_issue, "milestone"),
    ConsistencyRule(TASK_DATES_RULE_KEY, "planning", tasks_outside_project_dates,
                    task_dates_issue, "milestone"),
    ConsistencyRule(CONTRACT_FUND_DATES_RULE_KEY, "contracts", contracts_outside_fund_dates,
                    contract_fund_dates_issue),
    ConsistencyRule(EXPENSE_FUND_DATES_RULE_KEY, "expenses", expenses_outside_fund_dates,
                    expense_fund_dates_issue, "expense"),
    ConsistencyRule(PROJECT_LEADER_RULE_KEY, "projects", projects_without_leader,
                    project_without_leader_issue, "project"),
)
RULES_BY_KEY = {rule.key: rule for rule in RULES}


def issue_identity(rule, item):
    def value(path):
        result = item
        for part in path.split("__"):
            result = getattr(result, part)
        return result
    return {field: value(path) for field, path in IDENTITY_PATHS[rule.object_type].items()}


def open_exceptions():
    return DataConsistencyException.objects.filter(closed_at__isnull=True)


def active_issues(user, rule):
    matching = open_exceptions().filter(rule_key=rule.key, **{
        field: OuterRef(path) for field, path in IDENTITY_PATHS[rule.object_type].items()
    })
    return rule.issues(user).alias(_accepted=Exists(matching)).filter(_accepted=False)


def accepted_exceptions(user, rule):
    current_issues = rule.issues(user).filter(**{
        path: OuterRef(field) for field, path in IDENTITY_PATHS[rule.object_type].items()
    })
    return (open_exceptions().filter(rule_key=rule.key)
            .alias(_current_issue=Exists(current_issues))
            .filter(_current_issue=True).select_related("accepted_by").order_by("pk"))


def accepted_issue(exception, item, rule):
    return {
        **rule.serialize(item),
        "exception": {
            "id": exception.pk,
            "accepted_by": exception.accepted_by.get_username() if exception.accepted_by else None,
            "accepted_at": exception.accepted_at.isoformat(),
            "reason": exception.reason,
        },
    }


def summary(user):
    categories, rules, accepted_total = {}, [], 0
    for rule in RULES:
        count = active_issues(user, rule).count()
        accepted_count = accepted_exceptions(user, rule).count()
        accepted_total += accepted_count
        categories[rule.category] = categories.get(rule.category, 0) + count
        rules.append({"rule_key": rule.key, "category": rule.category,
                      "count": count, "accepted_count": accepted_count})
    return {
        "total": sum(categories.values()), "accepted_total": accepted_total,
        "categories": [{"key": key, "count": count} for key, count in categories.items() if count],
        "rules": rules,
    }
