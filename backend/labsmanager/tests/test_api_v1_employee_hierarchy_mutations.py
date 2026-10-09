"""Focused hierarchy mutation, visibility and graph checks."""

from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from staff.models import Employee, Employee_Superior


class EmployeeHierarchyMutationTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.editor = User.objects.create_user(username="hierarchy-editor")
        self.viewer = User.objects.create_user(username="hierarchy-viewer")
        view = Permission.objects.get(content_type__app_label="staff", codename="view_employee")
        change = Permission.objects.get(content_type__app_label="staff", codename="change_employee")
        self.editor.user_permissions.add(view, change)
        self.viewer.user_permissions.add(view)
        self.a = Employee.objects.create(first_name="Ada", last_name="Alpha")
        self.b = Employee.objects.create(first_name="Bea", last_name="Beta")
        self.c = Employee.objects.create(first_name="Cal", last_name="Gamma")
        self.client.force_authenticate(self.editor)

    def collection(self, employee):
        return f"/api/v1/employees/{employee.pk}/hierarchy/"

    def detail(self, employee, relation):
        return f"{self.collection(employee)}{relation.pk}/"

    def test_create_from_both_directions_is_one_logical_relation_and_duplicate_is_rejected(self):
        first = self.client.post(self.collection(self.b), {"direction": "superior", "employee_id": self.a.pk}, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        relation = Employee_Superior.objects.get(pk=first.data["id"])
        self.assertEqual((relation.superior_id, relation.employee_id), (self.a.pk, self.b.pk))
        self.assertEqual(self.client.get(self.collection(self.a)).data["subordinates"][0]["id"], relation.pk)
        duplicate = self.client.post(self.collection(self.a), {"direction": "subordinate", "employee_id": self.b.pk}, format="json")
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(duplicate.data["employee_id"], "duplicate")
        second = self.client.post(self.collection(self.b), {"direction": "subordinate", "employee_id": self.c.pk}, format="json")
        self.assertEqual(second.status_code, 201, second.data)
        self.assertTrue(Employee_Superior.objects.filter(superior=self.b, employee=self.c).exists())

    def test_self_relation_and_three_employee_cycle_are_rejected(self):
        self.assertEqual(self.client.post(self.collection(self.a), {"direction": "superior", "employee_id": self.a.pk}, format="json").status_code, 400)
        Employee_Superior.objects.create(superior=self.a, employee=self.b)
        Employee_Superior.objects.create(superior=self.b, employee=self.c)
        response = self.client.post(self.collection(self.a), {"direction": "superior", "employee_id": self.c.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["employee_id"], "cycle")
        self.assertEqual(Employee_Superior.objects.count(), 2)

    def test_read_only_cannot_mutate_and_superuser_can(self):
        relation = Employee_Superior.objects.create(superior=self.a, employee=self.b)
        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.get(self.collection(self.b)).data["capabilities"],
                         {"can_add": False, "can_change": False, "can_delete": False})
        self.assertEqual(self.client.post(self.collection(self.c), {"direction": "superior", "employee_id": self.a.pk}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.detail(self.b, relation)).status_code, 403)
        superuser = get_user_model().objects.create_superuser(username="hierarchy-super", email="s@example.test", password="test")
        self.client.force_authenticate(superuser)
        self.assertEqual(self.client.post(self.collection(self.c), {"direction": "superior", "employee_id": self.a.pk}, format="json").status_code, 201)

    def test_edit_dates_and_delete_use_the_existing_relation(self):
        relation = Employee_Superior.objects.create(superior=self.a, employee=self.b)
        end = (date.today() - timedelta(days=1)).isoformat()
        response = self.client.patch(self.detail(self.b, relation), {"start_date": "2020-01-01", "end_date": end}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        relation.refresh_from_db()
        self.assertEqual(relation.end_date.isoformat(), end)
        self.assertFalse(relation.is_active)
        self.assertEqual(self.client.get(self.collection(self.b)).data["superiors"][0]["id"], relation.pk)
        self.assertEqual(self.client.delete(self.detail(self.b, relation)).status_code, 204)
        self.assertFalse(Employee_Superior.objects.filter(pk=relation.pk).exists())

    def test_invisible_linked_employee_is_rejected(self):
        user = get_user_model().objects.create_user(username="hierarchy-self")
        self_perm = Permission.objects.get(content_type__app_label="common", codename="self_edit")
        user.user_permissions.add(self_perm)
        root = Employee.objects.create(first_name="Self", last_name="Editor", user=user)
        self.client.force_authenticate(user)
        response = self.client.post(self.collection(root), {"direction": "superior", "employee_id": self.a.pk}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_candidates_exclude_self_existing_relation_and_cycle(self):
        Employee_Superior.objects.create(superior=self.a, employee=self.b)
        Employee_Superior.objects.create(superior=self.b, employee=self.c)
        response = self.client.get(f"{self.collection(self.a)}candidates/?direction=superior")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])
        reverse = self.client.get(f"{self.collection(self.a)}candidates/?direction=subordinate")
        self.assertEqual([item["id"] for item in reverse.data["results"]], [self.c.pk])

    def test_superior_object_permission_obeys_existing_setting(self):
        user = get_user_model().objects.create_user(username="hierarchy-supervisor")
        user.user_permissions.add(Permission.objects.get(content_type__app_label="staff", codename="view_employee"))
        self.a.user = user
        self.a.save()
        Employee_Superior.objects.create(superior=self.a, employee=self.b)
        self.client.force_authenticate(user)
        with patch("staff.rules.LabsManagerSetting.get_setting", return_value=False):
            self.assertEqual(self.client.post(self.collection(self.b), {"direction": "subordinate", "employee_id": self.c.pk}, format="json").status_code, 403)
        with patch("staff.rules.LabsManagerSetting.get_setting", return_value=True):
            response = self.client.post(self.collection(self.b), {"direction": "subordinate", "employee_id": self.c.pk}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
