from datetime import date, timedelta
from unittest.mock import patch

from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from fund.models import Fund, Fund_Institution
from project.models import Institution, Institution_Participant, Participant, Project
from staff.models import Employee


class ProjectListV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="project-reader", password="test")
        self.employee = Employee.objects.create(first_name="A", last_name="Reader", user=self.user)
        self.visible = Project.objects.create(name="Alpha", status=True, start_date=date(2026, 1, 1))
        self.inactive = Project.objects.create(name="Beta", status=False)
        self.hidden = Project.objects.create(name="Secret", status=True)
        Participant.objects.create(project=self.visible, employee=self.employee, status="l")
        self.list_url = reverse("api_v1:projects")
        self.client.force_login(self.user)

    def grant(self, codename):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="project", codename=codename))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def test_visibility_filters_search_sort_and_pagination(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.json()["results"]], ["Alpha"])
        self.grant("view_project")
        self.assertEqual([item["name"] for item in self.client.get(self.list_url, {"status": "true"}).json()["results"]], ["Alpha", "Secret"])
        self.assertEqual([item["name"] for item in self.client.get(self.list_url, {"status": "false"}).json()["results"]], ["Beta"])
        self.assertEqual([item["name"] for item in self.client.get(self.list_url, {"search": "beta"}).json()["results"]], ["Beta"])
        self.assertEqual([item["name"] for item in self.client.get(self.list_url, {"ordering": "-name", "limit": 1}).json()["results"]], ["Secret"])
        self.assertEqual(self.client.get(self.list_url, {"ordering": "name", "limit": 1, "offset": 1}).json()["results"][0]["name"], "Beta")

    @patch("project.models.LMUserSetting.get_setting", return_value=3)
    def test_stale_filter_keeps_existing_active_and_end_date_threshold(self, _setting):
        self.grant("view_project")
        today = date.today()
        soon = Project.objects.create(name="Soon", status=True, end_date=today + timedelta(days=20))
        overdue = Project.objects.create(name="Overdue", status=True, end_date=today - timedelta(days=1))
        far = Project.objects.create(name="Far", status=True, end_date=today + timedelta(days=200))
        inactive = Project.objects.create(name="Inactive", status=False, end_date=today + timedelta(days=20))
        stale = {item["id"] for item in self.client.get(self.list_url, {"stale": "true"}).json()["results"]}
        fresh = {item["id"] for item in self.client.get(self.list_url, {"stale": "false"}).json()["results"]}
        self.assertIn(soon.pk, stale)
        self.assertIn(overdue.pk, stale)
        self.assertNotIn(far.pk, stale)
        self.assertNotIn(inactive.pk, stale)
        self.assertIn(far.pk, fresh)
        self.assertIn(inactive.pk, fresh)

    def test_compact_relations_are_scoped_to_visible_projects(self):
        institution = Institution.objects.create(short_name="IN", name="Institution")
        funder = Fund_Institution.objects.create(short_name="FUN", name="Funder")
        Institution_Participant.objects.create(project=self.visible, institution=institution)
        Fund.objects.create(project=self.visible, institution=institution, funder=funder, ref="A-1")
        hidden_institution = Institution.objects.create(short_name="SECRET", name="Secret institution")
        Institution_Participant.objects.create(project=self.hidden, institution=hidden_institution)
        self.grant("view_project")
        item = next(item for item in self.client.get(self.list_url).json()["results"] if item["name"] == "Alpha")
        self.assertEqual(item["institutions"], ["IN"])
        self.assertEqual(item["participants"], [str(self.employee)])
        self.assertEqual(item["funds"], ["FUN · A-1"])
        self.assertNotIn("SECRET", str(self.client.get(self.list_url, {"project_name": "Alpha"}).json()))

    def test_create_update_delete_and_capabilities(self):
        self.assertFalse(self.client.get(reverse("api_v1:project-capabilities")).json()["can_add"])
        self.assertEqual(self.client.post(self.list_url, {"name": "Created", "status": True}, format="json").status_code, 403)
        self.grant("add_project")
        self.assertTrue(self.client.get(reverse("api_v1:project-capabilities")).json()["can_add"])
        created = self.client.post(self.list_url, {"name": "Created", "status": True}, format="json")
        self.assertEqual(created.status_code, 201)
        project = Project.objects.get(pk=created.json()["id"])
        self.assertTrue(Participant.objects.filter(project=project, employee=self.employee, status="l").exists())
        detail = reverse("api_v1:project-detail", kwargs={"pk": project.pk})
        self.assertTrue(self.client.get(detail).json()["capabilities"]["can_change"])
        self.assertEqual(self.client.patch(detail, {"end_date": "2025-01-01"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(detail, {"name": "Renamed"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(detail, {"status": False}, format="json").status_code, 200)
        audit = LogEntry.objects.filter(content_type=ContentType.objects.get_for_model(Project), object_pk=str(project.pk))
        self.assertTrue(audit.filter(action=LogEntry.Action.CREATE).exists())
        self.assertTrue(audit.filter(action=LogEntry.Action.UPDATE).exists())
        self.assertEqual(self.client.delete(detail).status_code, 403)
        self.grant("delete_project")
        self.assertEqual(self.client.delete(detail).status_code, 204)
        self.assertFalse(Project.objects.filter(pk=project.pk).exists())
        self.assertTrue(audit.filter(action=LogEntry.Action.DELETE).exists())

    def test_hidden_detail_and_related_filter_options(self):
        hidden_url = reverse("api_v1:project-detail", kwargs={"pk": self.hidden.pk})
        self.assertEqual(self.client.get(hidden_url).status_code, 404)
        self.assertEqual(self.client.patch(hidden_url, {"status": False}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(hidden_url).status_code, 404)
        self.assertEqual(self.client.get(reverse("api_v1:project-filter-options")).status_code, 200)

    def test_view_only_user_cannot_change_or_delete(self):
        reader = get_user_model().objects.create_user(username="project-view-only", password="test")
        reader.user_permissions.add(Permission.objects.get(content_type__app_label="project", codename="view_project"))
        self.client.force_login(reader)
        detail = reverse("api_v1:project-detail", kwargs={"pk": self.visible.pk})
        self.assertEqual(self.client.get(detail).status_code, 200)
        self.assertEqual(self.client.get(detail).json()["capabilities"], {"can_add": False, "can_change": False, "can_delete": False, "can_export_word": False, "can_export_pdf": False, "can_change_settings": False})
        self.assertEqual(self.client.patch(detail, {"status": False}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(detail).status_code, 403)
        self.assertEqual(self.client.post(self.list_url, {"name": "Denied"}, format="json").status_code, 403)

    def test_related_legacy_filters_and_hidden_option_values(self):
        institution = Institution.objects.create(short_name="VISIBLE", name="Visible institution")
        hidden_institution = Institution.objects.create(short_name="HIDDEN", name="Hidden institution")
        Institution_Participant.objects.create(project=self.visible, institution=institution)
        Institution_Participant.objects.create(project=self.hidden, institution=hidden_institution)
        self.assertEqual(self.client.get(self.list_url, {"institution_name": institution.pk}).json()["count"], 1)
        self.assertEqual(self.client.get(self.list_url, {"institution_name": hidden_institution.pk}).json()["count"], 0)
        self.assertEqual(self.client.get(self.list_url, {"participant_name": "Reader"}).json()["count"], 1)
        self.assertEqual(self.client.get(self.list_url, {"participant": self.employee.pk}).json()["count"], 1)
        self.assertEqual(self.client.get(self.list_url, {"participant": self.employee.pk + 10000}).json()["count"], 0)
        self.assertEqual(self.client.get(self.list_url, {"project_name": "alp"}).json()["count"], 1)
        self.assertEqual(self.client.get(self.list_url, {"start_date": "2026-01-01"}).json()["count"], 1)
        options = self.client.get(reverse("api_v1:project-filter-options")).json()
        self.assertEqual([item["short_name"] for item in options["institutions"]], ["VISIBLE"])

    def test_visible_project_does_not_reveal_inaccessible_fund_through_filters(self):
        institution = Institution.objects.create(short_name="PRIVATE", name="Private institution")
        funder = Fund_Institution.objects.create(short_name="PRIVATE", name="Private funder")
        Fund.objects.create(project=self.inactive, institution=institution, funder=funder, ref="SECRET-REF")
        self.grant("view_project")
        self.assertEqual(self.client.get(self.list_url, {"status": "false"}).json()["count"], 1)
        item = self.client.get(self.list_url, {"status": "false"}).json()["results"][0]
        self.assertEqual(item["funds"], [])
        for criterion in ({"fundref": "SECRET-REF"}, {"funder": funder.pk}, {"institution_name": institution.pk}, {"search": "SECRET-REF"}):
            self.assertEqual(self.client.get(self.list_url, criterion).json()["count"], 0)
        self.assertEqual(self.client.get(reverse("api_v1:project-filter-options")).json()["funders"], [])

    def test_authentication_and_csrf(self):
        self.client.logout()
        self.assertIn(self.client.get(self.list_url).status_code, (401, 403))
        self.grant("add_project")
        strict = APIClient(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post(self.list_url, {"name": "CSRF"}, format="json").status_code, 403)
