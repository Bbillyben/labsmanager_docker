"""Limited Employee Planning milestone permissions and writes."""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework.test import APITestCase

from endpoints.models import MilestoneDependency, Milestones
from project.models import Participant, Project
from settings.models import LMProjectSetting
from staff.models import Employee


class EmployeeMilestoneMutationV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="assigned-editor", password="test")
        self.employee = Employee.objects.create(first_name="Assigned", last_name="Editor", user=self.user)
        self.project = Project.objects.create(name="Limited Planning")
        self.item = Milestones.objects.create(
            project=self.project, name="A milestone", desc="Before", type="q",
            quotity=Decimal("0.250"), status=False,
        )
        self.item.employee.add(self.employee)
        self.client.force_login(self.user)

    def collection(self, employee=None):
        return reverse("api_v1:employee-milestones", kwargs={"pk": (employee or self.employee).pk})

    def detail(self, item=None, employee=None):
        return reverse("api_v1:employee-milestone-detail", kwargs={
            "pk": (employee or self.employee).pk, "item_id": (item or self.item).pk,
        })

    def capability(self, employee=None):
        return self.client.get(self.collection(employee)).json()[0]["can_change"]

    def test_capability_uses_rule_for_assignee_setting_and_project_owner(self):
        self.assertTrue(self.capability())
        setting = LMProjectSetting.objects.get(project=self.project, key="EMPLOYEE_EDIT_MILESTONE")
        setting.value = "False"
        setting.save()
        self.assertFalse(self.capability())

        owner = get_user_model().objects.create_user(username="project-owner", password="test")
        owner_employee = Employee.objects.create(first_name="Project", last_name="Owner", user=owner)
        Participant.objects.create(project=self.project, employee=owner_employee, status="l")
        owner.user_permissions.add(Permission.objects.get(content_type__app_label="staff", codename="view_employee"))
        self.client.force_login(owner)
        self.assertTrue(self.capability())
        self.assertEqual(self.client.patch(self.detail(), {"desc": "Owner edit"}, format="json").status_code, 200)

    def test_partial_patch_saves_only_allowed_fields_and_retains_project_progress_semantics(self):
        original = Milestones.save
        with patch.object(Milestones, "save", autospec=True, side_effect=original) as save:
            response = self.client.patch(self.detail(), {
                "desc": "After", "quotity": "0.750", "status": False,
            }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(save.call_count, 1)
        self.assertEqual(response.json()["desc"], "After")
        self.assertEqual(response.json()["quotity"], "0.750")
        self.assertFalse(response.json()["status"])
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, "A milestone")
        self.assertEqual(self.item.project, self.project)
        self.assertEqual(self.item.quotity, Decimal("0.750"))
        self.assertEqual(self.client.patch(self.detail(), {"status": True}, format="json").json()["quotity"], "1.000")
        self.assertTrue(self.client.patch(self.detail(), {"quotity": "1.000", "status": False}, format="json").json()["status"])
        self.assertEqual(self.client.patch(self.detail(), {"quotity": "1.500"}, format="json").status_code, 400)

    def test_denies_unknown_fields_create_delete_and_dependency_changes(self):
        forbidden = {
            "name": "Changed", "start_date": "2026-10-01", "end_date": "2026-11-01",
            "project": self.project.pk, "employee_ids": [], "type": "o", "dependencies": [],
        }
        for field, value in forbidden.items():
            with self.subTest(field=field):
                response = self.client.patch(self.detail(), {field: value}, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())
        self.assertEqual(self.client.post(self.collection(), {"name": "New"}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(self.detail()).status_code, 405)
        self.assertEqual(self.client.patch(self.detail(), {"predecessor_ids": []}, format="json").status_code, 400)
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, "A milestone")

    def test_viewer_of_other_employee_cannot_mutate_without_rule_and_scope_is_bounded(self):
        reader = get_user_model().objects.create_user(username="other-reader", password="test")
        Employee.objects.create(first_name="Other", last_name="Reader", user=reader)
        reader.user_permissions.add(Permission.objects.get(content_type__app_label="staff", codename="view_employee"))
        self.client.force_login(reader)
        self.assertFalse(self.capability())
        self.assertEqual(self.client.patch(self.detail(), {"desc": "Forbidden"}, format="json").status_code, 403)
        hidden = Employee.objects.create(first_name="Hidden", last_name="Employee")
        self.assertEqual(self.client.get(self.collection(hidden)).status_code, 200)
        self.assertEqual(self.client.patch(self.detail(employee=hidden), {"desc": "Hidden"}, format="json").status_code, 404)

        unlinked = get_user_model().objects.create_user(username="unlinked-reader", password="test")
        unlinked.user_permissions.add(Permission.objects.get(content_type__app_label="staff", codename="view_employee"))
        self.client.force_login(unlinked)
        self.assertFalse(self.capability())
        self.assertEqual(self.client.patch(self.detail(), {"desc": "Unlinked"}, format="json").status_code, 403)

        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.collection(hidden)).status_code, 404)
        self.assertEqual(self.client.patch(self.detail(employee=hidden), {"desc": "Hidden"}, format="json").status_code, 404)

    def test_milestone_edit_permission_does_not_grant_dependency_mutations(self):
        predecessor = Milestones.objects.create(project=self.project, name="Earlier")
        relation = MilestoneDependency.objects.create(predecessor=predecessor, successor=self.item)
        collection = reverse("api_v1:planning-dependencies", kwargs={"successor_id": self.item.pk})
        detail = reverse("api_v1:planning-dependency-detail", kwargs={
            "successor_id": self.item.pk, "dependency_id": relation.pk,
        })
        self.assertTrue(self.capability())
        self.assertEqual(self.client.post(collection, {"predecessor_id": predecessor.pk}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(detail).status_code, 403)
        self.assertTrue(MilestoneDependency.objects.filter(pk=relation.pk).exists())
