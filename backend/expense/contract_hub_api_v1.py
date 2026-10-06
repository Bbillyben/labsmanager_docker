"""Visible, filtered Contract collection for the cross-project Contract Hub."""

from decimal import Decimal

from django.db.models import DecimalField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django_filters import rest_framework as django_filters
from rest_framework import filters, generics, permissions, serializers
from rest_framework.response import Response

from fund.models import Fund
from infos.api_v1 import note_admin, visible_note_counts
from labsmanager.admin_links_v1 import AdminUrlSerializerMixin
from labsmanager.list_export_v1 import ListExportContentNegotiation, export_list_queryset
from labsmanager.pagination import LabPagination
from project.models import Project
from staff.models import Employee
from staff.serializers_v1 import EmployeeContractV1Serializer

from .contracts_api_v1 import (
    ContractContextView, ContractDetailV1View, ContractEmployeeEndDateSyncV1View,
    has_model_or_object_perm,
)
from .models import Contract, Contract_expense, Contract_type
from .resources import ContractResource


def visible_contracts(user):
    """Use the model's existing Contract visibility for every Hub endpoint."""
    return Contract.get_instances_for_user("view", user, Contract.objects.all())


def contract_hub_queryset(user):
    totals = (Contract_expense.objects.filter(contract_id=OuterRef("pk"))
              .values("contract_id").annotate(total=Sum("amount")).values("total")[:1])
    money = DecimalField(max_digits=14, decimal_places=2)
    return (visible_contracts(user)
            .select_related("employee", "contract_type", "fund__project", "fund__funder", "fund__institution")
            .annotate(hub_total_amount=Coalesce(Subquery(totals, output_field=money), Value(Decimal("0.00"), output_field=money))))


def contract_hub_serializer_context(request, note_counts):
    user = request.user
    return {
        "request": request,
        "today": timezone.localdate(),
        "visible_employee_ids": set(Employee.get_instances_for_user("view", user, Employee.objects.all()).values_list("pk", flat=True)),
        "visible_project_ids": set(Project.get_instances_for_user("view", user, Project.objects.all()).values_list("pk", flat=True)),
        "can_view_organizations": user.has_perm("common.display_infos"),
        "note_counts": note_counts,
    }


class ContractHubFilter(django_filters.FilterSet):
    active = django_filters.BooleanFilter(field_name="is_active")
    ongoing = django_filters.BooleanFilter(method="by_ongoing")
    employee = django_filters.NumberFilter(field_name="employee_id")
    type = django_filters.NumberFilter(field_name="contract_type_id")
    cont_status = django_filters.ChoiceFilter(field_name="status", choices=Contract.type_cont)
    project = django_filters.NumberFilter(field_name="fund__project_id")
    funder = django_filters.NumberFilter(field_name="fund__funder_id")
    institution = django_filters.NumberFilter(field_name="fund__institution_id")
    stale = django_filters.BooleanFilter(method="by_stale")

    class Meta:
        model = Contract
        fields = ()

    def by_ongoing(self, queryset, name, value):
        today = timezone.localdate()
        condition = Q(start_date__lte=today, end_date__gte=today)
        return queryset.filter(condition) if value else queryset.exclude(condition)

    def by_stale(self, queryset, name, value):
        condition = Contract.staleFilter()
        return queryset.filter(condition) if value else queryset.exclude(condition)


class ContractHubListSerializer(AdminUrlSerializerMixin, EmployeeContractV1Serializer):
    is_active = serializers.BooleanField(read_only=True)
    total_amount = serializers.DecimalField(source="hub_total_amount", max_digits=14, decimal_places=2, read_only=True)
    capabilities = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()

    class Meta(EmployeeContractV1Serializer.Meta):
        fields = EmployeeContractV1Serializer.Meta.fields + ("is_active", "total_amount", "capabilities", "admin_url", "notes")

    def can_change(self, contract):
        cache = self.context.setdefault("contract_change_capabilities", {})
        if contract.pk not in cache:
            cache[contract.pk] = has_model_or_object_perm(
                self.context["request"].user, "expense.change_contract", contract
            )
        return cache[contract.pk]

    def get_capabilities(self, contract):
        return {"can_change": self.can_change(contract)}

    def get_notes(self, contract):
        user = self.context["request"].user
        return {
            "visible_count": self.context["note_counts"].get(contract.pk, 0),
            "can_add": bool(note_admin(user) or self.can_change(contract)),
        }


class ContractHubListV1View(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ContractHubListSerializer
    pagination_class = LabPagination
    filter_backends = (django_filters.DjangoFilterBackend, filters.OrderingFilter)
    filterset_class = ContractHubFilter
    ordering_fields = ("employee__last_name", "contract_type__name", "status", "start_date", "end_date", "fund__project__name", "hub_total_amount")
    ordering = ("employee__last_name", "employee__first_name", "pk")

    def paginate_queryset(self, queryset):
        page = super().paginate_queryset(queryset)
        self.note_counts = visible_note_counts(self.request.user, Contract, (item.pk for item in page)) if page is not None else {}
        return page

    def get_queryset(self):
        return contract_hub_queryset(self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(contract_hub_serializer_context(self.request, self.note_counts))
        return context


class ContractHubExportV1View(ContractHubListV1View):
    http_method_names = ("get", "head", "options")
    content_negotiation_class = ListExportContentNegotiation

    def get(self, request, *args, **kwargs):
        return export_list_queryset(request, self.filter_queryset(self.get_queryset()), ContractResource, "Contract")


class ContractHubFilterOptionsV1View(generics.GenericAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        contracts = visible_contracts(request.user)
        return Response({
            "contract_types": list(Contract_type.objects.filter(contract__in=contracts).distinct().order_by("name", "pk").values("id", "name")),
            "statuses": [{"value": code, "label": str(label)} for code, label in Contract.type_cont],
            "funders": [{"id": pk, "short_name": name} for pk, name in contracts.order_by(
                "fund__funder__short_name").values_list("fund__funder_id", "fund__funder__short_name").distinct()],
            "institutions": [{"id": pk, "short_name": name} for pk, name in contracts.order_by(
                "fund__institution__short_name").values_list("fund__institution_id", "fund__institution__short_name").distinct()],
        })


class ContractHubContextView(ContractContextView):
    """Resolve a Contract without inheriting a Project or Employee edit authority."""

    def context(self):
        return None, None, Fund.objects.none(), Employee.objects.none()

    def queryset(self):
        return visible_contracts(self.request.user).select_related(
            "employee", "contract_type", "fund__project", "fund__funder", "fund__institution"
        )

    def capabilities(self, contract=None):
        return {"can_add": False, "can_change": bool(contract and has_model_or_object_perm(
            self.request.user, "expense.change_contract", contract)), "can_delete": False}

    def serialized(self, contract, *, detailed=False, note_counts=None):
        data = super().serialized(contract, detailed=detailed, note_counts=note_counts)
        data["capabilities"] = self.capabilities(contract)
        return data


class ContractHubDetailV1View(ContractHubContextView, ContractDetailV1View):
    http_method_names = ("get", "patch", "head", "options")


class ContractHubOptionsV1View(ContractHubContextView):
    def get(self, request, *args, **kwargs):
        contract = self.contract()
        return Response({
            "employees": [{"id": contract.employee_id, "name": str(contract.employee)}],
            "funds": [{"id": contract.fund_id, "name": str(contract.fund), "project_id": contract.fund.project_id}],
            "contract_types": list(Contract_type.objects.order_by("name", "pk").values("id", "name")),
        })


class ContractHubEndDateSyncV1View(ContractHubContextView, ContractEmployeeEndDateSyncV1View):
    http_method_names = ("post", "options")
