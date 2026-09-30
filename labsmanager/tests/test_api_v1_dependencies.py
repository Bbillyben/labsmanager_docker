from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from endpoints.models import MilestoneDependency, Milestones
from project.models import Participant, Project
from staff.models import Employee


class DependencyModelTests(TestCase):
    def setUp(self):
        self.first = Milestones.objects.create(name="First", project=Project.objects.create(name="First project"), start_date=date(2026, 6, 2))
        self.second = Milestones.objects.create(name="Second", project=Project.objects.create(name="Second project"), end_date=date(2026, 6, 1))
        self.third = Milestones.objects.create(name="Third", project=self.second.project)

    def test_temporal_difference_is_informational(self):
        relation = MilestoneDependency.objects.create(predecessor=self.first, successor=self.second)
        self.assertTrue(relation.temporally_inconsistent)
        self.assertEqual(MilestoneDependency.objects.count(), 1)

    def test_self_duplicate_and_indirect_cycle_are_rejected(self):
        with self.assertRaises(ValidationError):
            MilestoneDependency.objects.create(predecessor=self.first, successor=self.first)
        MilestoneDependency.objects.create(predecessor=self.first, successor=self.second)
        with self.assertRaises(ValidationError):
            MilestoneDependency.objects.create(predecessor=self.first, successor=self.second)
        MilestoneDependency.objects.create(predecessor=self.second, successor=self.third)
        with self.assertRaises(ValidationError):
            MilestoneDependency.objects.create(predecessor=self.third, successor=self.first)
        self.assertEqual(MilestoneDependency.objects.count(), 2)

    def test_endpoint_delete_cascades_to_dependency(self):
        MilestoneDependency.objects.create(predecessor=self.first, successor=self.second)
        self.first.delete()
        self.assertFalse(MilestoneDependency.objects.exists())

    def test_successor_delete_cascades_and_all_work_kind_pairs_are_allowed(self):
        milestone = Milestones.objects.create(name="Point", project=self.first.project, end_date=date(2026, 6, 3))
        task = Milestones.objects.create(name="Task", project=self.first.project, start_date=date(2026, 6, 4))
        for predecessor, successor in ((self.first, task), (self.first, milestone), (milestone, task), (milestone, self.second)):
            MilestoneDependency.objects.create(predecessor=predecessor, successor=successor)
        self.assertEqual(MilestoneDependency.objects.count(), 4)
        milestone.delete()
        self.assertEqual(MilestoneDependency.objects.count(), 1)

    def test_temporal_equal_later_and_missing_dates(self):
        point = Milestones.objects.create(name="Point", project=self.first.project, end_date=date(2026, 6, 2))
        later = Milestones.objects.create(name="Later", project=self.first.project, start_date=date(2026, 6, 3))
        unknown = Milestones.objects.create(name="Unknown", project=self.first.project)
        self.assertFalse(MilestoneDependency.objects.create(predecessor=self.first, successor=point).temporally_inconsistent)
        self.assertFalse(MilestoneDependency.objects.create(predecessor=point, successor=later).temporally_inconsistent)
        self.assertFalse(MilestoneDependency.objects.create(predecessor=unknown, successor=point).temporally_inconsistent)


class DependencyApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="planning-editor", password="test-password")
        self.employee = Employee.objects.create(first_name="Planning", last_name="Editor", user=self.user)
        self.first_project = Project.objects.create(name="First project")
        self.second_project = Project.objects.create(name="Second project")
        self.first = Milestones.objects.create(name="First", project=self.first_project)
        self.second = Milestones.objects.create(name="Second", project=self.second_project)
        Participant.objects.create(employee=self.employee, project=self.first_project, status="l")
        Participant.objects.create(employee=self.employee, project=self.second_project, status="p")
        self.client.force_login(self.user)
        self.url = reverse("api_v1:planning-dependencies", kwargs={"successor_id": self.first.pk})

    def test_requires_change_on_both_projects_for_create_and_delete(self):
        self.assertEqual(self.client.post(self.url, {"predecessor_id": self.second.pk}).status_code, 403)
        relation = MilestoneDependency.objects.create(predecessor=self.second, successor=self.first)
        delete_url = reverse("api_v1:planning-dependency-detail", kwargs={"successor_id": self.first.pk, "dependency_id": relation.pk})
        self.assertEqual(self.client.delete(delete_url).status_code, 403)
        Participant.objects.filter(employee=self.employee, project=self.second_project).update(status="cl")
        self.assertEqual(self.client.delete(delete_url).status_code, 204)
        self.assertEqual(self.client.post(self.url, {"predecessor_id": self.second.pk}).status_code, 201)

    def test_candidates_are_scoped_and_cycle_is_reported(self):
        projects = self.client.get(reverse("api_v1:planning-projects")).json()
        self.assertEqual([project["id"] for project in projects], [self.first_project.pk])
        self.assertEqual(self.client.get(reverse("api_v1:planning-project-items", kwargs={"project_id": self.second_project.pk})).status_code, 404)
        Participant.objects.filter(employee=self.employee, project=self.second_project).update(status="l")
        self.assertEqual(self.client.post(self.url, {"predecessor_id": self.second.pk}).status_code, 201)
        reverse_url = reverse("api_v1:planning-dependencies", kwargs={"successor_id": self.second.pk})
        response = self.client.post(reverse_url, {"predecessor_id": self.first.pk})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "cycle")

    def test_global_change_permission_is_respected(self):
        permission = Permission.objects.get(codename="change_project", content_type__app_label="project")
        self.user.user_permissions.add(permission)
        self.assertEqual(self.client.post(self.url, {"predecessor_id": self.second.pk}).status_code, 201)

    def test_read_only_and_no_rights_cannot_mutate(self):
        Participant.objects.filter(employee=self.employee).update(status="p")
        self.assertEqual(self.client.post(self.url, {"predecessor_id": self.second.pk}).status_code, 403)
        Participant.objects.filter(employee=self.employee).delete()
        self.assertIn(self.client.post(self.url, {"predecessor_id": self.second.pk}).status_code, (403, 404))

    def test_get_and_temporal_flag_are_scoped(self):
        self.first.start_date = date(2026, 6, 1)
        self.first.save()
        self.second.start_date = date(2026, 6, 2)
        self.second.save()
        relation = MilestoneDependency.objects.create(predecessor=self.second, successor=self.first)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["predecessors"][0]["id"], relation.pk)
        self.assertTrue(response.json()["predecessors"][0]["temporally_inconsistent"])
        self.assertFalse(response.json()["predecessors"][0]["can_delete"])

    def test_successors_are_directional_and_only_visible_items_are_returned(self):
        visible_relation = MilestoneDependency.objects.create(predecessor=self.first, successor=self.second)
        hidden_project = Project.objects.create(name="Hidden successor project")
        hidden_item = Milestones.objects.create(name="Hidden successor", project=hidden_project)
        MilestoneDependency.objects.create(predecessor=self.first, successor=hidden_item)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["predecessors"], [])
        self.assertEqual([relation["id"] for relation in response.json()["successors"]], [visible_relation.pk])
        self.assertEqual(response.json()["successors"][0]["successor"]["id"], self.second.pk)
        self.assertEqual(response.json()["successors"][0]["predecessor_id"], self.first.pk)
        self.assertNotIn("can_delete", response.json()["successors"][0])
        self.assertNotIn("Hidden successor", str(response.json()))
        self.assertEqual(self.client.get(reverse("api_v1:planning-dependencies", kwargs={"successor_id": hidden_item.pk})).status_code, 404)

    def test_api_rejects_self_and_duplicate_with_explicit_codes(self):
        Participant.objects.filter(employee=self.employee, project=self.second_project).update(status="l")
        self.assertEqual(self.client.post(self.url, {"predecessor_id": self.first.pk}).json()["code"], "self_dependency")
        self.assertEqual(self.client.post(self.url, {"predecessor_id": self.second.pk}).status_code, 201)
        self.assertEqual(self.client.post(self.url, {"predecessor_id": self.second.pk}).json()["code"], "duplicate")

    def test_change_on_predecessor_alone_is_insufficient(self):
        Participant.objects.filter(employee=self.employee, project=self.first_project).update(status="p")
        Participant.objects.filter(employee=self.employee, project=self.second_project).update(status="l")
        self.assertEqual(self.client.post(self.url, {"predecessor_id": self.second.pk}).status_code, 403)

    def test_session_post_requires_csrf(self):
        strict_client = APIClient(enforce_csrf_checks=True)
        strict_client.force_login(self.user)
        response = strict_client.post(self.url, {"predecessor_id": self.second.pk})
        self.assertEqual(response.status_code, 403)

    def test_intra_project_change_and_lost_successor_change(self):
        predecessor = Milestones.objects.create(name="Same project", project=self.first_project)
        response = self.client.post(self.url, {"predecessor_id": predecessor.pk})
        self.assertEqual(response.status_code, 201)
        relation_id = response.json()["id"]
        Participant.objects.filter(employee=self.employee, project=self.first_project).update(status="p")
        delete_url = reverse("api_v1:planning-dependency-detail", kwargs={"successor_id": self.first.pk, "dependency_id": relation_id})
        self.assertEqual(self.client.delete(delete_url).status_code, 403)

    def test_participant_view_only_can_read_but_cannot_mutate(self):
        Participant.objects.filter(employee=self.employee).update(status="p")
        relation = MilestoneDependency.objects.create(predecessor=self.second, successor=self.first)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["can_add"], False)
        self.assertEqual(response.json()["predecessors"][0]["id"], relation.pk)
        self.assertEqual(response.json()["predecessors"][0]["can_delete"], False)
        self.assertEqual(self.client.post(self.url, {"predecessor_id": self.second.pk}).status_code, 403)
        delete_url = reverse("api_v1:planning-dependency-detail", kwargs={"successor_id": self.first.pk, "dependency_id": relation.pk})
        self.assertEqual(self.client.delete(delete_url).status_code, 403)

    def test_global_project_view_only_can_read_and_hidden_project_is_404(self):
        Participant.objects.filter(employee=self.employee).delete()
        relation = MilestoneDependency.objects.create(predecessor=self.second, successor=self.first)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        permission = Permission.objects.get(codename="view_project", content_type__app_label="project")
        self.user.user_permissions.add(permission)
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["can_add"])
        self.assertEqual(response.json()["predecessors"][0]["id"], relation.pk)
        self.assertFalse(response.json()["predecessors"][0]["can_delete"])

    def test_contextual_employee_visibility_can_read_without_project_view(self):
        Participant.objects.filter(employee=self.employee).delete()
        self.first.employee.add(self.employee)
        relation = MilestoneDependency.objects.create(predecessor=self.second, successor=self.first)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["can_add"])
        self.assertEqual(response.json()["predecessors"], [])
        self.second.employee.add(self.employee)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["predecessors"][0]["id"], relation.pk)
        self.assertFalse(response.json()["predecessors"][0]["can_delete"])
        self.assertEqual(self.client.post(self.url, {"predecessor_id": self.second.pk}).status_code, 403)
        delete_url = reverse("api_v1:planning-dependency-detail", kwargs={"successor_id": self.first.pk, "dependency_id": relation.pk})
        self.assertEqual(self.client.delete(delete_url).status_code, 403)
