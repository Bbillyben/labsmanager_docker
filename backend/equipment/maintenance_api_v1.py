"""Permission-scoped maintenance records and their calendar projections."""

from datetime import datetime, timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from common.calendar import CalendarContext, CalendarService, CalendarType, LabsManagerCalendarEvent
from fund.financial_tools_api_v1 import visible_funds
from labsmanager.pagination import LabPagination

from .api_v1 import StrictModelSerializer, validate_model, visible_equipment
from .models import EquipmentExpenseLink, EquipmentMaintenance


def maintenance_capabilities(user):
    """Combine the independent Maintenance permission with Equipment visibility."""
    view = user.has_perm("equipment.view_equipment") and user.has_perm("equipment.view_equipmentmaintenance")
    return {"can_view": view, "can_add": view and user.has_perm("equipment.add_equipmentmaintenance"),
            "can_change": view and user.has_perm("equipment.change_equipmentmaintenance"),
            "can_delete": view and user.has_perm("equipment.delete_equipmentmaintenance")}


def require_maintenance(user, action):
    if not maintenance_capabilities(user)[action]:
        raise PermissionDenied()


def visible_maintenances(user):
    return EquipmentMaintenance.objects.filter(equipment__in=visible_equipment(user))


def financial_links(user, equipment):
    """Only expose links whose financial Expense and Equipment are both visible."""
    if not user.has_perm("equipment.view_equipmentexpenselink"):
        return EquipmentExpenseLink.objects.none()
    return EquipmentExpenseLink.objects.filter(
        equipment=equipment, expense__fund_item__in=visible_funds(user),
    ).select_related("expense")


class MaintenanceWriteSerializer(StrictModelSerializer):
    expense_link_id = serializers.PrimaryKeyRelatedField(
        source="expense_link", queryset=EquipmentExpenseLink.objects.all(), allow_null=True,
        required=False,
    )

    class Meta:
        model = EquipmentMaintenance
        fields = ("title", "maintenance_type", "status", "scheduled_date", "scheduled_start_time",
                  "scheduled_end_time", "performed_date", "description", "report", "expense_link_id")

    def validate(self, attrs):
        equipment = self.context["equipment"]
        link = attrs.get("expense_link")
        if ("expense_link" in attrs and self.instance and self.instance.expense_link_id and
                not financial_links(self.context["request"].user, equipment).filter(pk=self.instance.expense_link_id).exists()):
            raise serializers.ValidationError({"expense_link_id": "Current expense link is not available."})
        if link and not financial_links(self.context["request"].user, equipment).filter(pk=link.pk).exists():
            raise serializers.ValidationError({"expense_link_id": "Expense link is not available for this Equipment."})
        item = self.instance or EquipmentMaintenance(equipment=equipment)
        for field, value in attrs.items():
            setattr(item, field, value)
        validate_model(item)
        return attrs

    def create(self, validated_data):
        return EquipmentMaintenance.objects.create(equipment=self.context["equipment"], **validated_data)


def maintenance_data(item, user):
    """Financial identity is omitted unless both link and Expense are visible."""
    link = item.expense_link
    visible_link = bool(link and financial_links(user, item.equipment).filter(pk=link.pk).exists())
    return {
        "id": item.pk, "equipment": {"id": item.equipment_id, "name": item.equipment.name},
        "title": item.title, "maintenance_type": item.maintenance_type, "status": item.status,
        "scheduled_date": item.scheduled_date, "scheduled_start_time": item.scheduled_start_time,
        "scheduled_end_time": item.scheduled_end_time, "performed_date": item.performed_date,
        "description": item.description, "report": item.report,
        "expense_link": {"id": link.pk, "expense_id": link.expense_id,
                         "label": link.expense.expense_id or str(link.expense_id)} if visible_link else None,
        "capabilities": maintenance_capabilities(user),
    }


def filtered_maintenances(request, queryset):
    """Apply bounded database filters before pagination or event projection."""
    for name, choices in (("maintenance_type", EquipmentMaintenance.Type.values),
                          ("status", EquipmentMaintenance.Status.values)):
        value = request.query_params.get(name)
        if value:
            if value not in choices:
                raise serializers.ValidationError({name: "Unknown value."})
            queryset = queryset.filter(**{name: value})
    for name, lookup in (("from", "scheduled_date__gte"), ("to", "scheduled_date__lte")):
        value = request.query_params.get(name)
        if value:
            value = serializers.DateField().run_validation(value)
            queryset = queryset.filter(**{lookup: value})
    if request.query_params.get("overdue") in ("1", "true"):
        queryset = queryset.filter(scheduled_date__lt=timezone.localdate()).exclude(
            status__in=(EquipmentMaintenance.Status.COMPLETED, EquipmentMaintenance.Status.CANCELLED))
    elif request.query_params.get("overdue") not in (None, "0", "false"):
        raise serializers.ValidationError({"overdue": "Expected 0 or 1."})
    return queryset


class MaintenanceCollection(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def equipment(self):
        return get_object_or_404(visible_equipment(self.request.user), pk=self.kwargs["equipment_id"])

    def get(self, request, *args, **kwargs):
        require_maintenance(request.user, "can_view")
        equipment = self.equipment() if "equipment_id" in self.kwargs else None
        queryset = visible_maintenances(request.user)
        if equipment:
            queryset = queryset.filter(equipment=equipment)
        selected = request.query_params.get("equipment")
        if selected:
            selected = serializers.IntegerField(min_value=1).run_validation(selected)
            queryset = queryset.filter(equipment_id=selected)
        queryset = filtered_maintenances(request, queryset).select_related("equipment", "expense_link__expense")
        paginator = LabPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        response = paginator.get_paginated_response([maintenance_data(item, request.user) for item in page])
        response.data["capabilities"] = maintenance_capabilities(request.user)
        return response

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        require_maintenance(request.user, "can_add")
        if "equipment_id" not in self.kwargs:
            raise serializers.ValidationError({"equipment_id": "Create maintenance from an Equipment."})
        equipment = self.equipment()
        serializer = MaintenanceWriteSerializer(data=request.data, context={"request": request, "equipment": equipment})
        serializer.is_valid(raise_exception=True)
        return Response(maintenance_data(serializer.save(), request.user), status=status.HTTP_201_CREATED)


class MaintenanceDetail(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def item(self):
        require_maintenance(self.request.user, "can_view")
        return get_object_or_404(visible_maintenances(self.request.user).select_related(
            "equipment", "expense_link__expense"), pk=self.kwargs["maintenance_id"])

    def get(self, request, *args, **kwargs):
        return Response(maintenance_data(self.item(), request.user))

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        require_maintenance(request.user, "can_change")
        item = self.item()
        serializer = MaintenanceWriteSerializer(item, data=request.data, partial=True,
                                                context={"request": request, "equipment": item.equipment})
        serializer.is_valid(raise_exception=True)
        return Response(maintenance_data(serializer.save(), request.user))

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        require_maintenance(request.user, "can_delete")
        self.item().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MaintenanceAction(MaintenanceDetail):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        require_maintenance(request.user, "can_change")
        item = self.item()
        action = self.kwargs["action"]
        if item.status in (EquipmentMaintenance.Status.COMPLETED, EquipmentMaintenance.Status.CANCELLED):
            raise serializers.ValidationError({"status": "A closed maintenance cannot be completed or cancelled again."})
        if action == "complete":
            if set(request.data) - {"performed_date", "report"}:
                raise serializers.ValidationError({"detail": "Only performed date and report are accepted."})
            payload = {**request.data, "status": EquipmentMaintenance.Status.COMPLETED}
        elif action == "cancel":
            if request.data:
                raise serializers.ValidationError({"detail": "Cancellation takes no fields."})
            payload = {"status": EquipmentMaintenance.Status.CANCELLED}
        else:
            raise serializers.ValidationError({"action": "Unknown maintenance action."})
        serializer = MaintenanceWriteSerializer(item, data=payload, partial=True,
                                                context={"request": request, "equipment": item.equipment})
        serializer.is_valid(raise_exception=True)
        return Response(maintenance_data(serializer.save(), request.user))


def maintenance_to_event(item):
    """Project one intervention into the shared calendar contract."""
    timed = bool(item.scheduled_start_time and item.scheduled_end_time)
    if timed:
        start = timezone.make_aware(datetime.combine(item.scheduled_date, item.scheduled_start_time))
        end = timezone.make_aware(datetime.combine(item.scheduled_date, item.scheduled_end_time))
    else:
        start, end = item.scheduled_date, item.scheduled_date + timedelta(days=1)
    return LabsManagerCalendarEvent(
        id=f"equipment-maintenance:{item.pk}", title=item.title, start=start, end=end,
        source="core", kind="equipment-maintenance", all_day=not timed,
        metadata={"maintenance_id": item.pk, "equipment_id": item.equipment_id,
                  "status": item.status, "url": f"/equipment/{item.equipment_id}/maintenance?maintenance={item.pk}"},
    )


class MaintenanceCalendar(MaintenanceCollection):
    def get(self, request, *args, **kwargs):
        require_maintenance(request.user, "can_view")
        if not request.query_params.get("from") or not request.query_params.get("to"):
            raise serializers.ValidationError({"from": "A bounded period is required."})
        queryset = visible_maintenances(request.user)
        if "equipment_id" in self.kwargs:
            queryset = queryset.filter(equipment=self.equipment())
            calendar_type = CalendarType.EQUIPMENT
        else:
            calendar_type = CalendarType.EQUIPMENT_MAINTENANCE
            selected = request.query_params.get("equipment")
            if selected:
                queryset = queryset.filter(equipment_id=serializers.IntegerField(min_value=1).run_validation(selected))
        queryset = filtered_maintenances(request, queryset).select_related("equipment")
        context = CalendarContext(calendar_type, user=request.user,
                                  start=serializers.DateField().run_validation(request.query_params["from"]),
                                  end=serializers.DateField().run_validation(request.query_params["to"]),
                                  equipment_id=self.kwargs.get("equipment_id"),
                                  filters=request.query_params)
        if context.start > context.end:
            raise serializers.ValidationError({"to": "Must be on or after from."})
        events = [maintenance_to_event(item) for item in queryset.order_by("scheduled_date", "pk")]
        return Response({"events": [event.as_dict() for event in CalendarService(plugins=[]).get_events(context, events)],
                         "capabilities": maintenance_capabilities(request.user)})


class MaintenanceExpenseOptions(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, equipment_id):
        require_maintenance(request.user, "can_view")
        equipment = get_object_or_404(visible_equipment(request.user), pk=equipment_id)
        return Response([{"id": link.pk, "label": link.expense.expense_id or str(link.expense_id)}
                         for link in financial_links(request.user, equipment).order_by("-expense__date", "-pk")])
