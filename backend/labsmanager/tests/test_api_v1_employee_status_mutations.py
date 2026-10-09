"""Targeted Employee status CRUD and historical response checks."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from staff.models import Employee, Employee_Status, Employee_Type


class EmployeeStatusMutationTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.editor = User.objects.create_user(username="status-editor")
        self.viewer = User.objects.create_user(username="status-viewer")
        view = Permission.objects.get(content_type__app_label="staff", codename="view_employee")
        change = Permission.objects.get(content_type__app_label="staff", codename="change_employee")
        self.editor.user_permissions.add(view, change)
        self.viewer.user_permissions.add(view)
        self.employee = Employee.objects.create(first_name="Ada", last_name="Alpha")
        self.other = Employee.objects.create(first_name="Bea", last_name="Beta")
        self.kind = Employee_Type.objects.create(shortname="ENG", name="Engineer")
        self.client.force_authenticate(self.editor)

    def collection(self, employee=None):
        return f"/api/v1/employees/{(employee or self.employee).pk}/statuses/"

    def detail(self, status, employee=None):
        return f"{self.collection(employee)}{status.pk}/"

    def test_get_preserves_current_and_previous_and_exposes_capabilities_separately(self):
        current = Employee_Status.objects.create(employee=self.employee, type=self.kind)
        previous = Employee_Status.objects.create(employee=self.employee, type=self.kind, start_date=date(2020, 1, 1), end_date=date(2021, 1, 1))
        response = self.client.get(self.collection())
        self.assertEqual(response.status_code, 200)
        self.assertEqual({item["id"]: item["is_active"] for item in response.data}, {current.pk: True, previous.pk: False})
        options = self.client.get(f"{self.collection()}options/")
        self.assertEqual(options.data["capabilities"], {"can_add": True, "can_change": True, "can_delete": True})
        self.assertEqual(options.data["types"][0]["id"], self.kind.pk)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get(f"{self.collection()}options/").data["capabilities"], {"can_add": False, "can_change": False, "can_delete": False})

    def test_create_and_edit_preserve_type_and_reclassify_dates(self):
        response = self.client.post(self.collection(), {"type": self.kind.pk, "start_date": "2020-01-01", "is_contractual": "s"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        status = Employee_Status.objects.get(pk=response.data["id"])
        self.assertEqual(status.is_contractual, "s")
        self.assertTrue(status.is_active)
        end_date = (date.today() - timedelta(days=1)).isoformat()
        response = self.client.patch(self.detail(status), {"end_date": end_date}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["is_active"])
        self.assertFalse(next(item for item in self.client.get(self.collection()).data if item["id"] == status.pk)["is_active"])
        self.assertEqual(self.client.patch(self.detail(status), {"type": self.kind.pk}, format="json").status_code, 400)
        status.refresh_from_db()
        self.assertEqual(status.type_id, self.kind.pk)

    def test_validation_rejects_invalid_dates_type_and_payload_employee(self):
        self.assertEqual(self.client.post(self.collection(), {"type": 999999}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.collection(), {"type": self.kind.pk, "end_date": "2024-01-01"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.collection(), {"type": self.kind.pk, "start_date": "2025-01-01", "end_date": "2024-01-01"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.collection(), {"type": self.kind.pk, "employee_id": self.other.pk}, format="json").status_code, 400)
        self.assertEqual(Employee_Status.objects.count(), 0)

    def test_foreign_status_is_not_found_and_delete_is_physical(self):
        foreign = Employee_Status.objects.create(employee=self.other, type=self.kind)
        self.assertEqual(self.client.patch(self.detail(foreign), {"end_date": None}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(self.detail(foreign)).status_code, 404)
        self.assertEqual(self.client.delete(self.detail(foreign, self.other)).status_code, 204)
        self.assertFalse(Employee_Status.objects.filter(pk=foreign.pk).exists())

    def test_read_only_user_cannot_mutate(self):
        status = Employee_Status.objects.create(employee=self.employee, type=self.kind)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post(self.collection(), {"type": self.kind.pk}, format="json").status_code, 403)
        self.assertEqual(self.client.patch(self.detail(status), {"end_date": None}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.detail(status)).status_code, 403)

    def test_superuser_can_mutate(self):
        superuser = get_user_model().objects.create_superuser(username="status-super", email="status@example.test", password="test")
        self.client.force_authenticate(superuser)
        response = self.client.post(self.collection(), {"type": self.kind.pk}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
