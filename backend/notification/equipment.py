"""Scheduled Equipment maintenance notices using the existing user notifications."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from common.models import subscription
from equipment.api_v1 import visible_equipment
from equipment.maintenance_api_v1 import maintenance_capabilities
from equipment.models import Equipment, EquipmentMaintenance, EquipmentResponsibility
from settings.models import LMUserSetting

from .models import UserNotification
from .utils import check_enabled_notification_user


def check_equipment_maintenance():
    """Queue one notice per visible recipient, maintenance, and scheduled date.

    The ISO date in ``message`` is the existing notification row's deadline
    identity. A pending notice for an old date is removed when rescheduled;
    delivered rows remain as history. Locking the maintenance serializes
    concurrent runs without adding a second history table.
    """
    today = timezone.localdate()
    maintenance_type = ContentType.objects.get_for_model(EquipmentMaintenance)
    equipment_type = ContentType.objects.get_for_model(Equipment)
    count = 0

    for maintenance_id in EquipmentMaintenance.objects.values_list("pk", flat=True):
        with transaction.atomic():
            maintenance = EquipmentMaintenance.objects.select_for_update().select_related("equipment").get(pk=maintenance_id)
            pending = UserNotification.objects.filter(
                source_content_type=maintenance_type,
                source_object_id=maintenance.pk,
                send__isnull=True,
            )
            if maintenance.status not in (EquipmentMaintenance.Status.PLANNED, EquipmentMaintenance.Status.IN_PROGRESS):
                pending.delete()
                continue

            deadline = maintenance.scheduled_date.isoformat()
            responsibility_ids = EquipmentResponsibility.objects.filter(
                equipment_id=maintenance.equipment_id,
            ).filter(
                (Q(start_date__isnull=True) | Q(start_date__lte=today))
                & (Q(end_date__isnull=True) | Q(end_date__gte=today))
            ).filter(employee__is_active=True).exclude(employee__user__isnull=True).values_list("employee__user_id", flat=True)
            subscriber_ids = subscription.objects.filter(
                content_type=equipment_type, object_id=maintenance.equipment_id,
            ).values_list("user_id", flat=True)
            users = get_user_model().objects.filter(
                pk__in=set(responsibility_ids) | set(subscriber_ids), is_active=True,
            )
            eligible_users = []
            for user in users:
                if not maintenance_capabilities(user)["can_view"] and not user.is_staff:
                    continue
                if not visible_equipment(user).filter(pk=maintenance.equipment_id).exists():
                    continue
                if not check_enabled_notification_user(user, maintenance_type):
                    continue
                eligible_users.append(user)

            # Pending mail must not retain a stale date or a revoked recipient.
            pending.exclude(message=deadline, user_id__in=[user.pk for user in eligible_users]).delete()

            for user in eligible_users:
                advance = LMUserSetting.get_setting("EQUIPMENT_MAINTENANCE_ADVANCE_DAYS", user=user)
                if maintenance.scheduled_date > today + timedelta(days=advance):
                    continue
                action = "ove" if maintenance.scheduled_date < today else "sta"
                # The deadline, rather than action, is the identity: a notice
                # due today must not repeat as an overdue notice tomorrow.
                if UserNotification.objects.filter(
                    user=user, source_content_type=maintenance_type,
                    source_object_id=maintenance.pk, message=deadline,
                ).exists():
                    continue
                UserNotification.objects.create(
                    user=user, source_content_type=maintenance_type,
                    source_object_id=maintenance.pk, action_type=action, message=deadline,
                )
                count += 1

    return count
