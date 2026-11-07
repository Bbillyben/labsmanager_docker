"""Focused coverage for scheduled Equipment maintenance notifications."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.sites.models import Site
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from common.models import subscription
from equipment.models import Equipment, EquipmentCategory, EquipmentMaintenance, EquipmentResponsibility
from notification.equipment import check_equipment_maintenance
from notification.mails import NotificationMail
from notification.models import UserNotification
from settings.models import LMUserSetting
from staff.models import Employee


@override_settings(REACT_PUBLIC_URL="https://labs.example/app", SITE_ID=1)
class EquipmentMaintenanceNotificationTests(TestCase):
    def setUp(self):
        Site.objects.update_or_create(pk=1, defaults={"domain": "labs.example", "name": "LabsManager"})
        category = EquipmentCategory.objects.create(name="Test category")
        self.equipment = Equipment.objects.create(name="Microscope", internal_reference="EQ-N-1", category=category)
        self.today = timezone.localdate()
        self.maintenance = EquipmentMaintenance.objects.create(
            equipment=self.equipment, title="Annual check", maintenance_type="inspection",
            scheduled_date=self.today + timedelta(days=5),
        )
        self.reader = self.make_user("reader")

    def make_user(self, name, *, view=True, maintenance=True, active=True):
        user = get_user_model().objects.create_user(username=name, is_active=active)
        codes = []
        if view:
            codes.append("view_equipment")
        if maintenance:
            codes.append("view_equipmentmaintenance")
        user.user_permissions.add(*Permission.objects.filter(content_type__app_label="equipment", codename__in=codes))
        return user

    def subscribe(self, user):
        from django.contrib.contenttypes.models import ContentType
        subscription.objects.create(user=user, content_type=ContentType.objects.get_for_model(Equipment), object_id=self.equipment.pk)

    def responsible(self, user, **dates):
        employee = Employee.objects.create(first_name=user.username, last_name="Reader", user=user)
        return EquipmentResponsibility.objects.create(equipment=self.equipment, employee=employee, **dates)

    def notes(self, user):
        return UserNotification.objects.filter(user=user, source_object_id=self.maintenance.pk,
                                               source_content_type__app_label="equipment",
                                               source_content_type__model="equipmentmaintenance")

    def test_responsible_subscriber_dedup_and_permissions(self):
        self.responsible(self.reader)
        self.subscribe(self.reader)
        responsible_only = self.make_user("responsible-only")
        self.responsible(responsible_only)
        subscriber = self.make_user("subscriber")
        self.subscribe(subscriber)
        inactive = self.make_user("inactive", active=False)
        self.subscribe(inactive)
        hidden = self.make_user("hidden", maintenance=False)
        self.subscribe(hidden)
        no_equipment = self.make_user("no-equipment", view=False)
        self.subscribe(no_equipment)
        ended = self.make_user("ended")
        self.responsible(ended, end_date=self.today - timedelta(days=1))
        future = self.make_user("future")
        self.responsible(future, start_date=self.today + timedelta(days=1))
        self.assertEqual(check_equipment_maintenance(), 3)
        self.assertEqual(self.notes(self.reader).count(), 1)
        self.assertEqual(self.notes(responsible_only).count(), 1)
        self.assertEqual(self.notes(subscriber).count(), 1)
        for user in (inactive, hidden, no_equipment, ended, future):
            self.assertFalse(self.notes(user).exists())
        self.assertEqual(check_equipment_maintenance(), 0)

    def test_individual_advance_and_zero(self):
        self.subscribe(self.reader)
        zero = self.make_user("zero")
        self.subscribe(zero)
        LMUserSetting.objects.create(user=zero, key="EQUIPMENT_MAINTENANCE_ADVANCE_DAYS", value="0")
        self.assertEqual(check_equipment_maintenance(), 1)  # Default seven days.
        self.notes(self.reader).update(send=timezone.now())
        self.maintenance.scheduled_date = self.today
        self.maintenance.save()
        self.assertEqual(check_equipment_maintenance(), 2)
        self.assertEqual(self.notes(zero).count(), 1)
        self.assertEqual(self.notes(self.reader).count(), 2)

    def test_overdue_once_reschedule_and_closed(self):
        self.subscribe(self.reader)
        self.maintenance.scheduled_date = self.today - timedelta(days=2)
        self.maintenance.save()
        self.assertEqual(check_equipment_maintenance(), 1)
        self.assertEqual(self.notes(self.reader).first().action_type, "ove")
        self.assertEqual(check_equipment_maintenance(), 0)
        self.notes(self.reader).update(send=timezone.now())
        self.maintenance.scheduled_date = self.today + timedelta(days=1)
        self.maintenance.save()
        self.assertEqual(check_equipment_maintenance(), 1)
        self.maintenance.status = EquipmentMaintenance.Status.CANCELLED
        self.maintenance.save()
        self.assertEqual(check_equipment_maintenance(), 0)
        self.assertEqual(self.notes(self.reader).filter(send__isnull=True).count(), 0)
        self.maintenance.status = EquipmentMaintenance.Status.COMPLETED
        self.maintenance.performed_date = self.today
        self.maintenance.save()
        self.assertEqual(check_equipment_maintenance(), 0)

    def test_rescheduling_removes_unsent_old_date(self):
        self.subscribe(self.reader)
        self.assertEqual(check_equipment_maintenance(), 1)
        self.maintenance.scheduled_date = self.today + timedelta(days=20)
        self.maintenance.save()
        self.assertEqual(check_equipment_maintenance(), 0)
        self.assertFalse(self.notes(self.reader).exists())

    def test_setting_rejects_negative_and_excessive_values(self):
        for value in ("-1", "366"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                LMUserSetting(user=self.reader, key="EQUIPMENT_MAINTENANCE_ADVANCE_DAYS", value=value).save()

    def test_in_progress_and_disabled_preference(self):
        self.subscribe(self.reader)
        self.maintenance.status = EquipmentMaintenance.Status.IN_PROGRESS
        self.maintenance.save()
        LMUserSetting.objects.create(
            user=self.reader, key="NOTIFICATION_EQUIPMENT_EQUIPMENTMAINTENANCE", value="False"
        )
        self.assertEqual(check_equipment_maintenance(), 0)
        LMUserSetting.objects.filter(
            user=self.reader, key="NOTIFICATION_EQUIPMENT_EQUIPMENTMAINTENANCE"
        ).update(value="True")
        self.assertEqual(check_equipment_maintenance(), 1)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_mail_renders_source_before_delivery(self):
        self.subscribe(self.reader)
        self.assertEqual(check_equipment_maintenance(), 1)
        with patch("plugin.registry.registry.with_mixin", return_value=[]), patch(
            "plugin.templatetags.plugin_tags.registry.with_mixin", return_value=[]
        ):
            notice_mail = NotificationMail()
            notice_mail.generate_context(user=self.reader.pk)
            html = notice_mail.render_html(user=self.reader)
        self.assertIn("Annual check", html)
        self.assertIn("Microscope", html)
        self.assertIn(f"https://labs.example/app/equipment/{self.equipment.pk}/maintenance", html)
        self.assertIsNone(self.notes(self.reader).first().send)
        with patch("plugin.registry.registry.with_mixin", return_value=[]), patch(
            "plugin.templatetags.plugin_tags.registry.with_mixin", return_value=[]
        ):
            self.assertEqual(NotificationMail().send("reader@example.test", user=self.reader.pk, embedImg=True), 1)
        self.assertIn("Annual check", mail.outbox[-1].alternatives[0][0])
