"""Equipment-scoped Expense links; the accounting row remains in Expense."""

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from expense.api_v1 import (ExpenseWriteSerializer, can_add, collection_capabilities, expense_capabilities,
                            expense_data, hr_types)
from expense.models import Contract, Expense
from fund.api_v1 import cost_type_data, money
from fund.financial_tools_api_v1 import visible_funds
from fund.models import Budget, Cost_Type
from settings.models import LMProjectSetting

from .api_v1 import visible_equipment
from .expense_access import assignment_capabilities, create_equipment_link, require_assignment_capability
from .models import EquipmentExpenseLink


def link_data(link, user):
    """Serialize a linked row with separate financial and link capabilities."""
    expense = link.expense
    data = expense_data(expense, user)
    assignment = assignment_capabilities(user, expense)
    data.update({
        "nature": link.nature,
        "fund": {"id": expense.fund_item_id, "name": str(expense.fund_item)},
        "link_capabilities": {
            "can_change": assignment["can_change"],
            "can_unlink": assignment["can_unlink"],
        },
    })
    data["capabilities"]["can_delete"] = (data["capabilities"]["can_delete"] and
                                             data["link_capabilities"]["can_unlink"])
    return data


class EquipmentExpenseBase(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def equipment(self):
        if not hasattr(self, "_equipment"):
            self._equipment = get_object_or_404(visible_equipment(self.request.user), pk=self.kwargs["pk"])
        return self._equipment

    def require(self, permission):
        if not self.request.user.has_perm(f"equipment.{permission}_equipmentexpenselink"):
            raise PermissionDenied()

    def visible_funds(self):
        return visible_funds(self.request.user)

    def queryset(self):
        self.require("view")
        return (EquipmentExpenseLink.objects.filter(equipment=self.equipment(), expense__fund_item__in=self.visible_funds())
                .select_related("expense__type", "expense__budget_item", "expense__fund_item",
                                "expense__contract_expense__contract__employee"))

    def link(self):
        return get_object_or_404(self.queryset(), expense_id=self.kwargs["expense_id"])

    def fund(self, fund_id):
        if not fund_id:
            raise serializers.ValidationError({"fund_id": "Choose a Fund."})
        return get_object_or_404(self.visible_funds(), pk=fund_id)


class EquipmentExpenses(EquipmentExpenseBase):
    """List, create, and attach Expenses from many visible Funds."""

    def get(self, request, *args, **kwargs):
        qs = self.queryset()
        total = qs.aggregate(total=Sum("expense__amount"))["total"] or Decimal("0.00")
        query = request.query_params.get("search", "").strip()
        if query:
            qs = qs.filter(Q(expense__expense_id__icontains=query) | Q(expense__desc__icontains=query))
        cost_type = request.query_params.get("type")
        if cost_type:
            try:
                qs = qs.filter(expense__type_id=int(cost_type))
            except ValueError as error:
                raise serializers.ValidationError({"type": "Invalid cost type."}) from error
        for param, lookup in (("date_from", "expense__date__gte"), ("date_to", "expense__date__lte")):
            value = request.query_params.get(param)
            if value:
                try:
                    date.fromisoformat(value)
                except ValueError as error:
                    raise serializers.ValidationError({param: "Invalid date."}) from error
                qs = qs.filter(**{lookup: value})
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs.order_by("-expense__date", "-pk"), request, view=self)
        response = paginator.get_paginated_response([link_data(link, request.user) for link in page])
        response.data["total_visible"] = money(total)
        response.data["capabilities"] = {
            "expense_mode": "e", "can_sync_expenses": False,
            "can_add": request.user.has_perm("equipment.add_equipmentexpenselink") and
                       request.user.has_perm("equipment.view_equipmentexpenselink") and
                       any(collection_capabilities(request.user, fund)["can_add"] for fund in self.visible_funds().select_related("project")),
            "can_link": request.user.has_perm("equipment.add_equipmentexpenselink") and
                        request.user.has_perm("equipment.view_equipmentexpenselink"),
        }
        return response

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        equipment = self.equipment()
        self.require("view")
        self.require("add")
        nature = request.data.get("nature", EquipmentExpenseLink.Nature.OTHER)
        if nature not in EquipmentExpenseLink.Nature.values:
            raise serializers.ValidationError({"nature": "Invalid nature."})
        existing_id = request.data.get("existing_expense_id")
        if existing_id is not None:
            if set(request.data) - {"existing_expense_id", "nature"}:
                raise serializers.ValidationError({"detail": "Unexpected association fields."})
            expense = get_object_or_404(Expense.objects.select_for_update().filter(fund_item__in=self.visible_funds()), pk=existing_id)
            require_assignment_capability(request.user, expense, "can_link")
        else:
            fund = self.fund(request.data.get("fund_id"))
            payload = {key: value for key, value in request.data.items() if key not in ("fund_id", "nature")}
            serializer = ExpenseWriteSerializer(data=payload, context={"fund": fund})
            serializer.is_valid(raise_exception=True)
            if not can_add(request.user, fund, serializer.validated_data["_contract"], serializer.validated_data.get("budget_item")):
                raise PermissionDenied()
            expense = serializer.save()
            if LMProjectSetting.get_setting("EXPENSE_CALCULATION", project=fund.project) in ("e", "h"):
                fund.calculate(force=True)
        link = create_equipment_link(equipment=equipment, expense=expense, nature=nature)
        return Response(link_data(link, request.user), status=status.HTTP_201_CREATED)


class EquipmentExpenseOptions(EquipmentExpenseBase):
    def get(self, request, *args, **kwargs):
        self.equipment()
        self.require("view")
        funds = list(self.visible_funds().select_related("project"))
        fund_ids = [fund.pk for fund in funds]
        contracts = Contract.get_instances_for_user("view", request.user, Contract.objects.filter(fund_id__in=fund_ids))
        return Response({
            "cost_types": [cost_type_data(item) for item in Cost_Type.objects.order_by("short_name", "pk")],
            "hr_type_ids": list(hr_types().values_list("pk", flat=True)),
            "funds": [{"id": fund.pk, "name": str(fund),
                       "expense_mode": LMProjectSetting.get_setting("EXPENSE_CALCULATION", project=fund.project)} for fund in funds],
            "contracts": [{"id": item.pk, "name": str(item.employee), "fund_id": item.fund_id}
                          for item in contracts.select_related("employee")],
            "budgets": [{"id": item.pk, "name": str(item), "fund_id": item.fund_id}
                        for item in Budget.objects.filter(fund_id__in=fund_ids).select_related("cost_type")],
        })


class EquipmentExpenseCandidates(EquipmentExpenseBase):
    def get(self, request, *args, **kwargs):
        self.equipment()
        self.require("view")
        self.require("add")
        query = request.query_params.get("search", "").strip()
        if len(query) < 2:
            return Response({"results": []})
        qs = (Expense.objects.filter(fund_item__in=self.visible_funds(), equipment_link__isnull=True)
              .filter(Q(expense_id__icontains=query) | Q(desc__icontains=query))
              .select_related("type", "budget_item", "fund_item", "contract_expense__contract__employee")
              .order_by("-date", "-pk")[:30])
        return Response({"results": [{**expense_data(item, request.user),
                                      "fund": {"id": item.fund_item_id, "name": str(item.fund_item)}}
                                     for item in qs if expense_capabilities(request.user, item)["can_change"]]})


class EquipmentExpenseDetail(EquipmentExpenseBase):
    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        link = self.link()
        if set(request.data) == {"nature"}:
            require_assignment_capability(request.user, link.expense, "can_change")
            if request.data["nature"] not in EquipmentExpenseLink.Nature.values:
                raise serializers.ValidationError({"nature": "Invalid nature."})
            link.nature = request.data["nature"]
            link.save(update_fields=["nature"])
            return Response(link_data(link, request.user))
        if "nature" in request.data or "fund_id" in request.data:
            raise serializers.ValidationError({"detail": "Financial and link changes are separate."})
        expense = link.expense
        if not expense_capabilities(request.user, expense)["can_change"]:
            raise PermissionDenied()
        serializer = ExpenseWriteSerializer(expense, data=request.data, partial=True, context={"fund": expense.fund_item})
        serializer.is_valid(raise_exception=True)
        old_child, new_contract = serializer.validated_data["_old_child"], serializer.validated_data["_contract"]
        if old_child and not new_contract and not request.user.has_perm("expense.change_expense", expense):
            raise PermissionDenied()
        if new_contract and (not old_child or old_child.contract_id != new_contract.pk) and not can_add(request.user, expense.fund_item, new_contract):
            raise PermissionDenied()
        saved = serializer.save()
        fund = saved.fund_item
        if LMProjectSetting.get_setting("EXPENSE_CALCULATION", project=fund.project) in ("e", "h"):
            fund.calculate(force=True)
        link.expense = saved
        return Response(link_data(link, request.user))

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        link = self.link()
        require_assignment_capability(request.user, link.expense, "can_unlink")
        link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EquipmentExpenseDelete(EquipmentExpenseBase):
    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        link = self.link()
        self.require("delete")
        expense = link.expense
        if not expense_capabilities(request.user, expense)["can_delete"]:
            raise PermissionDenied()
        fund, budget = expense.fund_item, expense.budget_item
        expense.delete()
        if budget:
            budget.calculate_expense()
        if LMProjectSetting.get_setting("EXPENSE_CALCULATION", project=fund.project) in ("e", "h"):
            fund.calculate_expense(force=True)
            fund.calculate(force=True)
        return Response(status=status.HTTP_204_NO_CONTENT)
