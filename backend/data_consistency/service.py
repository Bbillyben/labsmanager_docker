"""Small registry of checks over canonically visible business objects."""

from dataclasses import dataclass

from django.db.models import Exists, OuterRef
from django.utils.translation import gettext as _

from expense.contract_hub_api_v1 import visible_contracts
from project.models import Participant

from .models import DataConsistencyException

CONTRACT_PARTICIPANT_RULE_KEY = "contract_employee_not_project_participant"


@dataclass(frozen=True)
class ConsistencyRule:
    key: str
    category: str
    issues: object
    serialize: object


def contracts_without_participant(user):
    participants = Participant.objects.filter(
        project_id=OuterRef("fund__project_id"),
        employee_id=OuterRef("employee_id"),
    )
    return (
        visible_contracts(user)
        .alias(_has_participant=Exists(participants))
        .filter(_has_participant=False)
        .select_related("employee", "fund__project")
        .order_by("pk")
    )


def contract_participant_issue(contract):
    project = contract.fund.project
    employee = contract.employee
    return {
        "rule_key": CONTRACT_PARTICIPANT_RULE_KEY,
        "category": "contracts",
        "contract_id": contract.pk,
        "employee_id": employee.pk,
        "project_id": project.pk,
        "label": _("%(employee)s is not a participant in %(project)s") % {
            "employee": str(employee), "project": project.name,
        },
        "employee_name": str(employee),
        "project_name": project.name,
    }


RULES = (
    ConsistencyRule(
        CONTRACT_PARTICIPANT_RULE_KEY,
        "contracts",
        contracts_without_participant,
        contract_participant_issue,
    ),
)
RULES_BY_KEY = {rule.key: rule for rule in RULES}


def open_exceptions():
    return DataConsistencyException.objects.filter(closed_at__isnull=True)


def active_issues(user, rule):
    matching = open_exceptions().filter(
        rule_key=rule.key,
        contract_id=OuterRef("pk"),
        employee_id=OuterRef("employee_id"),
        project_id=OuterRef("fund__project_id"),
    )
    return rule.issues(user).alias(_accepted=Exists(matching)).filter(_accepted=False)


def accepted_exceptions(user, rule):
    current_issues = rule.issues(user).filter(
        pk=OuterRef("contract_id"),
        employee_id=OuterRef("employee_id"),
        fund__project_id=OuterRef("project_id"),
    )
    return (open_exceptions().filter(rule_key=rule.key)
            .alias(_current_issue=Exists(current_issues))
            .filter(_current_issue=True).select_related("accepted_by").order_by("pk"))


def accepted_issue(exception, contract, rule):
    return {
        **rule.serialize(contract),
        "exception": {
            "id": exception.pk,
            "accepted_by": exception.accepted_by.get_username() if exception.accepted_by else None,
            "accepted_at": exception.accepted_at.isoformat(),
            "reason": exception.reason,
        },
    }


def summary(user):
    categories = {}
    rules = []
    accepted_total = 0
    for rule in RULES:
        count = active_issues(user, rule).count()
        accepted_count = accepted_exceptions(user, rule).count()
        accepted_total += accepted_count
        categories[rule.category] = categories.get(rule.category, 0) + count
        rules.append({"rule_key": rule.key, "category": rule.category,
                      "count": count, "accepted_count": accepted_count})
    return {
        "total": sum(categories.values()),
        "accepted_total": accepted_total,
        "categories": [{"key": key, "count": count} for key, count in categories.items()],
        "rules": rules,
    }
