"""Equipment KPI providers using the same visibility rules as the Equipment API."""

from datetime import timedelta

from django.utils import timezone
from django.utils.translation import gettext as _


def _visible_equipment(user, scope):
    """Filter Equipment by view permission and current personal responsibility."""
    from equipment.models import Equipment, EquipmentResponsibility

    visible = Equipment.get_instances_for_user("view", user, Equipment.objects.all())
    if scope == "mine":
        responsible_ids = EquipmentResponsibility.objects.filter(
            employee__user=user,
        ).filter(EquipmentResponsibility.get_active_filter()).values("equipment_id")
        visible = visible.filter(pk__in=responsible_ids)
    return visible


def can_view_equipment(context):
    return context.user.has_perm("equipment.view_equipment")


def can_view_maintenance(context):
    return can_view_equipment(context) and context.user.has_perm("equipment.view_equipmentmaintenance")


def my_equipment(context, config):
    """Count distinct Equipment currently assigned to the dashboard owner."""
    return {"value": _visible_equipment(context.user, "mine").count(),
            "label": _("My equipment"), "tone": "neutral"}


def _maintenance_queryset(context, config):
    from equipment.models import EquipmentMaintenance

    if not can_view_maintenance(context):
        return EquipmentMaintenance.objects.none()
    scope = config.get("scope", "all_visible")
    return EquipmentMaintenance.objects.filter(
        equipment__in=_visible_equipment(context.user, scope),
        status__in=(EquipmentMaintenance.Status.PLANNED, EquipmentMaintenance.Status.IN_PROGRESS),
    )


def upcoming_maintenance(context, config):
    """Count open interventions scheduled from today through the configured horizon."""
    today = timezone.localdate()
    days = config.get("within_days", 30)
    count = _maintenance_queryset(context, config).filter(
        scheduled_date__gte=today, scheduled_date__lte=today + timedelta(days=days),
    ).count()
    return {"value": count, "label": _("Upcoming maintenance"), "tone": "neutral"}


def overdue_maintenance(context, config):
    """Count open interventions whose scheduled date has passed."""
    count = _maintenance_queryset(context, config).filter(scheduled_date__lt=timezone.localdate()).count()
    return {"value": count, "label": _("Overdue maintenance"), "tone": "danger" if count else "neutral"}
