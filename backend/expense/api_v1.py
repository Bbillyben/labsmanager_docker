"""Fund- and Contract-scoped individual Expense API."""

from datetime import date

from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from fund.api_v1 import cost_type_data, money
from labsmanager.admin_links_v1 import get_admin_change_url
from fund.models import Budget, Cost_Type, Fund
from project.models import Project
from settings.models import LMProjectSetting
from staff.models import Employee

from .models import Contract, Contract_expense, Expense


def subtype(expense):
    try:
        return expense.contract_expense
    except ObjectDoesNotExist:
        return None


def expense_data(expense, user):
    child = subtype(expense)
    contract = child.contract if child else None
    budget = expense.budget_item
    return {
        "id": expense.pk, "admin_url": get_admin_change_url(user, expense), "expense_id": expense.expense_id or "", "desc": expense.desc or "",
        "date": expense.date, "type": cost_type_data(expense.type), "amount": money(expense.amount),
        "status": expense.status,
        "contract": {"id": contract.pk, "name": str(contract.employee)} if contract else None,
        "budget": {"id": budget.pk, "name": str(budget)} if budget else None,
        "capabilities": expense_capabilities(user, expense),
    }


def can_add(user, fund, contract=None, budget=None):
    mode = LMProjectSetting.get_setting("EXPENSE_CALCULATION", project=fund.project)
    if contract:
        return user.has_perm("expense.add_contract_expense") or user.has_perm("expense.change_contract_expense", contract)
    if mode == "s" and budget is None:
        return False
    return user.has_perm("expense.add_expense", fund) or user.has_perm("expense.add_expense")


def expense_capabilities(user, expense):
    child = subtype(expense)
    change = user.has_perm("expense.change_contract_expense", child.contract) if child else user.has_perm("expense.change_expense", expense)
    delete_perm = "expense.delete_contract_expense" if child else "expense.delete_expense"
    return {"can_change": change, "can_delete": user.has_perm(delete_perm)}


def collection_capabilities(user, fund, contract=None):
    mode = LMProjectSetting.get_setting("EXPENSE_CALCULATION", project=fund.project)
    if contract:
        add = can_add(user, fund, contract)
    else:
        # In Simple mode the form may still create a Budget- or Contract-linked
        # expense; the POST rejects a general Expense without either relation.
        standard_add = user.has_perm("expense.add_expense", fund) or user.has_perm("expense.add_expense")
        contracts = Contract.objects.filter(fund=fund)
        contract_add = (contracts.exists() and user.has_perm("expense.add_contract_expense")) or any(
            user.has_perm("expense.change_contract_expense", item) for item in contracts
        )
        add = (standard_add and (mode != "s" or Budget.objects.filter(fund=fund).exists())) or contract_add
    return {
        "expense_mode": mode,
        "can_add": add,
        "can_sync_expenses": user.has_perm("fund.change_fund", fund) and mode in ("e", "h") if contract is None else False,
    }


def hr_types():
    return Cost_Type.objects.filter(is_hr=True).get_descendants(include_self=True)


class ExpenseWriteSerializer(serializers.Serializer):
    expense_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    desc = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    date = serializers.DateField(required=False)
    type_id = serializers.PrimaryKeyRelatedField(source="type", queryset=Cost_Type.objects.all(), required=False)
    status = serializers.ChoiceField(choices=Expense.status_mod, required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    contract_id = serializers.PrimaryKeyRelatedField(source="contract", queryset=Contract.objects.all(), required=False, allow_null=True)
    budget_id = serializers.PrimaryKeyRelatedField(source="budget_item", queryset=Budget.objects.all(), required=False, allow_null=True)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            extra = set(data) - set(self.fields)
            if extra:
                raise serializers.ValidationError({key: "Unknown field." for key in extra})
        return super().to_internal_value(data)

    def validate(self, attrs):
        expense = self.instance
        fund = self.context["fund"]
        old_child = subtype(expense) if expense else None
        contract = attrs.get("contract", old_child.contract if old_child else self.context.get("contract"))
        budget = attrs.get("budget_item", expense.budget_item if expense else None)
        context_budget = self.context.get("budget")
        if context_budget:
            if "budget_item" in attrs and attrs["budget_item"] != context_budget:
                raise serializers.ValidationError({"budget_id": "Budget cannot be changed in this context."})
            budget = context_budget
            attrs["budget_item"] = context_budget
        cost_type = attrs.get("type", expense.type if expense else None)
        if not expense and (not attrs.get("date") or not cost_type or "amount" not in attrs):
            raise serializers.ValidationError({"detail": "Date, cost type and amount are required."})
        if self.context.get("contract") and contract != self.context["contract"]:
            raise serializers.ValidationError({"contract_id": "Contract cannot be changed in this context."})
        if contract and contract.fund_id != fund.pk:
            raise serializers.ValidationError({"contract_id": "Contract must belong to the same fund."})
        if budget and budget.fund_id != fund.pk:
            raise serializers.ValidationError({"budget_id": "Budget must belong to the same fund."})
        if contract and cost_type and not hr_types().filter(pk=cost_type.pk).exists():
            raise serializers.ValidationError({"type_id": "A contract expense requires an HR cost type."})
        if budget and cost_type:
            budget_type = budget.cost_type
            if budget_type and not (budget_type == cost_type or budget_type.is_ancestor_of(cost_type) or budget_type.is_descendant_of(cost_type)):
                raise serializers.ValidationError({"budget_id": "Expense type must match the budget type or its hierarchy."})
        attrs["_contract"] = contract
        attrs["_old_child"] = old_child
        return attrs

    def save(self, **kwargs):
        values = dict(self.validated_data)
        contract = values.pop("_contract")
        old_child = values.pop("_old_child")
        values.pop("contract", None)
        expense = self.instance or Expense(fund_item=self.context["fund"])
        for key, value in values.items():
            setattr(expense, key, value)
        try:
            expense.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(getattr(error, "message_dict", None) or error.messages) from error
        expense.save()
        if old_child and contract is None:
            old_child.delete(keep_parents=True)
        elif old_child and contract and old_child.contract_id != contract.pk:
            old_child.contract = contract
            old_child.save(update_fields=["contract"])
        elif not old_child and contract:
            # Django's normal child save updates the existing parent row, then
            # inserts the child row with the same parent PK. Copy every parent
            # field so that update is lossless; never create a second Expense.
            child = Contract_expense(expense_ptr=expense, contract=contract)
            for field in Expense._meta.local_concrete_fields:
                if not field.primary_key:
                    setattr(child, field.attname, getattr(expense, field.attname))
            child.save()
        return Expense.objects.get(pk=expense.pk)


class ExpensePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ExpenseBase(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def context(self):
        if not hasattr(self, "_context"):
            if "hub_contract_id" in self.kwargs:
                from .contract_hub_api_v1 import visible_contracts
                contract = get_object_or_404(
                    visible_contracts(self.request.user).select_related("fund__project", "employee"),
                    pk=self.kwargs["hub_contract_id"],
                )
                self._context = (contract.fund, contract)
            elif "budget_id" in self.kwargs:
                visible_projects = Project.get_instances_for_user("view", self.request.user, Project.objects.all())
                project = get_object_or_404(visible_projects, pk=self.kwargs["pk"])
                visible_funds = Fund.get_instances_for_user("view", self.request.user, Fund.objects.filter(project=project))
                self._budget = get_object_or_404(Budget.objects.select_related("fund__project"),
                                                 pk=self.kwargs["budget_id"], fund__in=visible_funds)
                self._context = (self._budget.fund, None)
            elif "contract_id" in self.kwargs and "pk" in self.kwargs:
                from .contracts_api_v1 import ContractContextView
                contract_context = ContractContextView()
                contract_context.request = self.request
                contract_context.kwargs = {"project_id": self.kwargs["pk"], "contract_id": self.kwargs["contract_id"]}
                contract = contract_context.contract()
                self._context = (contract.fund, contract)
            elif "contract_id" in self.kwargs:
                visible = Employee.get_instances_for_user("view", self.request.user, Employee.objects.all())
                employee = get_object_or_404(visible, pk=self.kwargs["employee_id"])
                contract = get_object_or_404(Contract.objects.select_related("fund__project", "employee"), pk=self.kwargs["contract_id"], employee=employee)
                self._context = (contract.fund, contract)
            else:
                visible = Fund.get_instances_for_user("view", self.request.user, Fund.objects.all())
                fund = get_object_or_404(visible.select_related("project"), pk=self.kwargs["fund_id"])
                self._context = (fund, None)
        return self._context

    def queryset(self):
        fund, contract = self.context()
        qs = Expense.objects.filter(fund_item=fund).select_related("type", "budget_item", "contract_expense__contract__employee")
        if contract:
            qs = qs.filter(contract_expense__contract=contract)
        if "budget_id" in self.kwargs:
            qs = qs.filter(budget_item=self._budget)
        return qs

    def budget_context(self):
        self.context()
        return getattr(self, "_budget", None)

    def expense(self):
        return get_object_or_404(self.queryset(), pk=self.kwargs["expense_id"])

    def require(self, allowed):
        if not allowed:
            raise PermissionDenied()


class ExpenseCollectionV1View(ExpenseBase):
    def get(self, request, *args, **kwargs):
        fund, contract = self.context()
        qs = self.queryset()
        query = request.query_params.get("search", "").strip()
        if query:
            qs = qs.filter(Q(expense_id__icontains=query) | Q(desc__icontains=query))
        cost_type = request.query_params.get("type")
        if cost_type:
            try:
                qs = qs.filter(type_id=int(cost_type))
            except ValueError as error:
                raise serializers.ValidationError({"type": "Invalid cost type."}) from error
        for param, lookup in (("date_from", "date__gte"), ("date_to", "date__lte")):
            value = request.query_params.get(param)
            if value:
                try:
                    date.fromisoformat(value)
                except ValueError as error:
                    raise serializers.ValidationError({param: "Invalid date."}) from error
                qs = qs.filter(**{lookup: value})
        qs = qs.order_by("-date", "-pk")
        paginator = ExpensePagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        result = paginator.get_paginated_response([expense_data(item, request.user) for item in page])
        result.data["capabilities"] = collection_capabilities(request.user, fund, contract)
        if budget := self.budget_context():
            result.data["capabilities"]["can_add"] = can_add(request.user, fund, budget=budget)
            result.data["capabilities"]["can_sync_expenses"] = False
        return result

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        fund, context_contract = self.context()
        serializer = ExpenseWriteSerializer(data=request.data, context={"fund": fund, "contract": context_contract,
                                                                  "budget": self.budget_context()})
        serializer.is_valid(raise_exception=True)
        contract = serializer.validated_data["_contract"]
        budget = serializer.validated_data.get("budget_item")
        self.require(can_add(request.user, fund, contract, budget))
        item = serializer.save()
        if LMProjectSetting.get_setting("EXPENSE_CALCULATION", project=fund.project) in ("e", "h"):
            fund.calculate(force=True)
        return Response(expense_data(item, request.user), status=201)


class ExpenseDetailV1View(ExpenseBase):
    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        item = self.expense()
        fund, context_contract = self.context()
        self.require(expense_capabilities(request.user, item)["can_change"])
        serializer = ExpenseWriteSerializer(item, data=request.data, partial=True,
                                            context={"fund": fund, "contract": context_contract,
                                                     "budget": self.budget_context()})
        serializer.is_valid(raise_exception=True)
        old_child = serializer.validated_data["_old_child"]
        new_contract = serializer.validated_data["_contract"]
        if old_child and not new_contract:
            self.require(request.user.has_perm("expense.change_expense", item))
        elif not old_child and new_contract:
            self.require(can_add(request.user, fund, new_contract))
        elif old_child and new_contract and old_child.contract_id != new_contract.pk:
            self.require(can_add(request.user, fund, new_contract))
        saved = serializer.save()
        if LMProjectSetting.get_setting("EXPENSE_CALCULATION", project=fund.project) in ("e", "h"):
            fund.calculate(force=True)
        return Response(expense_data(saved, request.user))

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        item = self.expense()
        self.require(expense_capabilities(request.user, item)["can_delete"])
        fund = item.fund_item
        budget = item.budget_item
        item.delete()
        if budget:
            budget.calculate_expense()
        if LMProjectSetting.get_setting("EXPENSE_CALCULATION", project=fund.project) in ("e", "h"):
            fund.calculate_expense(force=True)
            fund.calculate(force=True)
        return Response(status=204)


class ExpenseOptionsV1View(ExpenseBase):
    def get(self, request, *args, **kwargs):
        fund, context_contract = self.context()
        contracts = Contract.objects.filter(fund=fund).select_related("employee").order_by("employee__last_name", "pk")
        return Response({
            "cost_types": [cost_type_data(item) for item in Cost_Type.objects.order_by("short_name", "pk")],
            "hr_type_ids": list(hr_types().values_list("pk", flat=True)),
            "contracts": [{"id": item.pk, "name": str(item.employee)} for item in contracts] if context_contract is None else [{"id": context_contract.pk, "name": str(context_contract.employee)}],
            "budgets": [{"id": item.pk, "name": str(item)} for item in Budget.objects.filter(fund=fund, **({"pk": self._budget.pk} if self.budget_context() else {})).select_related("cost_type").order_by("pk")],
        })


class ExpenseSyncV1View(ExpenseBase):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        fund, contract = self.context()
        self.require(collection_capabilities(request.user, fund, contract)["can_sync_expenses"])
        fund.calculate_expense(force=True)
        # The forced zero update bypasses Expense_point post_save signals for
        # types with no remaining Expense; recalculate the cached totals too.
        fund.calculate(force=True)
        return Response({"detail": "Expenses synchronized."})
