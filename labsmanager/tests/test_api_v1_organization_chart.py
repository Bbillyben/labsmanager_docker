"""R2.26a graph visibility, history, user scope and malformed hierarchies."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from settings.models import LMUserSetting
from staff.models import Employee, Employee_Status, Employee_Superior, Employee_Type


class OrganizationChartV1Tests(APITestCase):
    url = "/api/v1/organization-chart/"

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="chart-viewer")
        self.other_user = get_user_model().objects.create_user(username="other-viewer")
        self.root = Employee.objects.create(first_name="Ada", last_name="Root", user=self.user)
        self.child = Employee.objects.create(first_name="Bea", last_name="Child")
        self.second = Employee.objects.create(first_name="Cal", last_name="Second")
        self.hidden = Employee.objects.create(first_name="Secret", last_name="Person")
        self.inactive = Employee.objects.create(first_name="Dan", last_name="Former", is_active=False)
        self.today = date.today()
        self.current = Employee_Superior.objects.create(superior=self.root, employee=self.child)
        self.past = Employee_Superior.objects.create(superior=self.child, employee=self.inactive, end_date=self.today - timedelta(days=1))
        Employee_Superior.objects.create(superior=self.second, employee=self.child)
        Employee_Superior.objects.create(superior=self.hidden, employee=self.second)
        kind = Employee_Type.objects.create(shortname="ENG", name="Engineer")
        Employee_Status.objects.create(employee=self.child, type=kind)
        self.client.force_login(self.user)

    def grant_global_view(self):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="staff", codename="view_employee"))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def test_default_current_scope_hides_invisible_edges_and_inactive_employees(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["show_current_only"])
        self.assertEqual({row["id"] for row in response.data["employees"]}, {self.root.pk, self.child.pk})
        self.assertEqual(response.data["relationships"], [{"superior_id": self.root.pk, "employee_id": self.child.pk}])
        self.assertEqual(response.data["employees"][1]["statuses"], [{"code": "ENG", "name": "Engineer"}])

    def test_global_view_preserves_two_superiors_and_current_vs_history(self):
        self.grant_global_view()
        current = self.client.get(self.url).data
        self.assertEqual(len([edge for edge in current["relationships"] if edge["employee_id"] == self.child.pk]), 2)
        self.assertNotIn(self.inactive.pk, {row["id"] for row in current["employees"]})
        self.assertEqual(self.client.patch(self.url, {"show_current_only": False}, format="json").status_code, 200)
        historical = self.client.get(self.url).data
        self.assertFalse(historical["show_current_only"])
        self.assertIn(self.inactive.pk, {row["id"] for row in historical["employees"]})
        self.assertIn({"superior_id": self.child.pk, "employee_id": self.inactive.pk}, historical["relationships"])
        self.assertFalse(LMUserSetting.get_setting("SHOW_PAST_ORG", user=self.user))

    def test_scope_is_per_user_and_rejects_non_boolean(self):
        self.assertEqual(self.client.patch(self.url, {"show_current_only": "false"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.url, {"show_current_only": False}, format="json").status_code, 200)
        self.assertTrue(LMUserSetting.get_setting("SHOW_PAST_ORG", user=self.other_user))

    def test_cycle_returns_controlled_error(self):
        self.grant_global_view()
        Employee_Superior.objects.create(superior=self.child, employee=self.inactive)
        Employee_Superior.objects.create(superior=self.inactive, employee=self.root)
        self.client.patch(self.url, {"show_current_only": False}, format="json")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["detail"], "hierarchy_cycle")

    def test_anonymous_user_is_rejected(self):
        self.client.logout()
        self.assertIn(self.client.get(self.url).status_code, (401, 403))
