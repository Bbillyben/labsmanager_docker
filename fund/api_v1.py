"""Project-scoped funding API. Persisted financial totals remain model-owned."""

from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from expense.models import Expense, Expense_point
from project.api_v1 import project_capabilities
from project.models import Institution, Project
from settings.models import LMProjectSetting

from .models import Cost_Type, Fund, Fund_Institution, Fund_Item


ZERO = Decimal("0.00")


def validate_model(instance):
    try:
        instance.full_clean()
    except DjangoValidationError as error:
        raise serializers.ValidationError(getattr(error, "message_dict", None) or error.messages) from error


def amount(value):
    return value if value is not None else ZERO


def money(value):
    return str(amount(value).quantize(Decimal("0.01")))


def fund_capabilities(user, project, fund=None, change_project=None):
    if change_project is None:
        change_project = project_capabilities(user, project)["can_change"]
    change_fund = bool(fund and not change_project and user.has_perm("fund.change_fund", fund))
    return {
        "can_add": change_project or user.has_perm("fund.add_fund"),
        "can_change": change_project or change_fund or user.has_perm("fund.change_fund"),
        "can_delete": user.has_perm("fund.delete_fund"),
    }


def fund_item_capabilities(user, fund):
    change = user.has_perm("fund.change_fund", fund) or user.has_perm("fund.change_funditem")
    return {"can_add": change or user.has_perm("fund.add_fund_item"),
            "can_change": change, "can_delete": user.has_perm("fund.delete_fund_item")}


def expense_point_capabilities(user, fund):
    mode = LMProjectSetting.get_setting("EXPENSE_CALCULATION", project=fund.project)
    manual = mode in ("s", "h")
    return {"expense_mode": mode,
            "can_add": manual and (user.has_perm("expense.add_expense_point", fund) or user.has_perm("expense.add_expense_point")),
            "can_change": manual and (user.has_perm("expense.change_expense_point", fund) or user.has_perm("expense.change_expense_point")),
            "can_delete": manual and user.has_perm("expense.delete_expense_point")}


def cost_type_data(item):
    return {"id": item.pk, "short_name": item.short_name, "name": item.name}


def fund_data(fund, user, change_project=None):
    return {"id": fund.pk, "funder": {"id": fund.funder_id, "short_name": fund.funder.short_name, "name": fund.funder.name},
            "institution": {"id": fund.institution_id, "short_name": fund.institution.short_name, "name": fund.institution.name},
            "ref": fund.ref, "start_date": fund.start_date, "end_date": fund.end_date,
            "amount": money(fund.amount), "expense": money(fund.expense),
            "available": money(amount(fund.amount) + amount(fund.expense)),
            "is_active": fund.is_active, "capabilities": fund_capabilities(user, fund.project, fund, change_project)}


def item_data(item):
    return {"id": item.pk, "type": cost_type_data(item.type), "entry_date": item.entry_date,
            "value_date": item.value_date, "amount": money(item.amount), "expense": money(item.expense),
            "available": money(amount(item.amount) + amount(item.expense))}


def point_data(point):
    return {"id": point.pk, "type": cost_type_data(point.type), "entry_date": point.entry_date,
            "value_date": point.value_date, "amount": money(point.amount)}


def totals(rows):
    return {key: money(sum((row[key] for row in rows), ZERO)) for key in ("amount", "expense", "available")}


def overview(funds, items):
    """Cost type x Fund using cached Fund_Item amounts and expenses."""
    by_type = defaultdict(dict)
    types = {}
    for item in items:
        types[item.type_id] = item.type
        by_type[item.type_id][item.fund_id] = {
            "amount": amount(item.amount), "expense": amount(item.expense),
            "available": amount(item.amount) + amount(item.expense),
        }
    rows = []
    for type_id, cells in sorted(by_type.items(), key=lambda pair: (types[pair[0]].short_name, pair[0])):
        rows.append({"type": cost_type_data(types[type_id]),
                     "cells": {str(fund.pk): {key: money(value) for key, value in cell.items()} for fund in funds if (cell := cells.get(fund.pk)) is not None},
                     "total": totals(cells.values())})
    grand = {"amount": sum((amount(fund.amount) for fund in funds), ZERO),
             "expense": sum((amount(fund.expense) for fund in funds), ZERO)}
    grand["available"] = grand["amount"] + grand["expense"]
    return {"rows": rows, "fund_totals": {str(fund.pk): {"amount": money(fund.amount), "expense": money(fund.expense),
             "available": money(amount(fund.amount) + amount(fund.expense))} for fund in funds},
            "grand_total": {key: money(value) for key, value in grand.items()}}


class StrictWriteSerializer(serializers.Serializer):
    immutable_on_update = frozenset()

    def to_internal_value(self, data):
        if isinstance(data, dict):
            allowed = set(self.fields) - (self.immutable_on_update if self.instance else set())
            extra = set(data) - allowed
            if extra:
                raise serializers.ValidationError({key: "This field cannot be supplied or changed." for key in sorted(extra)})
        return super().to_internal_value(data)


class FundWriteSerializer(StrictWriteSerializer):
    immutable_on_update = frozenset({"funder_id", "institution_id"})
    funder_id = serializers.PrimaryKeyRelatedField(source="funder", queryset=Fund_Institution.objects.all(), required=False)
    institution_id = serializers.PrimaryKeyRelatedField(source="institution", queryset=Institution.objects.all(), required=False)
    ref = serializers.CharField(max_length=30, required=False, allow_blank=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    update_project_end = serializers.BooleanField(required=False, default=False, write_only=True)

    def validate(self, attrs):
        instance = self.instance
        project = self.context["project"]
        start = attrs.get("start_date", instance.start_date if instance else project.start_date)
        end = attrs.get("end_date", instance.end_date if instance else project.end_date)
        if end and (not start or end <= start):
            raise serializers.ValidationError({"end_date": "End date must be later than start date."})
        if attrs.get("update_project_end"):
            if not project_capabilities(self.context["request"].user, project)["can_change"]:
                raise PermissionDenied()
            if end and project.start_date and end < project.start_date:
                raise serializers.ValidationError({"update_project_end": "Project end date precedes its start date."})
        return attrs

    def save(self, **kwargs):
        attrs = dict(self.validated_data)
        sync = attrs.pop("update_project_end", False)
        project = self.context["project"]
        if self.instance:
            instance = self.instance
            for key, value in attrs.items():
                setattr(instance, key, value)
        else:
            instance = Fund(project=project, **{"start_date": project.start_date, "end_date": project.end_date, **attrs})
        validate_model(instance)
        instance.save()
        if sync:
            project.end_date = instance.end_date
            validate_model(project)
            project.save()
        return instance


class FundItemWriteSerializer(StrictWriteSerializer):
    immutable_on_update = frozenset({"type_id"})
    type_id = serializers.PrimaryKeyRelatedField(source="type", queryset=Cost_Type.objects.all(), required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    entry_date = serializers.DateField(required=False)
    value_date = serializers.DateField(required=False)

    def validate(self, attrs):
        cost_type = attrs.get("type", self.instance.type if self.instance else None)
        fund = self.context["fund"]
        if cost_type and Fund_Item.objects.filter(fund=fund, type=cost_type).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError({"type_id": "This cost type already exists for the fund."})
        return attrs

    def save(self, **kwargs):
        item = self.instance or Fund_Item(fund=self.context["fund"])
        for key, value in self.validated_data.items():
            setattr(item, key, value)
        validate_model(item)
        item.save()
        return item


class ExpensePointWriteSerializer(FundItemWriteSerializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)

    def validate(self, attrs):
        cost_type = attrs.get("type", self.instance.type if self.instance else None)
        fund = self.context["fund"]
        if cost_type and Expense_point.objects.filter(fund=fund, type=cost_type).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError({"type_id": "This cost type already exists for the fund."})
        if "amount" in attrs:
            attrs["amount"] = -abs(attrs["amount"])
        return attrs

    def save(self, **kwargs):
        point = self.instance or Expense_point(fund=self.context["fund"])
        for key, value in self.validated_data.items():
            setattr(point, key, value)
        validate_model(point)
        point.save()
        return point


class FundingBase(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def project(self):
        if not hasattr(self, "_project"):
            visible = Project.get_instances_for_user("view", self.request.user, Project.objects.all())
            self._project = get_object_or_404(visible, pk=self.kwargs["pk"])
        return self._project

    def funds(self):
        project = self.project()
        visible = Fund.get_instances_for_user("view", self.request.user, Fund.objects.filter(project=project))
        if not visible.exists() and not (self.request.user.has_perm("fund.view_fund") or self.request.user.has_perm("fund.view_fund", project)):
            # A Fund reader may open an empty collection; Project rights alone
            # do not grant visibility into the financial domain.
            raise PermissionDenied()
        return visible.select_related("project", "funder", "institution").order_by("funder__short_name", "ref", "pk")

    def fund(self):
        return get_object_or_404(self.funds(), pk=self.kwargs["fund_id"])

    def require(self, capabilities, key):
        if not capabilities[key]:
            raise PermissionDenied()


class ProjectFundingView(FundingBase):
    def get(self, request, *args, **kwargs):
        funds = list(self.funds())
        items = list(Fund_Item.objects.filter(fund__in=funds).select_related("type", "fund").order_by("type__short_name", "pk"))
        change_project = project_capabilities(request.user, self.project())["can_change"]
        return Response({"capabilities": {"can_add": fund_capabilities(request.user, self.project(), change_project=change_project)["can_add"]},
                         "project_dates": {"start_date": self.project().start_date, "end_date": self.project().end_date},
                         "funds": [fund_data(fund, request.user, change_project) for fund in funds], "overview": overview(funds, items)})

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.funds()
        self.require(fund_capabilities(request.user, self.project()), "can_add")
        serializer = FundWriteSerializer(data=request.data, context={"project": self.project(), "request": request})
        serializer.is_valid(raise_exception=True)
        fund = serializer.save()
        return Response(fund_data(fund, request.user), status=201)


class FundingOptionsView(FundingBase):
    def get(self, request, *args, **kwargs):
        self.funds()
        project = self.project()
        # Institutions and funders are public catalogues in the historical forms.
        visible_institutions = Institution.objects.all()
        return Response({"funders": list(Fund_Institution.objects.order_by("short_name", "pk").values("id", "short_name", "name")),
                         "institutions": list(visible_institutions.order_by("short_name", "pk").values("id", "short_name", "name")),
                         "cost_types": [cost_type_data(item) for item in Cost_Type.objects.order_by("short_name", "pk")],
                         "project_dates": {"start_date": project.start_date, "end_date": project.end_date}})


class FundingFundView(FundingBase):
    def get(self, request, *args, **kwargs):
        fund = self.fund()
        items = list(Fund_Item.objects.filter(fund=fund).select_related("type").order_by("type__short_name", "pk"))
        points = list(Expense_point.objects.filter(fund=fund).select_related("type").order_by("type__short_name", "pk"))
        return Response({"fund": fund_data(fund, request.user), "summary": overview([fund], items)["rows"],
                         "total": {"amount": money(fund.amount), "expense": money(fund.expense), "available": money(amount(fund.amount) + amount(fund.expense))},
                         "items": {"capabilities": fund_item_capabilities(request.user, fund), "items": [item_data(item) for item in items]},
                         "expense_points": {"capabilities": expense_point_capabilities(request.user, fund), "items": [point_data(point) for point in points]}})

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        fund = self.fund()
        self.require(fund_capabilities(request.user, fund.project, fund), "can_change")
        serializer = FundWriteSerializer(fund, data=request.data, partial=True, context={"project": fund.project, "request": request})
        serializer.is_valid(raise_exception=True)
        return Response(fund_data(serializer.save(), request.user))

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        fund = self.fund()
        self.require(fund_capabilities(request.user, fund.project, fund), "can_delete")
        # Deleting Fund_Item while a point remains makes Fund.calculate() recreate
        # that line. Remove unit expenses first (their signals may update points),
        # then points, before the Fund cascade deletes its lines.
        Expense.objects.filter(fund_item=fund).delete()
        Expense_point.objects.filter(fund=fund).delete()
        fund.delete()
        return Response(status=204)


class FundingChildBase(FundingBase):
    model = None
    write_serializer = None
    read_item = None

    def capabilities(self, fund):
        return fund_item_capabilities(self.request.user, fund) if self.model is Fund_Item else expense_point_capabilities(self.request.user, fund)

    def child(self, fund):
        return get_object_or_404(self.model.objects.filter(fund=fund), pk=self.kwargs["item_id"])

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        fund = self.fund()
        self.require(self.capabilities(fund), "can_add")
        serializer = self.write_serializer(data=request.data, context={"fund": fund})
        serializer.is_valid(raise_exception=True)
        return Response(self.read_item(serializer.save()), status=201)

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        fund = self.fund()
        child = self.child(fund)
        self.require(self.capabilities(fund), "can_change")
        serializer = self.write_serializer(child, data=request.data, partial=True, context={"fund": fund})
        serializer.is_valid(raise_exception=True)
        return Response(self.read_item(serializer.save()))

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        fund = self.fund()
        child = self.child(fund)
        self.require(self.capabilities(fund), "can_delete")
        if self.model is Fund_Item and Expense_point.objects.filter(fund=fund, type=child.type).exists():
            raise serializers.ValidationError({"detail": "Delete the expense point for this cost type before deleting its fund item."})
        child.delete()
        if self.model is Expense_point:
            # The historical model has a post_save hook, but no post_delete hook.
            fund.calculate(force=True)
        return Response(status=204)


class FundItemView(FundingChildBase):
    model = Fund_Item
    write_serializer = FundItemWriteSerializer
    read_item = staticmethod(item_data)


class ExpensePointView(FundingChildBase):
    model = Expense_point
    write_serializer = ExpensePointWriteSerializer
    read_item = staticmethod(point_data)
