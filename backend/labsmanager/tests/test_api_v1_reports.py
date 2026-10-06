from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.http import HttpResponse
from django.urls import reverse
from rest_framework.test import APITestCase

from project.models import Participant, Project
from reports.models import EmployeePDFReport, EmployeeWordReport, ProjectPDFReport, ProjectWordReport
from staff.models import Employee


class ReportExportV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="reports-user", password="test")
        self.employee = Employee.objects.create(first_name="Ada", last_name="Lovelace", user=self.user)
        self.hidden_employee = Employee.objects.create(first_name="Hidden", last_name="Person")
        self.project = Project.objects.create(name="Visible project", status=True)
        self.hidden_project = Project.objects.create(name="Hidden project", status=True)
        Participant.objects.create(project=self.project, employee=self.employee, status="l")
        self.client.force_login(self.user)
        self.models = {
            ("project", "word"): ProjectWordReport,
            ("project", "pdf"): ProjectPDFReport,
            ("employee", "word"): EmployeeWordReport,
            ("employee", "pdf"): EmployeePDFReport,
        }

    def grant(self, model):
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="reports", codename=f"view_{model._meta.model_name}"
        ))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def url(self, entity, format_name, pk=None):
        if pk is None:
            pk = self.project.pk if entity == "project" else self.employee.pk
        return reverse("api_v1:report-export", kwargs={"entity": entity, "pk": pk, "format_name": format_name})

    def test_independent_capabilities_and_direct_endpoint_permissions(self):
        for entity in ("project", "employee"):
            with self.subTest(entity=entity):
                if entity == "employee":
                    self.user.user_permissions.add(Permission.objects.get(content_type__app_label="staff", codename="view_employee"))
                    self.user = get_user_model().objects.get(pk=self.user.pk)
                    self.client.force_login(self.user)
                pk = self.project.pk if entity == "project" else self.hidden_employee.pk
                detail = reverse("api_v1:project-detail" if entity == "project" else "api_v1:employee-detail", kwargs={"pk": pk})
                capabilities = self.client.get(detail).json()["capabilities"]
                self.assertFalse(capabilities["can_export_word"])
                self.assertFalse(capabilities["can_export_pdf"])
                for format_name in ("word", "pdf"):
                    self.assertEqual(self.client.get(self.url(entity, format_name, pk)).status_code, 403)
                    self.assertEqual(self.client.post(self.url(entity, format_name, pk), {"template_id": 1}, format="json").status_code, 403)
                self.grant(self.models[(entity, "word")])
                capabilities = self.client.get(detail).json()["capabilities"]
                self.assertTrue(capabilities["can_export_word"])
                self.assertFalse(capabilities["can_export_pdf"])
                self.grant(self.models[(entity, "pdf")])
                self.assertTrue(self.client.get(detail).json()["capabilities"]["can_export_pdf"])

    def test_templates_and_existing_renderers_for_all_four_types(self):
        for (entity, format_name), model in self.models.items():
            with self.subTest(entity=entity, format=format_name):
                self.grant(model)
                report = model.objects.create(name=f"{entity} {format_name}", description="Template", template="report.docx")
                url = self.url(entity, format_name)
                self.assertEqual(self.client.get(url).json(), {"templates": [{"id": report.pk, "name": report.name}]})
                with patch.object(model, "render", autospec=True, return_value=HttpResponse(b"file", content_type="application/pdf")) as render:
                    payload = {"template_id": report.pk}
                    if entity == "employee":
                        payload.update(start_date="2025-01-01", end_date="2026-01-01")
                    response = self.client.post(url, payload, format="json")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b"file")
                render.assert_called_once()
                request = render.call_args.args[1]
                self.assertEqual(render.call_args.args[2], {"pk": self.project.pk if entity == "project" else self.employee.pk})
                if entity == "employee":
                    self.assertEqual(request.GET["start_date"], "2025-01-01")
                    self.assertEqual(request.GET["end_date"], "2026-01-01")

    def test_wrong_template_type_invalid_template_and_project_dates_are_rejected(self):
        self.grant(ProjectWordReport)
        self.grant(ProjectPDFReport)
        word = ProjectWordReport.objects.create(name="Word", description="Template", template="word.docx")
        ProjectPDFReport.objects.create(name="PDF", description="Template", template="pdf.html")
        pdf = ProjectPDFReport.objects.create(name="PDF 2", description="Template", template="pdf2.html")
        url = self.url("project", "word")
        self.assertEqual(self.client.post(url, {"template_id": pdf.pk}, format="json").status_code, 404)
        self.assertEqual(self.client.post(url, {"template_id": 999999}, format="json").status_code, 404)
        self.assertEqual(self.client.post(url, {"template_id": word.pk, "start_date": "2025-01-01"}, format="json").status_code, 400)

    def test_hidden_entities_remain_404_even_with_export_permission(self):
        for (entity, format_name), model in self.models.items():
            with self.subTest(entity=entity, format=format_name):
                self.grant(model)
                pk = self.hidden_project.pk if entity == "project" else self.hidden_employee.pk
                url = self.url(entity, format_name, pk)
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url, {"template_id": 1}, format="json").status_code, 404)

    def test_employee_optional_dates_and_inverted_range(self):
        self.grant(EmployeeWordReport)
        report = EmployeeWordReport.objects.create(name="Word", description="Template", template="word.docx")
        url = self.url("employee", "word")
        self.assertEqual(self.client.post(url, {"template_id": report.pk, "start_date": "2026-01-02", "end_date": "2026-01-01"}, format="json").status_code, 400)
        with patch.object(EmployeeWordReport, "render", autospec=True, return_value=HttpResponse(b"file")) as render:
            response = self.client.post(url, {"template_id": report.pk, "start_date": None, "end_date": None}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("start_date", render.call_args.args[1].GET)
        self.assertNotIn("end_date", render.call_args.args[1].GET)

    def test_legacy_direct_render_urls_apply_the_same_scope_and_permissions(self):
        routes = {
            ("project", "word"): "project_report",
            ("project", "pdf"): "project_pdf_report",
            ("employee", "word"): "employee_report",
            ("employee", "pdf"): "employee_pdf_report",
        }
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="staff", codename="view_employee"))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        for (entity, format_name), model in self.models.items():
            with self.subTest(entity=entity, format=format_name):
                report = model.objects.create(name="Legacy", description="Template", template="legacy.docx")
                pk = self.project.pk if entity == "project" else self.hidden_employee.pk
                url = reverse(routes[(entity, format_name)], kwargs={"pk": pk, "template": report.pk})
                self.assertEqual(self.client.get(url).status_code, 403)
                self.grant(model)
                with patch.object(model, "render", autospec=True, return_value=HttpResponse(b"legacy")) as render:
                    self.assertEqual(self.client.get(url).content, b"legacy")
                render.assert_called_once()
                hidden_pk = self.hidden_project.pk if entity == "project" else 999999
                hidden = reverse(routes[(entity, format_name)], kwargs={"pk": hidden_pk, "template": report.pk})
                self.assertEqual(self.client.get(hidden).status_code, 404)

    def test_legacy_employee_range_is_revalidated(self):
        report = EmployeeWordReport.objects.create(name="Legacy", description="Template", template="legacy.docx")
        url = reverse("employee_report", kwargs={"pk": self.employee.pk, "template": report.pk})
        self.assertEqual(self.client.get(url, {"start_date": "2026-02-01", "end_date": "2026-01-01"}).status_code, 400)
        self.assertEqual(self.client.get(url, {"start_date": "invalid"}).status_code, 400)
