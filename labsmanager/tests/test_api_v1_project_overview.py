from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from project.models import GenericInfoProject, GenericInfoTypeProject, Institution, Institution_Participant, Participant, Project
from staff.models import Employee


class ProjectOverviewV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="project-overview-reader", password="test")
        self.employee = Employee.objects.create(first_name="A", last_name="Reader", user=self.user)
        self.candidate = Employee.objects.create(first_name="B", last_name="Candidate")
        self.project = Project.objects.create(name="Atlas", status=True, start_date=date(2026, 1, 1))
        self.hidden = Project.objects.create(name="Hidden")
        self.member = Participant.objects.create(project=self.project, employee=self.employee, status="p", start_date=date(2026, 1, 1))
        self.foreign_member = Participant.objects.create(project=self.hidden, employee=self.candidate, status="p")
        self.institution = Institution.objects.create(short_name="UL", name="Université de Lille")
        self.link = Institution_Participant.objects.create(project=self.project, institution=self.institution, status="c")
        self.foreign_link = Institution_Participant.objects.create(project=self.hidden, institution=self.institution)
        self.info_type = GenericInfoTypeProject.objects.create(name="URL")
        self.info = GenericInfoProject.objects.create(project=self.project, info=self.info_type, value="https://example.test")
        self.foreign_info = GenericInfoProject.objects.create(project=self.hidden, info=self.info_type, value="hidden")
        self.detail = reverse("api_v1:project-detail", kwargs={"pk": self.project.pk})
        self.client.force_login(self.user)

    def grant(self, codename, app="project"):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def collection(self, name, project=None):
        return reverse(f"api_v1:project-{name}", kwargs={"pk": (project or self.project).pk})

    def item(self, name, item, project=None):
        return reverse(f"api_v1:project-{name}-detail", kwargs={"pk": (project or self.project).pk, "item_id": item.pk})

    def test_overview_is_scoped_and_contains_only_nonfinancial_blocks(self):
        response = self.client.get(self.detail)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Atlas")
        self.assertEqual(data["start_date"], "2026-01-01")
        self.assertEqual(data["generic_info"]["items"][0]["value"], "https://example.test")
        self.assertEqual(data["institutions"]["items"][0]["status"], "c")
        self.assertEqual(data["participants"]["items"][0]["employee"]["last_name"], self.employee.last_name)
        self.assertTrue(data["participants"]["items"][0]["employee"]["can_view"])
        self.assertNotIn("funds", data)
        self.assertEqual(self.client.get(reverse("api_v1:project-detail", kwargs={"pk": self.hidden.pk})).status_code, 404)
        self.assertEqual(self.client.get(self.collection("participants", self.hidden)).status_code, 404)

    def test_generic_info_icon_contract_uses_lucide_names_and_nullable_values(self):
        self.info_type.icon = "BookOpen"
        self.info_type.save(update_fields=["icon"])
        self.assertEqual(self.client.get(self.detail).json()["generic_info"]["items"][0]["type"],
                         {"id": self.info_type.pk, "name": "URL", "icon": "BookOpen"})
        options = self.client.get(reverse("api_v1:project-overview-options", kwargs={"pk": self.project.pk})).json()
        self.assertIn({"id": self.info_type.pk, "name": "URL", "icon": "BookOpen"}, options["generic_info_types"])
        self.info_type.icon = None
        self.info_type.save(update_fields=["icon"])
        self.assertIsNone(self.client.get(self.detail).json()["generic_info"]["items"][0]["type"]["icon"])

    def test_readonly_capabilities_and_denied_mutations(self):
        overview = self.client.get(self.detail).json()
        for block in ("generic_info", "institutions", "participants"):
            self.assertEqual(overview[block]["capabilities"], {"can_add": False, "can_change": False, "can_delete": False})
        self.assertEqual(self.client.post(self.collection("generic-info"), {"type_id": self.info_type.pk}, format="json").status_code, 403)
        self.assertEqual(self.client.patch(self.item("generic-info", self.info), {"value": "changed"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.item("generic-info", self.info)).status_code, 403)
        self.assertEqual(self.client.post(self.collection("institutions"), {"institution_id": self.institution.pk}, format="json").status_code, 403)
        self.assertEqual(self.client.patch(self.item("institution", self.link), {"status": "p"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.item("institution", self.link)).status_code, 403)
        self.assertEqual(self.client.post(self.collection("participants"), {"employee_id": self.candidate.pk, "quotity": "0.500"}, format="json").status_code, 403)
        self.assertEqual(self.client.patch(self.item("participant", self.member), {"quotity": "0.250"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.item("participant", self.member)).status_code, 403)

    def test_generic_info_crud_and_foreign_lookup(self):
        self.member.status = "l"
        self.member.save()
        response = self.client.post(self.collection("generic-info"), {"type_id": self.info_type.pk, "value": "new"}, format="json")
        self.assertEqual(response.status_code, 201)
        item = GenericInfoProject.objects.get(pk=response.json()["id"])
        self.assertEqual(self.client.patch(self.item("generic-info", item), {"value": "updated"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(self.item("generic-info", item), {"type_id": self.info_type.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.item("generic-info", self.foreign_info), {"value": "leak"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(self.item("generic-info", item)).status_code, 403)
        self.grant("delete_genericinfoproject")
        self.assertTrue(self.client.get(self.detail).json()["generic_info"]["capabilities"]["can_delete"])
        self.assertEqual(self.client.delete(self.item("generic-info", item)).status_code, 204)

    def test_institution_crud_validations_and_foreign_lookup(self):
        self.member.status = "l"
        self.member.save()
        other = Institution.objects.create(short_name="IN", name="Inserm")
        response = self.client.post(self.collection("institutions"), {"institution_id": other.pk, "status": "p"}, format="json")
        self.assertEqual(response.status_code, 201)
        item = Institution_Participant.objects.get(pk=response.json()["id"])
        self.assertEqual(self.client.post(self.collection("institutions"), {"institution_id": other.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.item("institution", item), {"status": "c"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(self.item("institution", item), {"institution_id": self.institution.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.item("institution", self.foreign_link), {"status": "c"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(self.item("institution", item)).status_code, 403)
        self.grant("delete_institution_participant")
        self.assertEqual(self.client.delete(self.item("institution", item)).status_code, 204)

    def test_participant_crud_validations_and_foreign_lookup(self):
        self.member.status = "l"
        self.member.save()
        self.grant("view_employee", "staff")
        response = self.client.post(self.collection("participants"), {"employee_id": self.candidate.pk, "status": "p", "start_date": "2026-02-01", "quotity": "0.500"}, format="json")
        self.assertEqual(response.status_code, 201)
        item = Participant.objects.get(pk=response.json()["id"])
        self.assertEqual(item.quotity, 0.5)
        self.assertEqual(self.client.post(self.collection("participants"), {"employee_id": self.candidate.pk, "quotity": "0.100"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.item("participant", item), {"employee_id": self.employee.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.item("participant", item), {"end_date": "2025-01-01"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.item("participant", item), {"quotity": "0.250"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(self.item("participant", self.foreign_member), {"quotity": "0.250"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(self.item("participant", item)).status_code, 403)
        self.grant("delete_participant")
        self.assertEqual(self.client.delete(self.item("participant", item)).status_code, 204)

    def test_catalogue_and_authentication(self):
        response = self.client.get(reverse("api_v1:project-overview-options", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["generic_info_types"][0]["name"], "URL")
        self.assertEqual(response.json()["institutions"][0]["short_name"], "UL")
        self.client.logout()
        self.assertIn(self.client.get(self.detail).status_code, (401, 403))

    def test_child_permissions_can_be_global_without_project_change(self):
        self.grant("add_genericinfoproject")
        self.grant("change_institution_participant")
        self.grant("delete_participant")
        data = self.client.get(self.detail).json()
        self.assertTrue(data["generic_info"]["capabilities"]["can_add"])
        self.assertFalse(data["generic_info"]["capabilities"]["can_change"])
        self.assertTrue(data["institutions"]["capabilities"]["can_change"])
        self.assertTrue(data["participants"]["capabilities"]["can_delete"])
        self.assertEqual(self.client.post(self.collection("generic-info"), {"type_id": self.info_type.pk}, format="json").status_code, 201)
        self.assertEqual(self.client.patch(self.item("institution", self.link), {"status": "p"}, format="json").status_code, 200)

    def test_child_parent_substitution_and_invisible_employee_are_rejected(self):
        self.member.status = "l"
        self.member.save()
        self.assertEqual(self.client.post(self.collection("generic-info"), {"project": self.hidden.pk, "type_id": self.info_type.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.collection("institutions"), {"project": self.hidden.pk, "institution_id": self.institution.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.collection("participants"), {"project": self.hidden.pk, "employee_id": self.candidate.pk, "quotity": "0.500"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.collection("participants"), {"employee_id": self.candidate.pk, "quotity": "0.500"}, format="json").status_code, 400)
        strict = APIClient(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post(self.collection("generic-info"), {"type_id": self.info_type.pk}, format="json").status_code, 403)

    def test_overview_query_count_does_not_scale_with_child_rows(self):
        with CaptureQueriesContext(connection) as first:
            self.assertEqual(self.client.get(self.detail).status_code, 200)
        for index in range(5):
            employee = Employee.objects.create(first_name=f"Extra{index}", last_name="Member")
            Participant.objects.create(project=self.project, employee=employee, status="p")
            institution = Institution.objects.create(short_name=f"I{index}", name=f"Institution {index}")
            Institution_Participant.objects.create(project=self.project, institution=institution)
            info_type = GenericInfoTypeProject.objects.create(name=f"Type {index}")
            GenericInfoProject.objects.create(project=self.project, info=info_type, value="value")
        with CaptureQueriesContext(connection) as second:
            self.assertEqual(self.client.get(self.detail).status_code, 200)
        self.assertLessEqual(len(second), len(first) + 3)
