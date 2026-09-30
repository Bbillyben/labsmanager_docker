"""Contextual Contract API for Project and Employee detail pages."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Case, DateField, F, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from fund.models import Fund
from project.models import Participant, Project
from staff.models import Employee
from staff.rules import can_change_employee
from staff.serializers_v1 import EmployeeContractDetailV1Serializer, EmployeeContractV1Serializer
from infos.api_v1 import note_admin, parent_change, visible_note_counts

from .models import Contract, Contract_type


def has_model_or_object_perm(user, permission, item):
    """Keep Django's global permission alongside the existing Rules object rule."""
    return user.has_perm(permission) or user.has_perm(permission, item)


def contract_capabilities(user, contract=None, *, project=None, employee=None):
    """Compute capabilities in the endpoint context, never by merging contexts."""
    if project is not None:
        allowed = has_model_or_object_perm(user, "project.change_project", project)
        return {"can_add": allowed, "can_change": allowed, "can_delete": allowed}
    return {
        "can_add": bool(employee and user.has_perm("expense.add_contract") and
                        has_model_or_object_perm(user, "staff.change_employee", employee)),
        "can_change": bool(contract and has_model_or_object_perm(user, "expense.change_contract", contract)),
        "can_delete": bool(contract and has_model_or_object_perm(user, "expense.delete_contract", contract)),
    }


def employee_end_date_sync_offer(user, contract, employee=None):
    """Offer the saved Contract end date only to an Employee editor."""
    employee = employee or contract.employee
    proposed = contract.end_date
    if not proposed or employee.exit_date == proposed or not can_change_employee(user, employee):
        return None
    if Contract.objects.filter(employee=employee).exclude(pk=contract.pk).filter(end_date__gt=proposed).exists():
        return None
    return {
        "employee_id": employee.pk,
        "current_end_date": employee.exit_date.isoformat() if employee.exit_date else None,
        "proposed_end_date": proposed.isoformat(),
        "can_update": True,
    }


class ContractWriteSerializer(serializers.Serializer):
    employee_id = serializers.PrimaryKeyRelatedField(source="employee", queryset=Employee.objects.all(), required=False)
    fund_id = serializers.PrimaryKeyRelatedField(source="fund", queryset=Fund.objects.all(), required=False)
    contract_type_id = serializers.PrimaryKeyRelatedField(source="contract_type", queryset=Contract_type.objects.all(), required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    quotity = serializers.DecimalField(max_digits=4, decimal_places=3, required=False)
    status = serializers.ChoiceField(choices=Contract.type_cont, required=False)
    is_active = serializers.BooleanField(required=False)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            extra = set(data) - set(self.fields)
            if extra:
                raise serializers.ValidationError({key: "Unknown field." for key in sorted(extra)})
            if self.instance and ({"employee_id", "fund_id"} & set(data)):
                raise serializers.ValidationError({key: "This relation cannot be changed." for key in sorted({"employee_id", "fund_id"} & set(data))})
        return super().to_internal_value(data)

    def validate(self, attrs):
        employee = attrs.get("employee", self.instance.employee if self.instance else self.context.get("employee"))
        fund = attrs.get("fund", self.instance.fund if self.instance else None)
        if not employee:
            raise serializers.ValidationError({"employee_id": "Employee is required."})
        if not fund:
            raise serializers.ValidationError({"fund_id": "Fund is required."})
        project = self.context.get("project")
        if project and fund.project_id != project.pk:
            raise serializers.ValidationError({"fund_id": "Fund must belong to this project."})
        if self.context.get("employee") and employee.pk != self.context["employee"].pk:
            raise serializers.ValidationError({"employee_id": "Employee cannot be changed in this context."})
        if not Participant.objects.filter(project_id=fund.project_id, employee=employee).exists():
            raise serializers.ValidationError({"employee_id": "Employee must participate in the fund's project."})
        if not self.instance and not self.context["funds"].filter(pk=fund.pk).exists():
            raise serializers.ValidationError({"fund_id": "Fund is not available in this context."})
        start = attrs.get("start_date", self.instance.start_date if self.instance else None)
        end = attrs.get("end_date", self.instance.end_date if self.instance else None)
        if start and end and end < start:
            raise serializers.ValidationError({"end_date": "End date precedes start date."})
        status = attrs.get("status", self.instance.status if self.instance else "effe")
        contract_type = attrs.get("contract_type", self.instance.contract_type if self.instance else None)
        if status == "effe" and contract_type is None:
            raise serializers.ValidationError({"contract_type_id": "An effective contract requires a type."})
        active = attrs.get("is_active", self.instance.is_active if self.instance else True)
        if not active and end is None:
            raise serializers.ValidationError({"end_date": "An inactive contract requires an end date."})
        attrs["employee"] = employee
        attrs["fund"] = fund
        return attrs

    def save(self, **kwargs):
        contract = self.instance or Contract()
        for name, value in self.validated_data.items():
            setattr(contract, name, value)
        try:
            contract.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(getattr(error, "message_dict", None) or error.messages) from error
        contract.save()
        return contract


class ContractContextView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def context(self):
        if hasattr(self, "_contract_context"):
            return self._contract_context
        user = self.request.user
        if "project_id" in self.kwargs:
            visible = Project.get_instances_for_user("view", user, Project.objects.all())
            project = get_object_or_404(visible, pk=self.kwargs["project_id"])
            funds = Fund.get_instances_for_user("view", user, Fund.objects.filter(project=project))
            employees = Employee.objects.filter(pk__in=Participant.objects.filter(project=project).values("employee_id"))
            self._contract_context = (project, None, funds, employees)
        else:
            visible = Employee.get_instances_for_user("view", user, Employee.objects.all())
            employee = get_object_or_404(visible, pk=self.kwargs.get("employee_id", self.kwargs.get("pk")))
            funds = Fund.get_instances_for_user("change", user, Fund.objects.filter(
                project_id__in=Participant.objects.filter(employee=employee).values("project_id")
            ))
            self._contract_context = (None, employee, funds, Employee.objects.filter(pk=employee.pk))
        return self._contract_context

    def queryset(self):
        project, employee, funds, employees = self.context()
        qs = Contract.objects.select_related("employee", "contract_type", "fund__project", "fund__funder", "fund__institution")
        if project:
            return qs.filter(fund__in=funds, employee__in=employees)
        return qs.filter(employee=employee)

    def contract(self):
        return get_object_or_404(self.queryset(), pk=self.kwargs.get("contract_id", self.kwargs.get("contract_pk")))

    def capabilities(self, contract=None):
        project, employee, _, _ = self.context()
        return contract_capabilities(self.request.user, contract, project=project, employee=employee)

    def serialized(self, contract, *, detailed=False, note_counts=None):
        user = self.request.user
        project, employee, _, _ = self.context()
        if not hasattr(self, "_visible_project_ids"):
            self._visible_project_ids = set(Project.get_instances_for_user("view", user, Project.objects.all()).values_list("pk", flat=True))
            self._visible_employee_ids = set(Employee.get_instances_for_user("view", user, Employee.objects.all()).values_list("pk", flat=True))
        context = {"request": self.request, "today": timezone.localdate(),
                   "visible_project_ids": self._visible_project_ids, "visible_employee_ids": self._visible_employee_ids,
                   "can_view_organizations": user.has_perm("common.display_infos")}
        if detailed and employee:
            from .models import Contract_expense
            context["contract_expenses"] = list(Contract_expense.objects.filter(contract=contract).select_related("type").order_by("-date", "-pk"))
        serializer = EmployeeContractDetailV1Serializer if detailed and employee else EmployeeContractV1Serializer
        data = serializer(contract, context=context).data
        data["capabilities"] = contract_capabilities(user, contract, project=project, employee=employee)
        if note_counts is None:
            note_counts = visible_note_counts(user, Contract, [contract.pk])
        data["notes"] = {
            "visible_count": note_counts.get(contract.pk, 0),
            "can_add": bool(note_admin(user) or parent_change(user, contract)),
        }
        if detailed:
            data["total_amount"] = str(contract.total_amount)
            data["remain_amount"] = str(contract.remain_amount)
            data["man_month"] = str(contract.man_month)
        return data

    def write_context(self):
        project, employee, funds, _ = self.context()
        return {"project": project, "employee": employee, "funds": funds}


class ContractCollectionV1View(ContractContextView):
    """List Contracts inside the selected Project or Employee authority."""

    def get(self, request, *args, **kwargs):
        project, _, _, _ = self.context()
        queryset = self.queryset()
        if project:
            queryset = queryset.order_by("start_date", "pk")
        else:
            today = timezone.localdate()
            future = Q(start_date__gt=today)
            past = ~future & Q(end_date__lt=today)
            queryset = queryset.annotate(
                _v1_temporal_order=Case(When(future, then=Value(1)), When(past, then=Value(2)), default=Value(0), output_field=IntegerField()),
                _v1_current_end=Case(When(future | past, then=Value(None)), default=F("end_date"), output_field=DateField()),
                _v1_future_start=Case(When(future, then=F("start_date")), default=Value(None), output_field=DateField()),
                _v1_past_end=Case(When(past, then=F("end_date")), default=Value(None), output_field=DateField()),
            ).order_by("_v1_temporal_order", F("_v1_current_end").asc(nulls_last=True), F("_v1_future_start").asc(nulls_last=True), F("_v1_past_end").desc(nulls_last=True), "pk")
        contracts = list(queryset)
        note_counts = visible_note_counts(request.user, Contract, (item.pk for item in contracts))
        items = [self.serialized(item, note_counts=note_counts) for item in contracts]
        if project:
            return Response({"items": items, "capabilities": self.capabilities()})
        return Response(items)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        if not self.capabilities()["can_add"]:
            raise PermissionDenied()
        serializer = ContractWriteSerializer(data=request.data, context=self.write_context())
        serializer.is_valid(raise_exception=True)
        contract = serializer.save()
        data = self.serialized(contract)
        data["employee_end_date_sync"] = employee_end_date_sync_offer(request.user, contract)
        return Response(data, status=201)


class ContractDetailV1View(ContractContextView):
    """Read or mutate one Contract in the caller's context."""

    def get(self, request, *args, **kwargs):
        return Response(self.serialized(self.contract(), detailed=True))

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        contract = self.contract()
        if not self.capabilities(contract)["can_change"]:
            raise PermissionDenied()
        serializer = ContractWriteSerializer(contract, data=request.data, partial=True, context=self.write_context())
        serializer.is_valid(raise_exception=True)
        contract = serializer.save()
        data = self.serialized(contract)
        data["employee_end_date_sync"] = employee_end_date_sync_offer(request.user, contract)
        return Response(data)

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        contract = self.contract()
        if not self.capabilities(contract)["can_delete"]:
            raise PermissionDenied()
        contract.delete()
        return Response(status=204)


class ContractOptionsV1View(ContractContextView):
    """Limit writable relation choices to the current context."""

    def get(self, request, *args, **kwargs):
        project, employee, funds, employees = self.context()
        if project:
            selectable_funds = funds
        else:
            selectable_funds = funds if self.capabilities()["can_add"] else Fund.objects.none()
        return Response({
            "employees": [{"id": item.pk, "name": str(item)} for item in employees.order_by("last_name", "first_name", "pk")],
            "funds": [{"id": item.pk, "name": str(item), "project_id": item.project_id} for item in selectable_funds.select_related("project", "funder", "institution").order_by("project__name", "pk")],
            "contract_types": [{"id": item.pk, "name": item.name} for item in Contract_type.objects.order_by("name", "pk")],
        })


class EmployeeContractCapabilitiesV1View(ContractContextView):
    def get(self, request, *args, **kwargs):
        return Response(self.capabilities())


class ContractEmployeeEndDateSyncV1View(ContractContextView):
    """Apply an explicit, freshly revalidated Employee date decision."""

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        contract = self.contract()
        employee = Employee.objects.select_for_update().get(pk=contract.employee_id)
        if not can_change_employee(request.user, employee):
            raise PermissionDenied()
        offer = employee_end_date_sync_offer(request.user, contract, employee)
        if offer is None:
            raise ValidationError({"detail": "Employee end date synchronization is no longer available."})
        employee.exit_date = contract.end_date
        employee.save(update_fields=["exit_date"])
        return Response({"employee_id": employee.pk, "end_date": employee.exit_date.isoformat()})
