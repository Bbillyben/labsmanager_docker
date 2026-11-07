"""Permission-scoped Equipment catalogue and historical child APIs."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Prefetch, ProtectedError, Q
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as django_filters
from rest_framework import generics, permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from infos.models import GenericNote
from labsmanager.admin_links_v1 import AdminUrlSerializerMixin
from labsmanager.pagination import LabPagination
from project.models import Institution
from staff.models import Employee

from .models import (
    Equipment, EquipmentCategory, EquipmentGenericInfo, EquipmentGenericInfoType,
    EquipmentInstitutionInventory, EquipmentResponsibility,
)


def validate_model(item):
    """Use model constraints for API writes as well as Django Admin forms."""
    try:
        item.full_clean()
    except DjangoValidationError as error:
        raise serializers.ValidationError(getattr(error, "message_dict", None) or error.messages) from error


def equipment_capabilities(user, equipment=None):
    """Advertise model permissions; each mutation checks them again."""
    return {
        "can_view": user.has_perm("equipment.view_equipment"),
        "can_view_maintenance": user.has_perm("equipment.view_equipment") and user.has_perm("equipment.view_equipmentmaintenance"),
        "can_add": user.has_perm("equipment.view_equipment") and user.has_perm("equipment.add_equipment"),
        "can_change": user.has_perm("equipment.change_equipment"),
        "can_delete": user.has_perm("equipment.delete_equipment") and (
            equipment is None or not (
                equipment.generic_info.exists() or equipment.responsibilities.exists()
                or equipment.institution_inventories.exists() or equipment.expense_links.exists()
                or equipment.maintenances.exists()
                or GenericNote.objects.filter(content_type__app_label="equipment", content_type__model="equipment", object_id=equipment.pk).exists()
            )
        ),
    }


def require(user, permission):
    if not user.has_perm(permission):
        raise PermissionDenied()


def visible_equipment(user):
    return Equipment.get_instances_for_user("view", user, Equipment.objects.all())


def equipment_read_context(request, item):
    """Apply the same related-identity visibility rules to one Equipment."""
    ids = set(Employee.get_instances_for_user("view", request.user, Employee.objects.filter(
        pk__in=item.responsibilities.filter(EquipmentResponsibility.get_active_filter()).values("employee_id")
    )).values_list("pk", flat=True))
    return {"request": request, "detail": True, "visible_employee_ids": ids,
            "can_view_institution": request.user.has_perm("common.display_infos") or request.user.has_perm("project.view_institution")}


class StrictModelSerializer(serializers.ModelSerializer):
    """Reject unknown write fields instead of silently ignoring them."""

    def to_internal_value(self, data):
        if isinstance(data, dict):
            unexpected = set(data) - set(self.fields)
            if unexpected:
                raise serializers.ValidationError({key: "Unknown field." for key in sorted(unexpected)})
        return super().to_internal_value(data)


class EquipmentReadSerializer(AdminUrlSerializerMixin, serializers.ModelSerializer):
    category = serializers.SerializerMethodField()
    current_responsibles = serializers.SerializerMethodField()
    current_institutions = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = ("id", "admin_url", "name", "internal_reference", "category", "current_responsibles", "current_institutions", "status", "status_label",
                  "acquisition_date", "commissioning_date", "decommissioning_date", "capabilities")

    def get_category(self, item):
        return {"id": item.category_id, "name": item.category.name, "is_active": item.category.is_active}

    def get_current_responsibles(self, item):
        relations = getattr(item, "current_responsibility_rows", None)
        if relations is None:
            relations = item.responsibilities.filter(EquipmentResponsibility.get_active_filter()).select_related("employee")
        visible = self.context.get("visible_employee_ids", set())
        return [{"id": row.employee_id if row.employee_id in visible else None,
                 "name": str(row.employee) if row.employee_id in visible else None}
                for row in relations]

    def get_current_institutions(self, item):
        relations = getattr(item, "current_institution_rows", None)
        if relations is None:
            relations = item.institution_inventories.filter(
                EquipmentInstitutionInventory.get_active_filter(), status="registered"
            ).select_related("institution")
        visible = self.context.get("can_view_institution", False)
        return [{"id": row.institution_id if visible else None,
                 "name": row.institution.short_name if visible else None} for row in relations]

    def get_capabilities(self, item):
        user = self.context["request"].user
        capabilities = equipment_capabilities(user, item if self.context.get("detail") else None)
        if self.context.get("detail"):
            from reports.api_v1 import report_capabilities
            capabilities.update(report_capabilities(user, "equipment", item))
        return capabilities


class EquipmentWriteSerializer(StrictModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(source="category", queryset=EquipmentCategory.objects.all())

    class Meta:
        model = Equipment
        fields = ("id", "name", "internal_reference", "category_id", "status", "acquisition_date",
                  "commissioning_date", "decommissioning_date")
        read_only_fields = ("id",)

    def validate(self, attrs):
        if self.instance and "internal_reference" in attrs and attrs["internal_reference"] != self.instance.internal_reference:
            raise serializers.ValidationError({"internal_reference": "Internal reference cannot be changed."})
        category = attrs.get("category", self.instance.category if self.instance else None)
        if category and not category.is_active and (self.instance is None or category.pk != self.instance.category_id):
            raise serializers.ValidationError({"category_id": "Inactive category cannot be selected."})
        return attrs

    def create(self, validated_data):
        item = Equipment(**validated_data)
        validate_model(item)
        item.save()
        return item

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        validate_model(instance)
        instance.save()
        return instance


class EquipmentListFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="category_id")
    status = django_filters.ChoiceFilter(choices=Equipment.Status.choices)
    institution = django_filters.NumberFilter(method="filter_institution")
    responsible = django_filters.NumberFilter(method="filter_responsible")

    def filter_institution(self, queryset, _name, value):
        user = self.request.user
        if not (user.has_perm("common.display_infos") or user.has_perm("project.view_institution")):
            return queryset.none()
        current = EquipmentInstitutionInventory.objects.filter(
            EquipmentInstitutionInventory.get_active_filter(), status="registered", institution_id=value
        ).values("equipment_id")
        return queryset.filter(pk__in=current)

    def filter_responsible(self, queryset, _name, value):
        if not Employee.get_instances_for_user(
            "view", self.request.user, Employee.objects.filter(pk=value)
        ).exists():
            return queryset.none()
        current = EquipmentResponsibility.objects.filter(
            EquipmentResponsibility.get_active_filter(), employee_id=value
        ).values("equipment_id")
        return queryset.filter(pk__in=current)

    class Meta:
        model = Equipment
        fields = ("category", "status", "institution", "responsible")


class EquipmentCollection(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = LabPagination
    filter_backends = (django_filters.DjangoFilterBackend,)
    filterset_class = EquipmentListFilter

    def get_queryset(self):
        queryset = visible_equipment(self.request.user).select_related("category").prefetch_related(
            Prefetch("responsibilities", queryset=EquipmentResponsibility.objects.filter(
                EquipmentResponsibility.get_active_filter()).select_related("employee"), to_attr="current_responsibility_rows"),
            Prefetch("institution_inventories", queryset=EquipmentInstitutionInventory.objects.filter(
                EquipmentInstitutionInventory.get_active_filter(), status="registered"
            ).select_related("institution"), to_attr="current_institution_rows"),
        )
        query = self.request.query_params.get("search", "").strip()
        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(internal_reference__icontains=query))
        ordering = self.request.query_params.get("ordering", "name")
        if ordering not in ("name", "-name", "internal_reference", "-internal_reference", "category__name", "-category__name", "status", "-status"):
            raise serializers.ValidationError({"ordering": "Unsupported order."})
        return queryset.distinct().order_by(ordering, "pk")

    def get_serializer_class(self):
        return EquipmentWriteSerializer if self.request.method == "POST" else EquipmentReadSerializer

    def list(self, request, *args, **kwargs):
        require(request.user, "equipment.view_equipment")
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        items = page if page is not None else list(queryset)
        employee_ids = {row.employee_id for item in items for row in item.current_responsibility_rows}
        visible_ids = set(Employee.get_instances_for_user(
            "view", request.user, Employee.objects.filter(pk__in=employee_ids)
        ).values_list("pk", flat=True))
        serializer = self.get_serializer(items, many=True, context={**self.get_serializer_context(),
            "visible_employee_ids": visible_ids,
            "can_view_institution": request.user.has_perm("common.display_infos") or request.user.has_perm("project.view_institution")})
        response = self.get_paginated_response(serializer.data) if page is not None else Response(serializer.data)
        response.data["capabilities"] = equipment_capabilities(request.user)
        return response

    @transaction.atomic
    def perform_create(self, serializer):
        require(self.request.user, "equipment.view_equipment")
        require(self.request.user, "equipment.add_equipment")
        serializer.save()

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        item = Equipment.objects.select_related("category").get(pk=response.data["id"])
        response.data = EquipmentReadSerializer(item, context=equipment_read_context(request, item)).data
        return response


class EquipmentDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return visible_equipment(self.request.user).select_related("category")

    def get_serializer_class(self):
        return EquipmentWriteSerializer if self.request.method in ("PATCH", "PUT") else EquipmentReadSerializer

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "detail": True}

    def retrieve(self, request, *args, **kwargs):
        item = self.get_object()
        return Response(EquipmentReadSerializer(item, context=equipment_read_context(request, item)).data)

    def perform_update(self, serializer):
        require(self.request.user, "equipment.change_equipment")
        serializer.save()

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        item = self.get_object()
        response.data = EquipmentReadSerializer(item, context=equipment_read_context(request, item)).data
        return response

    @transaction.atomic
    def perform_destroy(self, instance):
        require(self.request.user, "equipment.delete_equipment")
        if not equipment_capabilities(self.request.user, instance)["can_delete"]:
            raise serializers.ValidationError({"detail": "Equipment with related history or notes cannot be deleted."})
        try:
            instance.delete()
        except ProtectedError as error:
            raise serializers.ValidationError({"detail": "Equipment with related history cannot be deleted."}) from error


class EquipmentCapabilities(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response(equipment_capabilities(request.user))


class EquipmentInstitutionOptions(APIView):
    """Return bounded Institution choices without bypassing its visibility right."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        require(request.user, "equipment.view_equipment")
        if not (request.user.has_perm("common.display_infos") or request.user.has_perm("project.view_institution")):
            raise PermissionDenied()
        queryset = Institution.objects.all()
        identifier = request.query_params.get("id")
        if identifier:
            if not identifier.isdecimal() or int(identifier) < 1:
                raise serializers.ValidationError({"id": "A positive integer is required."})
            queryset = queryset.filter(pk=identifier)
        search = request.query_params.get("search", "").strip()[:100]
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(short_name__icontains=search))
        rows = list(queryset.order_by("short_name", "pk").values("id", "name", "short_name")[:11])
        return Response({"results": rows[:10], "has_more": len(rows) > 10})


class CategorySerializer(StrictModelSerializer):
    class Meta:
        model = EquipmentCategory
        fields = ("id", "name", "is_active")
        read_only_fields = ("id",)

    def create(self, validated_data):
        item = self.Meta.model(**validated_data)
        validate_model(item)
        item.save()
        return item

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        validate_model(instance)
        instance.save()
        return instance


class CategoryCollection(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CategorySerializer
    queryset = EquipmentCategory.objects.all()
    pagination_class = None

    def list(self, request, *args, **kwargs):
        if not (request.user.has_perm("equipment.view_equipment") or request.user.has_perm("equipment.view_equipmentcategory")):
            raise PermissionDenied()
        response = super().list(request, *args, **kwargs)
        response.data = {"items": response.data, "capabilities": {
            "can_add": request.user.has_perm("equipment.add_equipmentcategory"),
            "can_change": request.user.has_perm("equipment.change_equipmentcategory"),
            "can_delete": request.user.has_perm("equipment.delete_equipmentcategory"),
        }}
        return response

    def perform_create(self, serializer):
        require(self.request.user, "equipment.add_equipmentcategory")
        serializer.save()


class CategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CategorySerializer
    queryset = EquipmentCategory.objects.all()

    def retrieve(self, request, *args, **kwargs):
        if not (request.user.has_perm("equipment.view_equipment") or request.user.has_perm("equipment.view_equipmentcategory")):
            raise PermissionDenied()
        return super().retrieve(request, *args, **kwargs)

    def perform_update(self, serializer):
        require(self.request.user, "equipment.change_equipmentcategory")
        serializer.save()

    def perform_destroy(self, instance):
        require(self.request.user, "equipment.delete_equipmentcategory")
        try:
            instance.delete()
        except ProtectedError as error:
            raise serializers.ValidationError({"detail": "Category is used by equipment."}) from error


class GenericInfoTypeSerializer(CategorySerializer):
    class Meta:
        model = EquipmentGenericInfoType
        fields = ("id", "name", "icon")
        read_only_fields = ("id",)


class GenericInfoTypeCollection(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = GenericInfoTypeSerializer
    queryset = EquipmentGenericInfoType.objects.all()
    pagination_class = None

    def list(self, request, *args, **kwargs):
        if not (request.user.has_perm("equipment.view_equipment") or request.user.has_perm("equipment.view_equipmentgenericinfotype")):
            raise PermissionDenied()
        response = super().list(request, *args, **kwargs)
        response.data = {"items": response.data, "capabilities": {
            "can_add": request.user.has_perm("equipment.add_equipmentgenericinfotype"),
            "can_change": request.user.has_perm("equipment.change_equipmentgenericinfotype"),
            "can_delete": request.user.has_perm("equipment.delete_equipmentgenericinfotype"),
        }}
        return response

    def perform_create(self, serializer):
        require(self.request.user, "equipment.add_equipmentgenericinfotype")
        serializer.save()


class GenericInfoTypeDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = GenericInfoTypeSerializer
    queryset = EquipmentGenericInfoType.objects.all()

    def retrieve(self, request, *args, **kwargs):
        if not (request.user.has_perm("equipment.view_equipment") or request.user.has_perm("equipment.view_equipmentgenericinfotype")):
            raise PermissionDenied()
        return super().retrieve(request, *args, **kwargs)

    def perform_update(self, serializer):
        require(self.request.user, "equipment.change_equipmentgenericinfotype")
        serializer.save()

    def perform_destroy(self, instance):
        require(self.request.user, "equipment.delete_equipmentgenericinfotype")
        try:
            instance.delete()
        except ProtectedError as error:
            raise serializers.ValidationError({"detail": "Information type is used."}) from error


class GenericInfoReadSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()

    class Meta:
        model = EquipmentGenericInfo
        fields = ("id", "type", "value")

    def get_type(self, item):
        return {"id": item.info_id, "name": item.info.name, "icon": item.info.icon or None}


class ResponsibilityReadSerializer(serializers.ModelSerializer):
    employee = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = EquipmentResponsibility
        fields = ("id", "employee", "start_date", "end_date", "is_active")

    def get_employee(self, item):
        visible = item.employee_id in self.context.get("visible_employee_ids", set())
        return {"id": item.employee_id if visible else None, "name": str(item.employee) if visible else None,
                "is_active": item.employee.is_active if visible else None, "can_view": visible}


class InventoryReadSerializer(serializers.ModelSerializer):
    institution = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = EquipmentInstitutionInventory
        fields = ("id", "institution", "start_date", "end_date", "inventory_number", "status", "status_label", "is_active")

    def get_institution(self, item):
        visible = self.context.get("can_view_institution", False)
        return {"id": item.institution_id if visible else None, "short_name": item.institution.short_name if visible else None,
                "name": item.institution.name if visible else None, "can_view": visible}


class ChildWriteSerializer(serializers.Serializer):
    """Child identity and parent are fixed by the URL once created."""

    def to_internal_value(self, data):
        if isinstance(data, dict):
            unexpected = set(data) - set(self.fields)
            if unexpected:
                raise serializers.ValidationError({key: "Unknown field." for key in sorted(unexpected)})
        return super().to_internal_value(data)

    def create(self, validated_data):
        item = self.Meta.model(equipment=self.context["equipment"], **validated_data)
        validate_model(item)
        item.save()
        return item

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        validate_model(instance)
        instance.save()
        return instance


class GenericInfoWriteSerializer(ChildWriteSerializer):
    type_id = serializers.PrimaryKeyRelatedField(source="info", queryset=EquipmentGenericInfoType.objects.all())
    value = serializers.CharField(max_length=150, required=False, allow_blank=True, allow_null=True, trim_whitespace=False)

    class Meta:
        model = EquipmentGenericInfo


class ResponsibilityWriteSerializer(ChildWriteSerializer):
    employee_id = serializers.PrimaryKeyRelatedField(source="employee", queryset=Employee.objects.all())
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = EquipmentResponsibility

    def validate(self, attrs):
        if self.instance is None:
            visible = Employee.get_instances_for_user("view", self.context["request"].user, Employee.objects.all())
            if not visible.filter(pk=attrs["employee"].pk).exists():
                raise serializers.ValidationError({"employee_id": "Employee is not available."})
        return attrs


class InventoryWriteSerializer(ChildWriteSerializer):
    institution_id = serializers.PrimaryKeyRelatedField(source="institution", queryset=Institution.objects.all())
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    inventory_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=EquipmentInstitutionInventory.Status.choices, required=False)

    class Meta:
        model = EquipmentInstitutionInventory

    def validate(self, attrs):
        if self.instance is None:
            user = self.context["request"].user
            if not (user.has_perm("common.display_infos") or user.has_perm("project.view_institution")):
                raise serializers.ValidationError({"institution_id": "Institution is not available."})
        return attrs


CHILDREN = {
    "generic-info": (EquipmentGenericInfo, "generic_info", "equipmentgenericinfo", GenericInfoWriteSerializer, GenericInfoReadSerializer),
    "responsibilities": (EquipmentResponsibility, "responsibilities", "equipmentresponsibility", ResponsibilityWriteSerializer, ResponsibilityReadSerializer),
    "institutions": (EquipmentInstitutionInventory, "institution_inventories", "equipmentinstitutioninventory", InventoryWriteSerializer, InventoryReadSerializer),
}


class ChildBase(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    resource = None

    def parent(self):
        if not hasattr(self, "_equipment"):
            self._equipment = get_object_or_404(visible_equipment(self.request.user), pk=self.kwargs["pk"])
        return self._equipment

    def spec(self):
        return CHILDREN[self.resource]

    def queryset(self):
        model, _, _, _, _ = self.spec()
        queryset = model.objects.filter(equipment=self.parent())
        if model is EquipmentGenericInfo:
            return queryset.select_related("info")
        if model is EquipmentResponsibility:
            return queryset.select_related("employee")
        return queryset.select_related("institution")

    def context(self):
        user = self.request.user
        return {"equipment": self.parent(), "request": self.request,
                "visible_employee_ids": set(Employee.get_instances_for_user("view", user, Employee.objects.all()).values_list("pk", flat=True)) if self.resource == "responsibilities" else set(),
                "can_view_institution": user.has_perm("common.display_infos") or user.has_perm("project.view_institution")}

    def rights(self):
        _, _, model_name, _, _ = self.spec()
        user = self.request.user
        parent_change = user.has_perm("equipment.change_equipment")
        return {action: parent_change and user.has_perm(f"equipment.{verb}_{model_name}")
                for action, verb in (("can_add", "add"), ("can_change", "change"), ("can_delete", "delete"))}

    def require_action(self, action):
        if not self.rights()[action]:
            raise PermissionDenied()

    def read(self, item):
        return self.spec()[4](item, context=self.context()).data


class ChildCollection(ChildBase):
    def get(self, request, *args, **kwargs):
        return Response({"capabilities": self.rights(), "items": self.spec()[4](self.queryset(), many=True, context=self.context()).data})

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.parent()
        self.require_action("can_add")
        serializer = self.spec()[3](data=request.data, context=self.context())
        serializer.is_valid(raise_exception=True)
        return Response(self.read(serializer.save()), status=201)


class ChildDetail(ChildBase):
    def item(self):
        return get_object_or_404(self.queryset(), pk=self.kwargs["item_id"])

    def get(self, request, *args, **kwargs):
        return Response(self.read(self.item()))

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        item = self.item()
        self.require_action("can_change")
        data = request.data
        identity = {"generic-info": "type_id", "responsibilities": "employee_id", "institutions": "institution_id"}[self.resource]
        if identity in data or "equipment" in data or "equipment_id" in data:
            raise serializers.ValidationError({identity: "Relation identity cannot be changed."})
        serializer = self.spec()[3](item, data=data, partial=True, context=self.context())
        serializer.is_valid(raise_exception=True)
        return Response(self.read(serializer.save()))

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        item = self.item()
        self.require_action("can_delete")
        item.delete()
        return Response(status=204)


def child_view(resource, *, detail=False):
    return (ChildDetail if detail else ChildCollection).as_view(resource=resource)
