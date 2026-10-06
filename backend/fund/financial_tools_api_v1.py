"""Read-only financial explorers using the same visible parents as Project funding."""

from collections import Counter
from decimal import Decimal

from django.db.models import F, Q
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as django_filters
from rest_framework import filters, generics, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from dashboard.utils import getDashboardTimeSlot
from expense.contract_hub_api_v1 import visible_contracts
from expense.models import Contract_type, Expense
from expense.resources import ExpenseResource
from fund.api_v1 import cost_type_data, item_data, money
from fund.models import Budget, Cost_Type, Fund, Fund_Institution, Fund_Item
from fund.resources import BudgetResource, FundItemResource
from labsmanager.admin_links_v1 import get_admin_change_url
from labsmanager.list_export_v1 import ListExportContentNegotiation, export_list_queryset
from labsmanager.pagination import LabPagination
from project.models import Institution, Participant, Project
from staff.models import Employee, Employee_Type


def visible_funds(user):
    """Intersect the established Project and Fund view scopes."""
    projects = Project.get_instances_for_user("view", user, Project.objects.all())
    return Fund.get_instances_for_user("view", user, Fund.objects.filter(project__in=projects))


def visible_financial_items(model, user):
    """Use the parent visibility already enforced by Project funding endpoints."""
    relation = "fund_item" if model is Expense else "fund"
    return model.objects.filter(**{f"{relation}__in": visible_funds(user)})


def cost_descendants(queryset, field, value):
    types = Cost_Type.objects.filter(pk=value).get_descendants(include_self=True)
    return queryset.filter(**{f"{field}__in": types})


class FinancialFilter(django_filters.FilterSet):
    active = django_filters.BooleanFilter(method="by_active")
    project = django_filters.NumberFilter(field_name="fund__project_id")
    institution = django_filters.NumberFilter(field_name="fund__institution_id")
    funder = django_filters.NumberFilter(field_name="fund__funder_id")
    fundref = django_filters.CharFilter(field_name="fund__ref", lookup_expr="icontains")
    available = django_filters.NumberFilter(method="by_available")

    def by_active(self, queryset, name, value):
        active = Fund.get_active_filter()
        return queryset.filter(Q(fund__in=Fund.objects.filter(active)) if value else ~Q(fund__in=Fund.objects.filter(active)))

    def by_available(self, queryset, name, value):
        return queryset.annotate(_available=Coalesce(F("amount"), Decimal("0")) + Coalesce(F("expense"), Decimal("0"))).filter(_available__gte=value)


class FundItemFilter(FinancialFilter):
    type = django_filters.NumberFilter(method="by_type")
    participant = django_filters.NumberFilter(method="by_participant")
    stale = django_filters.BooleanFilter(method="by_stale")

    class Meta:
        model = Fund_Item
        fields = ()

    def by_type(self, queryset, name, value):
        return cost_descendants(queryset, "type", value)

    def by_participant(self, queryset, name, value):
        projects = Participant.objects.filter(employee_id=value).values("project_id")
        return queryset.filter(fund__project_id__in=projects)

    def by_stale(self, queryset, name, value):
        condition = Q(fund__project__status=True)
        slot = getDashboardTimeSlot(self.request)
        if "from" in slot:
            condition &= Q(fund__end_date__gte=slot["from"])
        if "to" in slot:
            condition &= Q(fund__end_date__lte=slot["to"])
        return queryset.filter(condition) if value else queryset.exclude(condition)


class BudgetFilter(FinancialFilter):
    type = django_filters.NumberFilter(method="by_type")
    contract_type = django_filters.NumberFilter(field_name="contract_type__id")
    employee = django_filters.NumberFilter(field_name="employee_id")
    emp_type = django_filters.NumberFilter(field_name="emp_type_id")

    class Meta:
        model = Budget
        fields = ()

    def by_type(self, queryset, name, value):
        return cost_descendants(queryset, "cost_type", value)

    def by_available(self, queryset, name, value):
        return queryset.annotate(_available=Coalesce(F("amount"), Decimal("0")) - Coalesce(F("expense"), Decimal("0"))).filter(_available__gte=value)


class ExpenseFilter(django_filters.FilterSet):
    type = django_filters.NumberFilter(method="by_type")
    after = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    before = django_filters.DateFilter(field_name="date", lookup_expr="lte")
    desc = django_filters.CharFilter(field_name="desc", lookup_expr="icontains")
    project = django_filters.NumberFilter(field_name="fund_item__project_id")
    funder = django_filters.NumberFilter(field_name="fund_item__funder_id")
    institution = django_filters.NumberFilter(field_name="fund_item__institution_id")
    status = django_filters.ChoiceFilter(choices=Expense.status_mod)
    fundref = django_filters.CharFilter(field_name="fund_item__ref", lookup_expr="icontains")
    expense_id = django_filters.CharFilter(field_name="expense_id", lookup_expr="icontains")

    class Meta:
        model = Expense
        fields = ()

    def by_type(self, queryset, name, value):
        return cost_descendants(queryset, "type", value)


class FinancialList(generics.ListAPIView):
    """Apply a single visible, filtered, ordered queryset to list and export."""

    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = LabPagination
    filter_backends = (django_filters.DjangoFilterBackend, filters.OrderingFilter)
    model = None
    relation = "fund"

    def get_queryset(self):
        queryset = visible_financial_items(self.model, self.request.user)
        if self.model is Fund_Item:
            return queryset.annotate(_available=Coalesce(F("amount"), Decimal("0")) + Coalesce(F("expense"), Decimal("0"))).select_related("type", "fund__project", "fund__funder", "fund__institution")
        if self.model is Budget:
            return queryset.annotate(_available=Coalesce(F("amount"), Decimal("0")) - Coalesce(F("expense"), Decimal("0"))).select_related("cost_type", "fund__project", "fund__funder", "fund__institution", "emp_type", "employee").prefetch_related("contract_type")
        return queryset.select_related("type", "fund_item__project", "fund_item__funder", "fund_item__institution", "budget_item", "contract_expense__contract__employee").distinct()

    def get_serializer_context(self):
        return super().get_serializer_context()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset()).distinct()
        page = self.paginate_queryset(queryset)
        rows = list(page if page is not None else queryset)
        data = self.rows(rows)
        return self.get_paginated_response(data) if page is not None else Response(data)

    def relation_data(self, fund, project_ids, can_open_org):
        return {"project": {"id": fund.project_id, "name": fund.project.name, "can_view": fund.project_id in project_ids},
                "funder": {"id": fund.funder_id, "name": fund.funder.short_name, "can_view": can_open_org},
                "institution": {"id": fund.institution_id, "name": fund.institution.short_name, "can_view": can_open_org},
                "ref": fund.ref, "start_date": fund.start_date, "end_date": fund.end_date, "is_active": fund.is_active}

    def rows(self, rows):
        user = self.request.user
        project_ids = set(Project.get_instances_for_user("view", user, Project.objects.filter(pk__in=[getattr(item, self.relation).project_id for item in rows])).values_list("pk", flat=True))
        can_open_org = user.has_perm("common.display_infos")
        contract_counts = Counter()
        if self.model is Fund_Item:
            fund_ids = {item.fund_id for item in rows if item.type.is_hr}
            if fund_ids:
                contract_counts.update(visible_contracts(user).filter(fund_id__in=fund_ids).values_list("fund_id", flat=True))
        employee_ids = set()
        if self.model is Budget:
            employee_ids = set(Employee.get_instances_for_user("view", user, Employee.objects.filter(pk__in=[item.employee_id for item in rows if item.employee_id])).values_list("pk", flat=True))
        result = []
        for item in rows:
            fund = getattr(item, self.relation)
            data = {"id": item.pk, "fund": self.relation_data(fund, project_ids, can_open_org)}
            if self.model is Fund_Item:
                data.update(item_data(item, user))
                data["contract_count"] = contract_counts[item.fund_id] if item.type.is_hr else None
            elif self.model is Budget:
                data["admin_url"] = get_admin_change_url(user, item)
                data.update({"cost_type": cost_type_data(item.cost_type) if item.cost_type else None,
                             "desc": item.desc or "", "emp_type": {"id": item.emp_type_id, "name": item.emp_type.name} if item.emp_type_id else None,
                             "employee": {"id": item.employee_id, "name": str(item.employee), "can_view": item.employee_id in employee_ids} if item.employee_id else None,
                             "contract_types": [{"id": value.pk, "name": value.name} for value in item.contract_type.all()],
                             "quotity": str(item.quotity) if item.quotity is not None else None,
                             "amount": money(item.amount), "expense": money(item.expense),
                             "available": money(item.available) if item.available is not None else None})
            else:
                data["admin_url"] = get_admin_change_url(user, item)
                data.update({"expense_id": item.expense_id or "", "desc": item.desc or "", "date": item.date,
                             "type": cost_type_data(item.type), "amount": money(item.amount), "status": item.status})
            result.append(data)
        return result


class FundItemList(FinancialList):
    model = Fund_Item
    filterset_class = FundItemFilter
    ordering_fields = ("fund__project__name", "fund__funder__short_name", "fund__institution__short_name", "fund__start_date", "fund__end_date", "fund__ref", "type__name", "amount", "expense", "_available")
    ordering = ("fund__project__name", "pk")


class BudgetList(FinancialList):
    model = Budget
    filterset_class = BudgetFilter
    ordering_fields = ("fund__project__name", "cost_type__name", "fund__funder__short_name", "fund__institution__short_name", "fund__ref", "amount", "expense", "_available", "emp_type__name", "employee__last_name")
    ordering = ("fund__project__name", "pk")


class ExpenseList(FinancialList):
    model = Expense
    relation = "fund_item"
    filterset_class = ExpenseFilter
    ordering_fields = ("expense_id", "desc", "type__name", "amount", "status", "date", "fund_item__project__name", "fund_item__ref")
    ordering = ("-date", "-pk")


class FinancialExport:
    """Share the list queryset while leaving export unpaginated."""

    content_negotiation_class = ListExportContentNegotiation
    resource_class = None
    filename = None

    def get(self, request, *args, **kwargs):
        return export_list_queryset(request, self.filter_queryset(self.get_queryset()).distinct(), self.resource_class, self.filename)


class FundItemExport(FinancialExport, FundItemList):
    resource_class = FundItemResource
    filename = "FundItems"


class BudgetExport(FinancialExport, BudgetList):
    resource_class = BudgetResource
    filename = "Budgets"


class ExpenseExport(FinancialExport, ExpenseList):
    resource_class = ExpenseResource
    filename = "Expenses"


class FinancialOptions(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response({"cost_types": list(Cost_Type.objects.order_by("name", "pk").values("id", "name")),
                         "contract_types": list(Contract_type.objects.order_by("name", "pk").values("id", "name")),
                         "employee_types": list(Employee_Type.objects.order_by("name", "pk").values("id", "name")),
                         "statuses": [{"value": code, "label": str(label)} for code, label in Expense.status_mod]})


class FinancialOrganizations(generics.GenericAPIView):
    """Search only organizations attached to funds visible in these tools."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        kind = request.query_params.get("kind")
        if kind not in ("institutions", "funders"):
            raise ValidationError({"kind": "Choose institutions or funders."})
        model = Institution if kind == "institutions" else Fund_Institution
        field = "institution_id" if kind == "institutions" else "funder_id"
        queryset = model.objects.filter(pk__in=visible_funds(request.user).values(field))
        if request.query_params.get("id"):
            identifier = request.query_params["id"]
            if not identifier.isdecimal() or int(identifier) < 1:
                raise ValidationError({"id": "A positive integer is required."})
            queryset = queryset.filter(pk=identifier)
        if request.query_params.get("search"):
            search = request.query_params["search"][:100]
            queryset = queryset.filter(Q(name__icontains=search) | Q(short_name__icontains=search))
        rows = list(queryset.order_by("short_name", "pk")[:11].values("id", "name", "short_name"))
        return Response({"results": rows[:10], "has_more": len(rows) > 10})


class FundItemContracts(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, item_id):
        item = get_object_or_404(visible_financial_items(Fund_Item, request.user).select_related("type"), pk=item_id)
        if not item.type.is_hr:
            return Response([])
        contracts = visible_contracts(request.user).filter(fund_id=item.fund_id).select_related("employee", "contract_type").order_by("employee__last_name", "pk")
        return Response([{"id": contract.pk, "employee": str(contract.employee), "type": contract.contract_type.name if contract.contract_type else None,
                          "status": contract.status, "start_date": contract.start_date, "end_date": contract.end_date,
                          "quotity": str(contract.quotity), "is_active": contract.is_active} for contract in contracts])
