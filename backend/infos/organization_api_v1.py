"""Visibility-scoped v1 API for manager institutions and funders."""

from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from expense.models import Contract
from expense.contract_hub_api_v1 import ContractHubListSerializer, contract_hub_queryset, contract_hub_serializer_context
from fund.models import Fund, Fund_Institution
from labsmanager.admin_links_v1 import get_admin_change_url
from labsmanager.pagination import LabPagination
from project.models import Institution, Project
from project.api_v1 import ProjectListV1Serializer, project_list_queryset
from settings.models import LMUserSetting

from .models import Contact, ContactInfo, ContactInfoType, ContactType, OrganizationInfos, OrganizationInfosType
from .api_v1 import visible_note_counts

KINDS = {"institutions": Institution, "funders": Fund_Institution}
CHILDREN = {"infos": (OrganizationInfos, OrganizationInfosType, "info"), "contacts": (Contact, ContactType, "type")}


def model_for(kind):
    model = KINDS.get(kind)
    if model is None:
        raise Http404
    return model


def allowed(user, model, action, obj=None):
    permission = f"{model._meta.app_label}.{action}_{model._meta.model_name}"
    return user.has_perm(permission) or bool(obj and user.has_perm(permission, obj))


def capabilities(user, model, obj=None):
    return {"can_add": allowed(user, model, "add"), "can_change": bool(obj and allowed(user, model, "change", obj)), "can_delete": bool(obj and allowed(user, model, "delete", obj))}


def visible_org(user, kind, pk):
    model = model_for(kind)
    if not user.has_perm("common.display_infos"):
        raise Http404
    return get_object_or_404(model, pk=pk)


def require(user, model, action, obj=None):
    if not allowed(user, model, action, obj):
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied


def validate_save(obj):
    try:
        obj.full_clean()
        obj.save()
    except DjangoValidationError as error:
        raise serializers.ValidationError(getattr(error, "message_dict", None) or error.messages) from error
    except IntegrityError as error:
        raise serializers.ValidationError({"detail": "duplicate_value"}) from error


def org_data(user, org):
    rights = capabilities(user, type(org), org)
    relation = "institution" if isinstance(org, Institution) else "funder"
    has_funds = getattr(org, "_has_funds", None)
    if has_funds is None:
        has_funds = Fund.objects.filter(**{relation: org}).exists()
    rights["can_delete"] = rights["can_delete"] and not has_funds
    return {"id": org.pk, "short_name": org.short_name, "name": org.name,
            "admin_url": get_admin_change_url(user, org), "capabilities": rights}


def type_data(value):
    return {"id": value.pk, "name": value.name, "icon": getattr(value, "icon", None), "type": getattr(value, "type", None)}


def child_data(user, obj, kind):
    result = {"id": obj.pk, "admin_url": get_admin_change_url(user, obj), "capabilities": capabilities(user, type(obj), obj)}
    if kind == "contacts":
        result.update(first_name=obj.first_name, last_name=obj.last_name, type=type_data(obj.type), comment=obj.comment)
    else:
        result.update(info=type_data(obj.info), value=obj.value, comment=obj.comment)
    return result


def visible_funds(user, org):
    field = "institution" if isinstance(org, Institution) else "funder"
    base = Fund.objects.filter(**{field: org})
    return Fund.get_instances_for_user("view", user, base).filter(pk__in=base.values("pk"))


def visible_projects(user, org, funds=None):
    funds = funds if funds is not None else visible_funds(user, org)
    base = Project.objects.filter(pk__in=funds.values("project_id"))
    return Project.get_instances_for_user("view", user, base).filter(pk__in=base.values("pk")).distinct()


def visible_contracts(user, org, funds=None):
    funds = funds if funds is not None else visible_funds(user, org)
    projects = visible_projects(user, org, funds)
    base = Contract.objects.filter(fund__in=funds, fund__project__in=projects)
    return Contract.get_instances_for_user("view", user, base).filter(pk__in=base.values("pk"))


class OrganizationList(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, kind):
        model = model_for(kind)
        if not request.user.has_perm("common.display_infos"):
            raise Http404
        search = request.query_params.get("search", "").strip()
        relation = "institution_id" if kind == "institutions" else "funder_id"
        queryset = model.objects.annotate(_has_funds=Exists(Fund.objects.filter(**{relation: OuterRef("pk")})))
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(short_name__icontains=search))
        ordering = request.query_params.get("ordering", "short_name")
        queryset = queryset.order_by(ordering if ordering in ("short_name", "-short_name", "name", "-name") else "short_name", "pk")
        paginator = LabPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        result = paginator.get_paginated_response([org_data(request.user, obj) for obj in page])
        result.data["capabilities"] = {"can_add": allowed(request.user, model, "add")}
        return result

    def post(self, request, kind):
        model = model_for(kind)
        if not request.user.has_perm("common.display_infos"):
            raise Http404
        require(request.user, model, "add")
        data = OrganizationWrite(data=request.data)
        data.is_valid(raise_exception=True)
        with transaction.atomic():
            obj = model(**data.validated_data)
            validate_save(obj)
        return Response(org_data(request.user, obj), status=201)


class OrganizationDetail(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, kind, pk):
        return Response(org_data(request.user, visible_org(request.user, kind, pk)))

    def patch(self, request, kind, pk):
        obj = visible_org(request.user, kind, pk)
        require(request.user, type(obj), "change", obj)
        data = OrganizationWrite(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        for field, value in data.validated_data.items():
            setattr(obj, field, value)
        with transaction.atomic():
            validate_save(obj)
        return Response(org_data(request.user, obj))

    def delete(self, request, kind, pk):
        obj = visible_org(request.user, kind, pk)
        require(request.user, type(obj), "delete", obj)
        relation = "institution" if isinstance(obj, Institution) else "funder"
        if Fund.objects.filter(**{relation: obj}).exists():
            raise serializers.ValidationError({"detail": "referenced_by_fund"})
        from django.db.models.deletion import ProtectedError
        try:
            obj.delete()
        except ProtectedError as error:
            raise serializers.ValidationError({"detail": "referenced_object"}) from error
        return Response(status=204)


class OrganizationWrite(serializers.Serializer):
    short_name = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=150)


class ChildWrite(serializers.Serializer):
    type_id = serializers.IntegerField(required=False)
    info_id = serializers.IntegerField(required=False)
    first_name = serializers.CharField(max_length=50, required=False)
    last_name = serializers.CharField(max_length=50, required=False)
    value = serializers.CharField(max_length=150, allow_blank=True, allow_null=True, required=False)
    comment = serializers.CharField(max_length=350, allow_blank=True, allow_null=True, required=False)


class OrganizationOptions(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, kind, pk):
        visible_org(request.user, kind, pk)
        return Response({"organization_info_types": [type_data(x) for x in OrganizationInfosType.objects.order_by("name", "pk")],
                         "contact_types": [type_data(x) for x in ContactType.objects.order_by("name", "pk")],
                         "contact_info_types": [type_data(x) for x in ContactInfoType.objects.order_by("name", "pk")],
                         "map_provider": LMUserSetting.get_setting("MAP_PROVIDER", user=request.user)})


class OrganizationChildren(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, kind, pk, collection):
        org = visible_org(request.user, kind, pk)
        model, _, relation = CHILDREN[collection]
        ct = ContentType.objects.get_for_model(org)
        items = model.objects.filter(content_type=ct, object_id=org.pk).select_related(relation).order_by(relation + "__name", "pk")
        return Response({"items": [child_data(request.user, x, collection) for x in items], "capabilities": {"can_add": allowed(request.user, model, "add")}})

    def post(self, request, kind, pk, collection):
        org = visible_org(request.user, kind, pk)
        model, type_model, relation = CHILDREN[collection]
        require(request.user, model, "add")
        data = ChildWrite(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        type_id = values.pop("type_id" if collection == "contacts" else "info_id", None)
        if type_id is None:
            raise serializers.ValidationError({"type_id" if collection == "contacts" else "info_id": "required"})
        selected = get_object_or_404(type_model, pk=type_id)
        fields = ("first_name", "last_name", "comment") if collection == "contacts" else ("value", "comment")
        obj = model(content_type=ContentType.objects.get_for_model(org), object_id=org.pk, **{relation: selected}, **{k: v for k, v in values.items() if k in fields})
        with transaction.atomic():
            validate_save(obj)
        return Response(child_data(request.user, obj, collection), status=201)


class OrganizationChildDetail(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def child(self, request, kind, pk, collection, item_id):
        org = visible_org(request.user, kind, pk)
        model, _, relation = CHILDREN[collection]
        return get_object_or_404(model.objects.select_related(relation), pk=item_id, content_type=ContentType.objects.get_for_model(org), object_id=org.pk)

    def get(self, request, kind, pk, collection, item_id):
        return Response(child_data(request.user, self.child(request, kind, pk, collection, item_id), collection))

    def patch(self, request, kind, pk, collection, item_id):
        obj = self.child(request, kind, pk, collection, item_id)
        require(request.user, type(obj), "change", obj)
        data = ChildWrite(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        key = "type_id" if collection == "contacts" else "info_id"
        if key in values:
            _, type_model, relation = CHILDREN[collection]
            setattr(obj, relation, get_object_or_404(type_model, pk=values[key]))
        fields = ("first_name", "last_name", "comment") if collection == "contacts" else ("value", "comment")
        for field in fields:
            if field in values:
                setattr(obj, field, values[field])
        with transaction.atomic():
            validate_save(obj)
        return Response(child_data(request.user, obj, collection))

    def delete(self, request, kind, pk, collection, item_id):
        obj = self.child(request, kind, pk, collection, item_id)
        require(request.user, type(obj), "delete", obj)
        obj.delete()
        return Response(status=204)


class ContactInfos(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, kind, pk, contact_id):
        contact = OrganizationChildDetail().child(request, kind, pk, "contacts", contact_id)
        items = ContactInfo.objects.filter(contact=contact).select_related("info").order_by("info__name", "pk")
        return Response({"items": [child_data(request.user, x, "infos") for x in items], "capabilities": {"can_add": allowed(request.user, ContactInfo, "add")}})

    def post(self, request, kind, pk, contact_id):
        contact = OrganizationChildDetail().child(request, kind, pk, "contacts", contact_id)
        require(request.user, ContactInfo, "add")
        data = ChildWrite(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        if "info_id" not in values:
            raise serializers.ValidationError({"info_id": "required"})
        obj = ContactInfo(contact=contact, info=get_object_or_404(ContactInfoType, pk=values["info_id"]), value=values.get("value"), comment=values.get("comment"))
        with transaction.atomic():
            validate_save(obj)
        return Response(child_data(request.user, obj, "infos"), status=201)


class ContactInfoDetail(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def child(self, request, kind, pk, contact_id, item_id):
        contact = OrganizationChildDetail().child(request, kind, pk, "contacts", contact_id)
        return get_object_or_404(ContactInfo.objects.select_related("info"), pk=item_id, contact=contact)

    def get(self, request, kind, pk, contact_id, item_id):
        return Response(child_data(request.user, self.child(request, kind, pk, contact_id, item_id), "infos"))

    def patch(self, request, kind, pk, contact_id, item_id):
        obj = self.child(request, kind, pk, contact_id, item_id)
        require(request.user, ContactInfo, "change", obj)
        data = ChildWrite(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        for field in ("value", "comment"):
            if field in data.validated_data:
                setattr(obj, field, data.validated_data[field])
        if "info_id" in data.validated_data:
            obj.info = get_object_or_404(ContactInfoType, pk=data.validated_data["info_id"])
        with transaction.atomic():
            validate_save(obj)
        return Response(child_data(request.user, obj, "infos"))

    def delete(self, request, kind, pk, contact_id, item_id):
        obj = self.child(request, kind, pk, contact_id, item_id)
        require(request.user, ContactInfo, "delete", obj)
        obj.delete()
        return Response(status=204)


class OrganizationProjects(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, kind, pk):
        org = visible_org(request.user, kind, pk)
        funds = visible_funds(request.user, org)
        projects = visible_projects(request.user, org, funds)
        rows = project_list_queryset(request.user).filter(pk__in=projects.values("pk")).order_by("name", "pk")
        return Response(ProjectListV1Serializer(rows, many=True, context={"request": request}).data)


class OrganizationContracts(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, kind, pk):
        org = visible_org(request.user, kind, pk)
        scoped = visible_contracts(request.user, org)
        contracts = list(contract_hub_queryset(request.user).filter(pk__in=scoped.values("pk")).order_by("employee__last_name", "employee__first_name", "pk"))
        note_counts = visible_note_counts(request.user, Contract, (item.pk for item in contracts))
        return Response(ContractHubListSerializer(contracts, many=True, context=contract_hub_serializer_context(request, note_counts)).data)


class OrganizationSummary(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, kind, pk):
        org = visible_org(request.user, kind, pk)
        funds = visible_funds(request.user, org).select_related("project")
        projects = visible_projects(request.user, org, funds)
        project_ids = set(projects.values_list("pk", flat=True))
        related_funds = [x for x in funds if x.project_id in project_ids]
        contracts = visible_contracts(request.user, org, Fund.objects.filter(pk__in=[x.pk for x in related_funds])).only("start_date", "end_date", "is_active")
        today = timezone.localdate()
        def total(field):
            return sum((getattr(x, field) or Decimal(0) for x in related_funds), Decimal(0))
        current = sum(1 for x in contracts if (x.start_date is None or x.start_date <= today) and (x.end_date is None or x.end_date >= today))
        months = sum(((x.end_date.year - x.start_date.year) * 12 + x.end_date.month - x.start_date.month) for x in contracts if x.start_date and x.end_date)
        return Response({"projects": {"total": len(project_ids), "open": projects.filter(status=True).count(), "total_amount": total("amount"),
                                       "available_amount": total("amount") + total("expense"), "available_amount_focus": total("amount_f") + total("expense_f")},
                         "contracts": {"total": len(contracts), "current": current, "active": sum(x.is_active for x in contracts), "man_months": months}})
