"""R2.7 contextual mutations, validation and session audit."""
from unittest.mock import patch
from auditlog.models import LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase
from staff.models import Employee, Employee_Superior, GenericInfo, GenericInfoType


@override_settings(CSRF_COOKIE_SECURE=False, SESSION_COOKIE_SECURE=False, SECURE_SSL_REDIRECT=False)
class GenericInfoMutationTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="info-user", password="password")
        self.employee = Employee.objects.create(first_name="Own", last_name="Profile", user=self.user)
        self.other = Employee.objects.create(first_name="Other", last_name="Profile")
        self.type = GenericInfoType.objects.create(name="Badge", icon="Badge")
        self.info = GenericInfo.objects.create(employee=self.employee, info=self.type, value="before")
        self.url = f"/api/v1/employees/{self.employee.pk}/generic-info/"
        self.detail = f"{self.url}{self.info.pk}/"
        self.client.force_login(self.user)

    def grant(self, app, codename):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
        for key in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(key, None)

    def capabilities(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        return response.json()["capabilities"]

    def test_self_without_self_edit_can_only_create(self):
        self.assertTrue(self.user.has_perm("staff.change_partial_employee", self.employee))
        self.assertFalse(self.user.has_perm("staff.change_employee", self.employee))
        self.assertEqual(self.capabilities(), dict(can_add=True, can_change=False, can_delete=False))
        self.assertEqual(self.client.patch(self.detail, {"value": "new"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.detail).status_code, 403)
        response = self.client.post(self.url, {"type_id": self.type.pk, "value": "new"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["type"]["id"], self.type.pk)
        self.assertEqual(GenericInfo.objects.get(pk=response.json()["id"]).employee_id, self.employee.pk)

    def test_self_edit_preserves_full_historical_change(self):
        self.grant("common", "self_edit")
        self.assertTrue(self.user.has_perm("staff.change_employee", self.employee))
        self.assertEqual(self.capabilities(), dict(can_add=True, can_change=True, can_delete=True))
        self.assertEqual(self.client.patch(self.detail, {"value": "changed"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(self.detail).status_code, 204)

    def test_global_change_without_self_edit(self):
        self.grant("staff", "view_employee")
        self.grant("staff", "change_employee")
        self.url = f"/api/v1/employees/{self.other.pk}/generic-info/"
        self.assertEqual(self.capabilities(), dict(can_add=True, can_change=True, can_delete=True))
        self.assertTrue(self.user.has_perm("staff.change_partial_employee", self.other))
        self.assertEqual(self.client.post(self.url, {"type_id": self.type.pk}, format="json").status_code, 201)
        self.assertEqual(self.client.patch(self.detail, {"value": "global"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(self.detail).status_code, 204)

    def test_reader_has_no_mutations(self):
        reader = get_user_model().objects.create_user(username="reader")
        reader.user_permissions.add(Permission.objects.get(content_type__app_label="staff", codename="view_employee"))
        self.client.force_login(reader)
        self.assertEqual(self.capabilities(), dict(can_add=False, can_change=False, can_delete=False))
        self.assertEqual(self.client.post(self.url, {"type_id": self.type.pk}, format="json").status_code, 403)
        self.assertEqual(self.client.patch(self.detail, {"value": "no"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.detail).status_code, 403)

    def test_hierarchy_reuses_rule_and_setting(self):
        Employee_Superior.objects.create(employee=self.other, superior=self.employee)
        self.url = f"/api/v1/employees/{self.other.pk}/generic-info/"
        for enabled in (False, True):
            with self.subTest(enabled=enabled), patch("staff.rules.LabsManagerSetting.get_setting", return_value=enabled):
                self.assertEqual(self.capabilities(), dict(can_add=enabled, can_change=enabled, can_delete=enabled))
                response = self.client.post(self.url, {"type_id": self.type.pk}, format="json")
                self.assertEqual(response.status_code, 201 if enabled else 403)
                if enabled:
                    url = f'{self.url}{response.json()["id"]}/'
                    self.assertEqual(self.client.patch(url, {"value": "hierarchy"}, format="json").status_code, 200)
                    self.assertEqual(self.client.delete(url).status_code, 204)

    def test_parent_visibility_and_child_ownership(self):
        for url in (f"/api/v1/employees/{self.other.pk}/generic-info/", "/api/v1/employees/999999/generic-info/"):
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {"type_id": self.type.pk}, format="json").status_code, 404)
        child = GenericInfo.objects.create(employee=self.other, info=self.type)
        self.grant("staff", "change_employee")
        wrong = f"{self.url}{child.pk}/"
        self.assertEqual(self.client.patch(wrong, {"value": "no"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(wrong).status_code, 404)

    def test_optional_values_and_duplicates(self):
        for data in ({"value": ""}, {"value": None}, {}, {"value": "x" * 150}):
            response = self.client.post(self.url, {"type_id": self.type.pk, **data}, format="json")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["value"], data.get("value"))
        self.assertEqual(GenericInfo.objects.filter(employee=self.employee, info=self.type).count(), 5)

    def test_invalid_create_and_parent_injection(self):
        for payload, field in [
            ({"type_id": 999999}, "type_id"), ({}, "type_id"),
            ({"type_id": self.type.pk, "value": "x" * 151}, "value"),
            ({"type_id": self.type.pk, "employee": self.other.pk}, "employee"),
            ({"type_id": self.type.pk, "employee_id": self.other.pk}, "employee_id"),
        ]:
            response = self.client.post(self.url, payload, format="json")
            self.assertEqual(response.status_code, 400)
            self.assertIn(field, response.json())
        self.assertEqual(GenericInfo.objects.count(), 1)

    def test_patch_only_value_and_immutable_type(self):
        self.grant("common", "self_edit")
        for field in ("type_id", "info", "type", "employee", "employee_id"):
            response = self.client.patch(self.detail, {field: self.type.pk, "value": "no"}, format="json")
            self.assertEqual(response.status_code, 400)
            self.assertIn(field, response.json())
        self.info.refresh_from_db()
        self.assertEqual(self.info.value, "before")
        self.assertEqual(self.client.patch(self.detail, {"value": "x" * 151}, format="json").status_code, 400)
        for value in ("", None, "  text <plain>  "):
            response = self.client.patch(self.detail, {"value": value}, format="json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["value"], value)
        self.assertEqual(self.client.put(self.detail, {"value": "no"}, format="json").status_code, 405)

    def test_empty_envelope_and_global_read_only_catalogue(self):
        self.info.delete()
        self.assertEqual(self.client.get(self.url).json(), {"capabilities": dict(can_add=True, can_change=False, can_delete=False), "items": []})
        url = "/api/v1/generic-info-types/"
        self.assertEqual(self.client.get(url).json(), [{"id": self.type.pk, "name": "Badge", "icon": "Badge"}])
        for method in (self.client.post, self.client.patch, self.client.delete):
            self.assertEqual(method(url, {"name": "no"}, format="json").status_code, 405)

    def test_authentication_and_csrf(self):
        self.client.logout()
        for url in (self.url, "/api/v1/generic-info-types/"):
            self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.post(self.url, {"type_id": self.type.pk}, format="json").status_code, 401)
        self.grant("common", "self_edit")
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.url, {"type_id": self.type.pk}, format="json").status_code, 403)
        self.assertEqual(client.patch(self.detail, {"value": "no"}, format="json").status_code, 403)
        self.assertEqual(client.delete(self.detail).status_code, 403)
        client.get("/api/v1/me/")
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post(self.url, {"type_id": self.type.pk}, format="json", HTTP_X_CSRFTOKEN=token).status_code, 201)

    def test_audit_records_write_actions_and_session_actor(self):
        self.grant("common", "self_edit")
        response = self.client.post(self.url, {"type_id": self.type.pk, "value": "audit"}, format="json")
        self.assertEqual(response.status_code, 201)
        pk = response.json()["id"]
        item = GenericInfo.objects.get(pk=pk)
        url = f"{self.url}{pk}/"
        self.client.patch(url, {"value": "after"}, format="json")
        self.client.delete(url)
        logs = LogEntry.objects.get_for_object(item)
        self.assertEqual(set(logs.values_list("action", flat=True)), {LogEntry.Action.CREATE, LogEntry.Action.UPDATE, LogEntry.Action.DELETE})
        self.assertEqual(set(logs.values_list("actor_id", flat=True)), {self.user.pk})
