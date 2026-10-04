"""Permission-scoped financial dashboard providers backed by AmountHistory."""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.translation import gettext as _

from expense.models import Expense_point
from fund.models import AmountHistory, Fund
from project.models import Project


def visible_projects(context, config):
    projects = Project.get_instances_for_user("view", context.user, Project.objects.all())
    scope = config.get("project_scope", "context" if context.scope == "project" else "all_visible")
    if scope == "context":
        return projects.filter(pk=context.context_object.pk) if context.context_type == "project" and context.context_object else projects.none()
    if scope == "specific_project":
        project_id = config.get("project_id")
        return projects.filter(pk=project_id) if isinstance(project_id, int) and not isinstance(project_id, bool) else projects.none()
    return projects if scope == "all_visible" else projects.none()


def visible_funds(context, config):
    project_ids = visible_projects(context, config).values("pk")
    return Fund.get_instances_for_user("view", context.user, Fund.objects.filter(project_id__in=project_ids))


def advancement_for_funds(funds, today=None):
    """Spent / planned spend: sum(|expense|) / sum(amount * elapsed fraction).

    Elapsed fraction is clamped to [0, 1]. Future and invalid-date funds do not
    enter the ratio; completed funds contribute their full budget as plan.
    """
    today = today or timezone.localdate()
    amount = Decimal("0")
    spent = Decimal("0")
    planned = Decimal("0")
    for fund in funds:
        if not fund.amount or fund.amount <= 0 or not fund.start_date or not fund.end_date:
            continue
        duration = (fund.end_date - fund.start_date).days
        if duration <= 0 or today <= fund.start_date:
            continue
        elapsed = Decimal(min(duration, (today - fund.start_date).days)) / Decimal(duration)
        amount += fund.amount
        spent += abs(fund.expense or Decimal("0"))
        planned += fund.amount * elapsed
    if not planned:
        return None
    return {"ratio": float(spent / planned), "budget_percent": float(spent / amount * 100),
            "time_percent": float(planned / amount * 100), "spent": float(spent), "amount": float(amount)}


def financial_advancement(context, config):
    result = advancement_for_funds(visible_funds(context, config).only("amount", "expense", "start_date", "end_date"))
    if result is None:
        return {"value": "—", "label": _("Financial advancement"), "tone": "muted"}
    ratio = result["ratio"]
    return {"value": f"{ratio:.2f}", "label": _("Financial advancement"),
            "centered_ratio": ratio, "budget_percent": result["budget_percent"],
            "time_percent": result["time_percent"],
            "tone": "warning" if ratio > 1.2 or ratio < 0.8 else "success"}


def financial_summary(context, config):
    funds = visible_funds(context, config)
    amount = sum((item.amount or Decimal("0") for item in funds), Decimal("0"))
    spent = sum((abs(item.expense or Decimal("0")) for item in funds), Decimal("0"))
    return {"value": float(spent), "label": _("Spent"), "secondary": _("Total: %(amount)s") % {"amount": amount},
            "progress_percent": float(spent / amount * 100) if amount else 0}


def _month(date_value):
    return date(date_value.year, date_value.month, 1)


def _next_month(month):
    return date(month.year + (month.month == 12), month.month % 12 + 1, 1)


def _group(point, kind):
    if kind == "fund":
        return f"fund:{point.fund_id}", point.fund.ref or str(point.fund)
    if kind == "cost_type":
        return f"type:{point.type_id}", point.type.name
    if kind == "institution":
        return f"institution:{point.fund.institution_id}", point.fund.institution.name
    return "total", _("Total")


def expense_trend(context, config):
    funds = list(visible_funds(context, config).select_related("institution", "project"))
    by_fund = {item.pk: item for item in funds}
    if not by_fund:
        return {"series": [], "meta": {"display": config.get("display", "cumulative"), "group_by": config.get("group_by", "total")}}
    points = list(Expense_point.objects.filter(fund_id__in=by_fund).select_related("type", "fund__institution"))
    by_point = {item.pk: item for item in points}
    content_type = ContentType.objects.get_for_model(Expense_point)
    rows = list(AmountHistory.objects.filter(content_type=content_type, object_id__in=by_point).order_by("pk"))
    rows.sort(key=lambda row: (row.value_date or row.created_at, row.pk))
    group_by = config.get("group_by", "total")
    display = config.get("display", "cumulative")
    months = int(config.get("months", 24))
    cutoff = _month(timezone.localdate())
    for month_offset in range(max(0, months - 1)):
        cutoff = date(cutoff.year - (cutoff.month == 1), 12 if cutoff.month == 1 else cutoff.month - 1, 1)
    running = defaultdict(lambda: Decimal("0"))
    monthly = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    period_deltas = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    labels = {}
    for row in rows:
        point = by_point.get(row.object_id)
        if point is None:
            continue
        key, label = _group(point, group_by)
        labels[key] = label
        month = _month(row.value_date or row.created_at)
        previous = running[point.pk]
        current = -row.amount  # Expense_point amounts are stored as signed negatives.
        running[point.pk] = current
        monthly[key][month] += current - previous
        period_deltas[key][month] += -row.delta
    if not monthly:
        return {"series": [], "meta": {"display": display, "group_by": group_by}}
    last = _month(timezone.localdate())
    first = min(min(values) for values in monthly.values())
    first = max(first, cutoff)
    timeline = []
    month = first
    while month <= last:
        timeline.append(month)
        month = _next_month(month)
    if not timeline:
        return {"series": [], "meta": {"display": display, "group_by": group_by}}
    series = []
    for key, values in sorted(monthly.items()):
        running_total = sum((value for month, value in values.items() if month < first), Decimal("0"))
        plotted = []
        for month in timeline:
            change = values.get(month, Decimal("0"))
            running_total += change
            plotted.append({"date": month.isoformat(), "value": float(running_total if display == "cumulative" else period_deltas[key].get(month, Decimal("0")))})
        series.append({"key": key, "label": labels[key], "points": plotted})
    selected_projects = visible_projects(context, config)
    if display == "cumulative" and selected_projects.count() == 1:
        theoretical = []
        for month in timeline:
            month_end = _next_month(month) - date.resolution
            target = Decimal("0")
            for fund in funds:
                if not fund.amount or not fund.start_date or not fund.end_date or fund.end_date <= fund.start_date:
                    continue
                elapsed = max(0, min((month_end - fund.start_date).days, (fund.end_date - fund.start_date).days))
                target += fund.amount * Decimal(elapsed) / Decimal((fund.end_date - fund.start_date).days)
            theoretical.append({"date": month.isoformat(), "value": float(target)})
        series.append({"key": "theoretical_linear", "label": _("Linear trajectory"), "points": theoretical,
                       "kind": "reference"})
    return {"series": series, "meta": {"display": display, "group_by": group_by, "unit": "currency"}}
