from datetime import date
from unittest.mock import patch

from auditlog.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from leave.calendar import leave_to_calendar_event
from leave.models import Leave, Leave_Type
from staff.models import Employee, Employee_Superior


class LeaveOverlapTests(TestCase):
    def setUp(self):
        self.employee = Employee.objects.create(first_name="A", last_name="One")
        self.other_employee = Employee.objects.create(first_name="B", last_name="Two")
        self.type = Leave_Type.objects.create(name="Annual", short_name="AN")
        self.other_type = Leave_Type.objects.create(name="Sick", short_name="SI")

    def leave(self, **overrides):
        values = dict(employee=self.employee, type=self.type, start_date=date(2026, 9, 24), end_date=date(2026, 9, 24), start_period="ST", end_period="MI")
        values.update(overrides)
        instance = Leave(**values)
        instance.full_clean()
        instance.save()
        return instance

    def test_half_days_can_touch_but_not_overlap(self):
        self.leave()
        self.leave(start_period="MI", end_period="EN")
        with self.assertRaises(ValidationError):
            self.leave(start_period="ST", end_period="EN")
        self.leave(type=self.other_type, start_period="ST", end_period="EN")
        self.leave(employee=self.other_employee, start_period="ST", end_period="EN")

    def test_invalid_period_and_date_order(self):
        with self.assertRaises(ValidationError):
            self.leave(start_period="MI", end_period="MI")
        with self.assertRaises(ValidationError):
            self.leave(start_date=date(2026, 9, 25), end_date=date(2026, 9, 24))


class EmployeeLeaveMutationApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="leave-editor", password="test-password")
        self.employee = Employee.objects.create(first_name="Leave", last_name="Editor", user=self.user)
        self.other = Employee.objects.create(first_name="Other", last_name="Person")
        self.type = Leave_Type.objects.create(name="Annual", short_name="AN", color="#336699")
        self.child_type = Leave_Type.objects.create(name="RTT", short_name="RTT", parent=self.type)
        self.leave = Leave.objects.create(employee=self.employee, type=self.type, start_date=date(2026, 9, 10), end_date=date(2026, 9, 10))
        self.list_url = reverse("api_v1:employee-leaves", kwargs={"pk": self.employee.pk})
        self.detail_url = reverse("api_v1:employee-leave-detail", kwargs={"pk": self.employee.pk, "leave_id": self.leave.pk})
        self.cap_url = reverse("api_v1:employee-leave-capabilities", kwargs={"pk": self.employee.pk})
        self.payload = {"type_id": self.type.pk, "start_date": "2026-09-24", "start_period": "ST", "end_date": "2026-09-24", "end_period": "MI", "comment": "Morning"}
        self.client.force_login(self.user)

    def grant_change(self):
        permission = Permission.objects.get(content_type__app_label="staff", codename="change_employee")
        self.user.user_permissions.add(permission)
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def test_view_only_can_read_but_cannot_mutate(self):
        self.assertEqual(self.client.get(self.list_url).status_code, 200)
        self.assertEqual(self.client.get(self.cap_url).json(), {"can_add": False, "can_change": False, "can_delete": False})
        self.assertEqual(self.client.post(self.list_url, self.payload).status_code, 403)
        self.assertEqual(self.client.patch(self.detail_url, {"comment": "Changed"}).status_code, 403)
        self.assertEqual(self.client.delete(self.detail_url).status_code, 403)

    def test_global_change_crud_audit_and_context(self):
        self.grant_change()
        self.assertEqual(self.client.get(self.cap_url).json(), {"can_add": True, "can_change": True, "can_delete": True})
        created = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(created.status_code, 201)
        pk = created.json()["id"]
        self.assertEqual(Leave.objects.get(pk=pk).employee_id, self.employee.pk)
        self.assertEqual(created.json()["day_count"], 0.5)
        detail = reverse("api_v1:employee-leave-detail", kwargs={"pk": self.employee.pk, "leave_id": pk})
        changed = self.client.patch(detail, {"type_id": self.child_type.pk, "comment": "Updated"}, format="json")
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.json()["type"]["id"], self.child_type.pk)
        self.assertEqual(self.client.delete(detail).status_code, 204)
        self.assertFalse(Leave.objects.filter(pk=pk).exists())
        self.assertTrue(LogEntry.objects.filter(object_pk=str(pk), content_type__app_label="leave", actor=self.user).exists())

    def test_invalid_type_dates_overlap_and_payload_employee(self):
        self.grant_change()
        self.assertEqual(self.client.post(self.list_url, {**self.payload, "employee": self.other.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.list_url, {**self.payload, "type_id": 999999}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.list_url, {**self.payload, "start_date": None}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.list_url, {**self.payload, "start_period": "MI", "end_period": "MI"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.list_url, self.payload, format="json").status_code, 201)
        self.assertEqual(self.client.post(self.list_url, {**self.payload, "end_period": "EN"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.list_url, {**self.payload, "start_period": "MI", "end_period": "EN"}, format="json").status_code, 201)
        self.assertEqual(self.client.patch(self.detail_url, {"comment": "Unchanged dates"}, format="json").status_code, 200)

    def test_other_employee_is_hidden_and_catalogue_is_hierarchical(self):
        other_leave = Leave.objects.create(employee=self.other, type=self.type, start_date=date(2026, 9, 20), end_date=date(2026, 9, 20))
        self.grant_change()
        url = reverse("api_v1:employee-leave-detail", kwargs={"pk": self.employee.pk, "leave_id": other_leave.pk})
        self.assertEqual(self.client.patch(url, {"comment": "No"}).status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        catalogue = self.client.get(reverse("api_v1:leave-types")).json()
        self.assertEqual([(item["id"], item["depth"]) for item in catalogue], [(self.type.pk, 0), (self.child_type.pk, 1)])

    def test_csrf_and_calendar_core_conversion(self):
        strict = APIClient(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post(self.list_url, self.payload, format="json").status_code, 403)
        event = leave_to_calendar_event(self.leave)
        self.assertEqual(event.kind, "leave")
        self.assertEqual(event.metadata["leave_id"], self.leave.pk)
        self.assertTrue(event.all_day)

    def test_self_edit_and_superior_use_existing_change_rule(self):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="common", codename="self_edit"))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        self.assertTrue(self.client.get(self.cap_url).json()["can_change"])
        self.assertEqual(self.client.post(self.list_url, self.payload, format="json").status_code, 201)

        Employee_Superior.objects.create(employee=self.other, superior=self.employee)
        other_url = reverse("api_v1:employee-leaves", kwargs={"pk": self.other.pk})
        other_caps = reverse("api_v1:employee-leave-capabilities", kwargs={"pk": self.other.pk})
        with patch("staff.rules.LabsManagerSetting.get_setting", return_value=True):
            self.assertTrue(self.client.get(other_caps).json()["can_change"])
            self.assertEqual(self.client.post(other_url, self.payload, format="json").status_code, 201)
