import csv
from datetime import date
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework.test import APITestCase

from fund.models import Fund, Fund_Institution
from project.models import Institution
from project.models import Participant, Project
from project.resources import ProjectResource
from staff.models import Employee, Employee_Status, Employee_Type


def csv_rows(response, delimiter=","):
    return list(csv.reader(StringIO(response.content.decode("utf-8-sig")), delimiter=delimiter))


class EmployeeListExportV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="employee-exporter", password="test")
        self.own = Employee.objects.create(first_name="Own", last_name="Person", user=self.user)
        self.visible = Employee.objects.create(first_name="Alice", last_name="Visible")
        Employee.objects.create(first_name="Hidden", last_name="Person")
        from staff.models import Employee_Superior
        Employee_Superior.objects.create(employee=self.visible, superior=self.own)
        self.project = Project.objects.create(name="Export Project")
        Participant.objects.create(project=self.project, employee=self.visible)
        self.status = Employee_Type.objects.create(shortname="EXP", name="Export status")
        Employee_Status.objects.create(employee=self.visible, type=self.status)
        self.client.force_login(self.user)
        self.url = reverse("api_v1:employee-list-export")

    def test_formats_headers_and_nonempty_files(self):
        for format_name, mime in (
            ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("csv", "text/csv"),
            ("tsv", "text/tab-separated-values"),
            ("xls", "application/vnd.ms-excel"),
        ):
            with self.subTest(format=format_name):
                response = self.client.get(self.url, {"format": format_name})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.content)
                self.assertTrue(response["Content-Type"].startswith(mime))
                self.assertRegex(response["Content-Disposition"], rf'attachment; filename="Employee_\d{{8}}-\d{{4}}\.{format_name}"')
        self.assertEqual(self.client.get(self.url, {"format": "pdf"}).status_code, 400)
        self.assertEqual(self.client.post(self.url, {"first_name": "Forbidden"}).status_code, 405)

    def test_same_filters_ordering_visibility_and_no_pagination(self):
        Employee.objects.create(first_name="Zed", last_name="Not visible")
        params = {"project": self.project.pk, "status": self.status.pk, "ordering": "-first_name", "limit": 1, "offset": 1, "format": "csv"}
        response = self.client.get(self.url, params)
        rows = csv_rows(response)
        self.assertEqual(len(rows), 2)
        self.assertIn("Alice", rows[1])
        self.assertNotIn("Hidden", response.content.decode())
        self.assertEqual(self.client.get(self.url, {"format": "csv"}).status_code, 200)
        self.assertNotIn("Hidden", self.client.get(self.url, {"format": "csv"}).content.decode())

    def test_export_cannot_bypass_authentication(self):
        self.client.logout()
        self.assertIn(self.client.get(self.url).status_code, (401, 403))

    def test_lab_resource_still_removes_formula_prefixes(self):
        self.own.first_name = "=HYPERLINK"
        self.own.save()
        rows = csv_rows(self.client.get(self.url, {"format": "csv"}))
        self.assertTrue(any("HYPERLINK" in row for row in rows[1:]))
        self.assertFalse(any("=HYPERLINK" in row for row in rows[1:]))


class ProjectListExportV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="project-exporter", password="test")
        self.employee = Employee.objects.create(first_name="Project", last_name="Reader", user=self.user)
        self.alpha = Project.objects.create(name="Alpha", status=True, start_date=date(2026, 1, 1))
        self.beta = Project.objects.create(name="Beta", status=True, start_date=date(2026, 2, 1))
        self.hidden = Project.objects.create(name="Hidden", status=True)
        for project in (self.alpha, self.beta):
            Participant.objects.create(project=project, employee=self.employee)
        self.client.force_login(self.user)
        self.url = reverse("api_v1:project-list-export")

    def test_resource_format_filters_ordering_and_pagination(self):
        real_export = ProjectResource.export
        with patch.object(ProjectResource, "export", autospec=True, side_effect=real_export) as resource_export:
            response = self.client.get(self.url, {"format": "csv", "status": "true", "ordering": "-name", "limit": 1, "offset": 1})
            self.assertTrue(resource_export.called)
        self.assertEqual(response.status_code, 200)
        rows = csv_rows(response)
        self.assertEqual(len(rows), 3)
        self.assertEqual([row[0] for row in rows[1:]], ["Beta", "Alpha"])
        self.assertNotIn("Hidden", response.content.decode())
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertRegex(response["Content-Disposition"], r'attachment; filename="Project_\d{8}-\d{4}\.csv"')
        self.assertEqual(len(csv_rows(self.client.get(self.url, {"project_name": "Alpha", "format": "csv"}))), 2)
        self.assertEqual(self.client.get(self.url, {"format": "json"}).status_code, 400)
        self.assertEqual(self.client.post(self.url, {"name": "Forbidden"}).status_code, 405)

    def test_project_export_honors_global_view_scope(self):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="project", codename="view_project"))
        response = self.client.get(self.url, {"format": "csv", "ordering": "name"})
        self.assertIn("Hidden", response.content.decode())

    def test_export_does_not_reveal_a_fund_hidden_by_the_list(self):
        institution = Institution.objects.create(short_name="PRIVATE", name="Private institution")
        funder = Fund_Institution.objects.create(short_name="PRIVATE", name="Private funder")
        Fund.objects.create(project=self.alpha, institution=institution, funder=funder, ref="SECRET-REF")
        listed = self.client.get(reverse("api_v1:projects"), {"project_name": "Alpha"})
        self.assertEqual(listed.json()["results"][0]["funds"], [])
        exported = self.client.get(self.url, {"project_name": "Alpha", "format": "csv"})
        self.assertNotIn("SECRET-REF", exported.content.decode())
        legacy = self.client.get("/api/project/", {"export": "csv"})
        self.assertEqual(legacy.status_code, 200)
        self.assertNotIn("SECRET-REF", b"".join(legacy.streaming_content).decode())

        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="fund", codename="view_fund"))
        self.client.force_login(self.user)
        legacy_with_fund_right = self.client.get("/api/project/", {"export": "csv"})
        self.assertIn("SECRET-REF", b"".join(legacy_with_fund_right.streaming_content).decode())

    def test_visible_fund_subset_controls_every_financial_column_and_legacy_scope(self):
        institution = Institution.objects.create(short_name="MANAGER", name="Manager institution")
        funder = Fund_Institution.objects.create(short_name="FUNDER", name="Funder")
        visible = Fund.objects.create(project=self.alpha, institution=institution, funder=funder, ref="VISIBLE-REF")
        hidden = Fund.objects.create(project=self.alpha, institution=institution, funder=funder, ref="HIDDEN-REF")
        Fund.objects.filter(pk=visible.pk).update(amount=120, expense=-20, amount_f=60, expense_f=-10)
        Fund.objects.filter(pk=hidden.pk).update(amount=900, expense=-100, amount_f=500, expense_f=-50)

        # Today's Fund rule grants by project; this bounded return models a
        # narrower Fund scope without copying a permission predicate here.
        with patch.object(Fund, "get_instances_for_user", side_effect=lambda perm, user, queryset=None: (queryset if queryset is not None else Fund.objects.all()).filter(pk=visible.pk)):
            listed = self.client.get(reverse("api_v1:projects"), {"project_name": "Alpha"})
            exported = self.client.get(self.url, {"project_name": "Alpha", "format": "csv"})
        self.assertEqual(listed.json()["results"][0]["funds"], ["FUNDER · VISIBLE-REF"])
        rows = csv_rows(exported)
        row = dict(zip(rows[0], rows[1]))
        self.assertIn("VISIBLE-REF", row["Fund"])
        self.assertNotIn("HIDDEN-REF", exported.content.decode())
        self.assertEqual({name: Decimal(row[name]) for name in (
            "Total Fund", "Total Expense", "Total Available",
            "Total Fund Focus", "Total Expense Focus", "Total Available Focus",
        )}, {
            "Total Fund": Decimal("120"), "Total Expense": Decimal("-20"), "Total Available": Decimal("100"),
            "Total Fund Focus": Decimal("60"), "Total Expense Focus": Decimal("-10"), "Total Available Focus": Decimal("50"),
        })

        full = ProjectResource(fund_scope="all").export(queryset=Project.objects.filter(pk=self.alpha.pk))
        self.assertIn("HIDDEN-REF", full.export("csv"))
