from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase

from endpoints.models import MilestoneDependency, Milestones
from project.models import Participant, Project
from staff.models import Employee


class ProjectPlanningV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="project-planning-reader", password="test")
        self.viewer = Employee.objects.create(first_name="A", last_name="Viewer", user=self.user)
        self.assignee = Employee.objects.create(first_name="B", last_name="Assignee")
        self.outsider = Employee.objects.create(first_name="C", last_name="Outsider")
        self.project = Project.objects.create(name="Atlas")
        self.hidden = Project.objects.create(name="Hidden")
        Participant.objects.create(project=self.project, employee=self.viewer, status="p")
        Participant.objects.create(project=self.project, employee=self.assignee, status="p")
        self.today = timezone.localdate()
        self.task = Milestones.objects.create(name="Visible task", project=self.project, start_date=self.today - timedelta(days=2), end_date=self.today + timedelta(days=30))
        self.task.employee.add(self.assignee)
        self.foreign = Milestones.objects.create(name="Foreign secret", project=self.hidden)
        self.url = reverse("api_v1:project-planning", kwargs={"pk": self.project.pk})
        self.client.force_login(self.user)

    def item_url(self, item):
        return reverse("api_v1:project-planning-item", kwargs={"pk": self.project.pk, "item_id": item.pk})

    def grant_change(self):
        self.user.user_permissions.add(Permission.objects.get(codename="change_project", content_type__app_label="project"))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def payload(self, **changes):
        return {"name": "New task", "desc": None, "work_kind": "task", "start_date": str(self.today), "end_date": None, "type": "o", "quotity": "0.000", "status": False, "employee_ids": [self.assignee.pk], **changes}

    def test_read_scope_capabilities_and_mutation_denial(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["capabilities"], {"can_add": False, "can_change": False, "can_delete": False})
        self.assertEqual([item["name"] for item in data["items"]], ["Visible task"])
        self.assertEqual(data["items"][0]["employees"][0]["id"], self.assignee.pk)
        self.assertEqual({person["id"] for person in data["participants"]}, {self.viewer.pk, self.assignee.pk})
        self.assertEqual(self.client.post(self.url, self.payload(), format="json").status_code, 403)
        self.assertEqual(self.client.patch(self.item_url(self.task), self.payload(name="Changed"), format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.item_url(self.task)).status_code, 403)
        self.assertEqual(self.client.get(reverse("api_v1:project-planning", kwargs={"pk": self.hidden.pk})).status_code, 404)
        self.assertEqual(self.client.get(self.url, {"search": "Foreign secret"}).json()["items"], [])

    def test_shared_temporal_contract_and_filters(self):
        Milestones.objects.create(name="Completed", project=self.project, status=True, end_date=self.today - timedelta(days=1))
        Milestones.objects.create(name="Overdue", project=self.project, end_date=self.today - timedelta(days=1))
        Milestones.objects.create(name="Soon", project=self.project, end_date=self.today)
        Milestones.objects.create(name="Planned", project=self.project, start_date=self.today + timedelta(days=30))
        Milestones.objects.create(name="In progress", project=self.project, start_date=self.today - timedelta(days=1))
        states = {item["name"]: item["display_state"] for item in self.client.get(self.url).json()["items"]}
        self.assertEqual({states[name] for name in ("Completed", "Overdue", "Soon", "Planned", "In progress")}, {"completed", "overdue", "due_soon", "planned", "in_progress"})
        self.assertEqual([item["name"] for item in self.client.get(self.url, {"search": "Visible"}).json()["items"]], ["Visible task"])
        self.assertEqual([item["name"] for item in self.client.get(self.url, {"kind": "task", "employee": str(self.assignee.pk)}).json()["items"]], ["Visible task"])
        self.assertEqual(self.client.get(self.url, {"employee": str(self.outsider.pk)}).json()["items"], [])
        self.assertEqual(self.client.get(self.url, {"employee": "invalid"}).json()["items"], [])

    def test_crud_type_switch_participants_and_dependencies(self):
        self.grant_change()
        self.assertEqual(self.client.get(self.url).json()["capabilities"], {"can_add": True, "can_change": True, "can_delete": True})
        denied = self.client.post(self.url, self.payload(employee_ids=[self.outsider.pk]), format="json")
        self.assertEqual(denied.status_code, 400)
        self.assertIn("employee_ids", denied.json())
        created = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(created.status_code, 201)
        item = Milestones.objects.get(pk=created.json()["id"])
        self.assertEqual(list(item.employee.values_list("pk", flat=True)), [self.assignee.pk])
        relation = MilestoneDependency.objects.create(predecessor=self.task, successor=item)
        listed = self.client.get(self.url).json()["items"]
        self.assertIn(relation.pk, [dependency["id"] for entry in listed if entry["id"] == item.pk for dependency in entry["dependencies"]])
        milestone_payload = self.payload(work_kind="milestone", name="New milestone")
        milestone_payload.pop("start_date")
        changed = self.client.patch(self.item_url(item), milestone_payload, format="json")
        self.assertEqual(changed.status_code, 200)
        item.refresh_from_db()
        self.assertIsNone(item.start_date)
        self.assertEqual(changed.json()["work_kind"], "milestone")
        self.assertEqual(self.client.post(self.url, self.payload(work_kind="milestone", start_date=str(self.today)), format="json").status_code, 400)
        self.assertEqual(self.client.delete(self.item_url(item)).status_code, 204)
        self.assertFalse(MilestoneDependency.objects.filter(pk=relation.pk).exists())
        self.assertEqual(self.client.patch(self.item_url(self.foreign), self.payload(), format="json").status_code, 404)
