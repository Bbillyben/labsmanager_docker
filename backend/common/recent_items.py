"""Resolve a small, explicit set of recently opened React destinations."""

from django.utils.translation import gettext as _

from global_search.business_providers import ContractSearchProvider, FundSearchProvider, TeamSearchProvider
from global_search.providers import EmployeeSearchProvider, ProjectSearchProvider


OBJECT_PROVIDERS = {
    "employee": EmployeeSearchProvider(),
    "project": ProjectSearchProvider(),
    "fund": FundSearchProvider(),
    "contract": ContractSearchProvider(),
    "team": TeamSearchProvider(),
}
OBJECT_IDS = frozenset((*OBJECT_PROVIDERS, "budget", "institution", "funder"))
PAGE_IDS = frozenset(("calendar", "fund-explorer", "budget-explorer", "expenses"))


def resolve_recent_destination(user, url_id, obj_id):
    """Return current, permission-checked display data; never trust stored labels/URLs."""
    if url_id in OBJECT_PROVIDERS:
        if obj_id is None:
            return None
        provider = OBJECT_PROVIDERS[url_id]
        obj = provider.visible_queryset(user).filter(pk=obj_id).first()
        if obj is None:
            return None
        result = provider.make_result(obj, score=0, match_reason=str(_("Recently viewed")))
        return {"type": url_id, "title": result.title, "subtitle": result.subtitle,
                "icon": result.icon, "url": result.url}

    if url_id == "budget":
        from fund.financial_tools_api_v1 import visible_funds
        from fund.models import Budget
        obj = Budget.objects.filter(pk=obj_id, fund__in=visible_funds(user)).select_related("fund__project").first()
        if obj is None:
            return None
        return {"type": url_id, "title": obj.desc or str(obj.cost_type),
                "subtitle": obj.fund.project.name, "icon": "Wallet",
                "url": f"/app/projects/{obj.fund.project_id}/budgets"}

    if url_id in ("institution", "funder"):
        from infos.organization_api_v1 import visible_org
        from django.http import Http404
        kind = "institutions" if url_id == "institution" else "funders"
        try:
            obj = visible_org(user, kind, obj_id)
        except Http404:
            return None
        return {"type": url_id, "title": obj.name, "subtitle": obj.short_name,
                "icon": "Building2", "url": f"/app/organizations/{kind}/{obj.pk}"}

    if url_id == "calendar" and (user.has_perm("common.display_calendar") or user.has_perm("leave.view_leave")):
        return {"type": url_id, "title": _("Calendar"), "subtitle": "", "icon": "CalendarDays", "url": "/app/calendars"}
    pages = {
        "fund-explorer": (_("Fund explorer"), "Landmark", "/app/tools/fund-items"),
        "budget-explorer": (_("Budget explorer"), "Wallet", "/app/tools/budgets"),
        "expenses": (_("Expenses"), "Receipt", "/app/tools/expenses"),
    }
    if url_id in pages:
        title, icon, url = pages[url_id]
        return {"type": url_id, "title": title, "subtitle": "", "icon": icon, "url": url}
    return None
