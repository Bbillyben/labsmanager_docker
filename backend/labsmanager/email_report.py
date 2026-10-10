"""Presentation data for the periodic email, scoped to its already-visible funds."""

from collections import defaultdict
from decimal import Decimal

from django.utils import timezone

from dashboard.business_sources import _project_funding_pace, _project_temporal_percent
from project.views import get_project_fund_overviewReport_bytType


def _financial_row(item, amount, expense, available, available_focus, *, absolute_ratio=False):
    amount = amount if amount is not None else None
    expense = expense if expense is not None else None
    temporal_percent = _project_temporal_percent(item, timezone.localdate())
    consumption_ratio = float(expense / amount) if amount not in (None, 0) and expense is not None else None
    if absolute_ratio and consumption_ratio is not None:
        consumption_ratio = abs(consumption_ratio)
    financial_percent = abs(consumption_ratio) * 100 if consumption_ratio is not None else None
    return {
        "amount": amount,
        "expense": expense,
        "available": available,
        "available_focus": available_focus,
        "consumption_ratio": consumption_ratio,
        "consumption_bar": min(100, max(0, financial_percent)) if financial_percent is not None else None,
        "temporal_ratio": temporal_percent / 100 if temporal_percent is not None else None,
        "temporal_bar": min(100, max(0, temporal_percent)) if temporal_percent is not None else None,
        "funding_pace": _project_funding_pace({
            "temporal_percent": temporal_percent,
            "financial": {"percent": financial_percent} if financial_percent is not None else None,
        }),
    }


def periodic_funding_rows(projects, funds):
    """Build compact report rows without querying funds outside the mail's view scope."""
    funds_by_project = defaultdict(list)
    for fund in funds:
        funds_by_project[fund.project_id].append(fund)

    project_rows = []
    fund_rows = []
    for project in projects:
        visible = funds_by_project[project.pk]
        if visible:
            amount = sum((fund.amount or Decimal("0") for fund in visible), Decimal("0"))
            expense = sum((fund.expense or Decimal("0") for fund in visible), Decimal("0"))
            available = sum((fund.available or Decimal("0") for fund in visible), Decimal("0"))
            available_focus = sum((fund.available_f or Decimal("0") for fund in visible), Decimal("0"))
            financial = _financial_row(project, amount, expense, available, available_focus, absolute_ratio=True)
        else:
            financial = _financial_row(project, None, None, None, None)
        project_rows.append({"object": project, **financial,
                             "type_summary": get_project_fund_overviewReport_bytType(project.pk, funds=[fund.pk for fund in visible]) if visible else None})
        for fund in visible:
            fund_rows.append({"object": fund, **_financial_row(
                fund, fund.amount, fund.expense, fund.available, fund.available_f,
            )})
    return project_rows, fund_rows
