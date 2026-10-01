"""Project-scoped Budget and Contribution resources for the React detail."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from expense.models import Contract_type
from labsmanager.admin_links_v1 import get_admin_change_url
from project.models import Project
from staff.models import Employee, Employee_Type

from .api_v1 import cost_type_data, money
from .models import Budget, Contribution, Cost_Type, Fund


def project_change(user, project):
    """Use the existing object rule for mutations in the Project context."""
    return user.has_perm("project.change_project", project)


def capabilities(user, project):
    allowed = project_change(user, project)
    return {"can_add": allowed, "can_change": allowed, "can_delete": allowed}


def relation(item):
    return {"id": item.pk, "name": str(item)} if item else None


def budget_data(item, user, project, kind):
    """Return model-owned financial values; Contribution has no Expense UI."""
    result = {
        "id": item.pk,
        "admin_url": get_admin_change_url(user, item),
        "fund": {"id": item.fund_id, "name": str(item.fund)},
        "cost_type": cost_type_data(item.cost_type) if item.cost_type else None,
        "desc": item.desc or "",
        "emp_type": relation(item.emp_type),
        "employee": relation(item.employee),
        "contract_types": [relation(value) for value in item.contract_type.all()],
        "quotity": str(item.quotity) if item.quotity is not None else None,
        "amount": money(item.amount),
        "capabilities": capabilities(user, project),
    }
    if kind == "budget":
        result.update({
            "expense": money(item.expense),
            "available": money(item.available) if item.available is not None else None,
            "consumption_ratio": str(item.get_consumption_ratio()) if item.get_consumption_ratio() != "-" else None,
        })
    else:
        result.update({"start_date": item.start_date, "end_date": item.end_date})
    return result


class BudgetContributionWriteSerializer(serializers.Serializer):
    fund_id = serializers.PrimaryKeyRelatedField(source="fund", queryset=Fund.objects.all(), required=False)
    cost_type_id = serializers.PrimaryKeyRelatedField(source="cost_type", queryset=Cost_Type.objects.all(), required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    emp_type_id = serializers.PrimaryKeyRelatedField(source="emp_type", queryset=Employee_Type.objects.all(), required=False, allow_null=True)
    employee_id = serializers.PrimaryKeyRelatedField(source="employee", queryset=Employee.objects.all(), required=False, allow_null=True)
    contract_type_ids = serializers.PrimaryKeyRelatedField(source="contract_types", queryset=Contract_type.objects.all(), many=True, required=False)
    quotity = serializers.DecimalField(max_digits=4, decimal_places=3, required=False, allow_null=True)
    desc = serializers.CharField(max_length=150, required=False, allow_blank=True, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            forbidden = set(data) - set(self.fields)
            if forbidden:
                raise serializers.ValidationError({key: "Unknown field." for key in sorted(forbidden)})
            if self.instance and ({"fund_id", "cost_type_id"} & set(data)):
                raise serializers.ValidationError({key: "This field cannot be changed." for key in sorted({"fund_id", "cost_type_id"} & set(data))})
            if self.context["kind"] == "budget" and ({"start_date", "end_date"} & set(data)):
                raise serializers.ValidationError({"dates": "Dates belong only to Contribution."})
        return super().to_internal_value(data)

    def validate(self, attrs):
        project = self.context["project"]
        fund = attrs.get("fund", self.instance.fund if self.instance else None)
        cost_type = attrs.get("cost_type", self.instance.cost_type if self.instance else None)
        if not fund:
            raise serializers.ValidationError({"fund_id": "Fund is required."})
        if not cost_type:
            raise serializers.ValidationError({"cost_type_id": "Cost type is required."})
        if fund.project_id != project.pk or not self.context["visible_funds"].filter(pk=fund.pk).exists():
            raise serializers.ValidationError({"fund_id": "Fund is not available in this project."})
        if "employee" in attrs and attrs["employee"] is not None:
            editable = Employee.get_instances_for_user("change", self.context["request"].user, Employee.objects.all())
            if not editable.filter(pk=attrs["employee"].pk).exists():
                raise serializers.ValidationError({"employee_id": "Employee is not editable."})
        if self.context["kind"] == "contribution":
            start = attrs.get("start_date", self.instance.start_date if self.instance else None)
            end = attrs.get("end_date", self.instance.end_date if self.instance else None)
            if start and end and end < start:
                raise serializers.ValidationError({"end_date": "End date precedes start date."})
        return attrs

    def save(self, **kwargs):
        values = dict(self.validated_data)
        contract_types = values.pop("contract_types", None)
        model = Budget if self.context["kind"] == "budget" else Contribution
        item = self.instance or model()
        for key, value in values.items():
            setattr(item, key, value)
        try:
            item.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(getattr(error, "message_dict", None) or error.messages) from error
        item.save()
        if contract_types is not None:
            item.contract_type.set(contract_types)
        return item


class ProjectBudgetBase(APIView):
    """Scope every resource to a visible Project and its visible Funds."""

    permission_classes = (permissions.IsAuthenticated,)
    model = None
    kind = None

    def project(self):
        if not hasattr(self, "_project"):
            visible = Project.get_instances_for_user("view", self.request.user, Project.objects.all())
            self._project = get_object_or_404(visible, pk=self.kwargs["pk"])
        return self._project

    def visible_funds(self):
        if not hasattr(self, "_funds"):
            self._funds = Fund.get_instances_for_user(
                "view", self.request.user, Fund.objects.filter(project=self.project())
            )
        return self._funds

    def queryset(self):
        return (self.model.objects.filter(fund__in=self.visible_funds())
                .select_related("fund__funder", "fund__institution", "cost_type", "emp_type", "employee")
                .prefetch_related("contract_type").order_by("pk"))

    def item(self):
        return get_object_or_404(self.queryset(), pk=self.kwargs["item_id"])

    def require_change(self):
        if not project_change(self.request.user, self.project()):
            raise PermissionDenied()

    def serializer(self, data, instance=None):
        return BudgetContributionWriteSerializer(
            instance, data=data, partial=instance is not None,
            context={"kind": self.kind, "project": self.project(),
                     "visible_funds": self.visible_funds(), "request": self.request},
        )


class ProjectBudgetCollectionV1View(ProjectBudgetBase):
    def get(self, request, *args, **kwargs):
        project = self.project()
        return Response({"capabilities": capabilities(request.user, project),
                         "items": [budget_data(item, request.user, project, self.kind) for item in self.queryset()]})

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.require_change()
        serializer = self.serializer(request.data)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        return Response(budget_data(item, request.user, self.project(), self.kind), status=201)


class ProjectBudgetDetailV1View(ProjectBudgetBase):
    def get(self, request, *args, **kwargs):
        return Response(budget_data(self.item(), request.user, self.project(), self.kind))

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        item = self.item()
        self.require_change()
        serializer = self.serializer(request.data, item)
        serializer.is_valid(raise_exception=True)
        return Response(budget_data(serializer.save(), request.user, self.project(), self.kind))

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        item = self.item()
        self.require_change()
        item.delete()
        return Response(status=204)


class ProjectBudgetOptionsV1View(ProjectBudgetBase):
    def get(self, request, *args, **kwargs):
        self.project()
        editable_employees = Employee.get_instances_for_user("change", request.user, Employee.objects.all())
        return Response({
            "funds": [{"id": item.pk, "name": str(item)} for item in self.visible_funds().select_related("funder", "institution").order_by("pk")],
            "cost_types": [cost_type_data(item) for item in Cost_Type.objects.order_by("short_name", "pk")],
            "employee_types": [{"id": item.pk, "name": str(item)} for item in Employee_Type.objects.order_by("name", "pk")],
            "contract_types": [{"id": item.pk, "name": str(item)} for item in Contract_type.objects.order_by("name", "pk")],
            "employees": [{"id": item.pk, "name": str(item)} for item in editable_employees.order_by("last_name", "pk")],
        })


class ProjectBudgetCollection(ProjectBudgetCollectionV1View):
    model = Budget
    kind = "budget"


class ProjectBudgetDetail(ProjectBudgetDetailV1View):
    model = Budget
    kind = "budget"


class ProjectBudgetOptions(ProjectBudgetOptionsV1View):
    model = Budget
    kind = "budget"


class ProjectContributionCollection(ProjectBudgetCollectionV1View):
    model = Contribution
    kind = "contribution"


class ProjectContributionDetail(ProjectBudgetDetailV1View):
    model = Contribution
    kind = "contribution"


class ProjectContributionOptions(ProjectBudgetOptionsV1View):
    model = Contribution
    kind = "contribution"
