"""Focused integration tests for the disposable synthetic dataset."""

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from dashboard.models import Dashboard
from dashboard.registry import DashboardContext
from dashboard import business_sources
from endpoints.models import Milestones
from expense.models import Contract, Expense, Expense_point
from fund.models import AmountHistory, Fund
from leave.models import Leave
from project.models import Project
from reports.models import EmployeeWordReport, ProjectPDFReport
from staff.models import Employee, Employee_Superior

from .context import DemoContext


@override_settings(DEBUG=True)
class DemoDatasetTests(TestCase):
    T0 = date(2026, 10, 4)

    @classmethod
    def setUpClass(cls):
        cls._media_dir = TemporaryDirectory()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_dir.name)
        cls._media_override.enable()
        try:
            super().setUpClass()
        except Exception:
            cls._media_override.disable()
            cls._media_dir.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls._media_override.disable()
            cls._media_dir.cleanup()

    def generate(self, date_value=None, seed=42, reset=False):
        output = StringIO()
        call_command("generate_demo_data", reference_date=(date_value or self.T0).isoformat(),
                     seed=seed, reset=reset, stdout=output)
        return output.getvalue()

    def snapshot(self):
        return {
            "people": list(Employee.objects.order_by("first_name", "last_name").values_list(
                "first_name", "last_name", "entry_date", "exit_date")),
            "projects": list(Project.objects.order_by("name").values_list("name", "start_date", "end_date")),
            "funds": list(Fund.objects.order_by("ref").values_list("ref", "amount", "expense")),
        }

    def test_generation_scenarios_permissions_and_dashboard_sources(self):
        self.assertIn("33 employees, 20 projects, 14 funds", self.generate())
        self.assertGreaterEqual(Expense.objects.count(), 40)
        history = AmountHistory.objects.filter(content_type=ContentType.objects.get_for_model(Expense_point))
        self.assertGreater(history.count(), 80)
        self.assertGreater(history.values("value_date").distinct().count(), 8)
        self.assertEqual(Dashboard.objects.count(), 3)
        roles = {"admin": "Lab_admin", "labmanager": "Lab_Manager",
                 "leader": "Lab_leader", "employee": "Lab_employee"}
        User = get_user_model()
        for username, role in roles.items():
            user = User.objects.get(username=username)
            self.assertTrue(user.groups.filter(name=role).exists())
            self.assertTrue(user.groups.filter(name="favorite_notif_perm").exists())
        self.assertTrue(Group.objects.filter(name="Lab_admin").exists())
        self.assertTrue(Project.objects.filter(status=True, end_date__gt=self.T0).exists())
        self.assertTrue(Project.objects.filter(end_date__lt=self.T0).exists())
        self.assertTrue(Milestones.objects.filter(status=False, end_date__lt=self.T0).exists())
        self.assertTrue(Milestones.objects.filter(status=False, end_date__gt=self.T0).exists())
        self.assertTrue(Fund.objects.filter(end_date__range=(self.T0, self.T0 + timedelta(days=35))).exists())
        bridge = Fund.objects.get(ref="DM-ORION-BRIDGE")
        helix = Fund.objects.get(ref="DM-HELIX-GRANT")
        self.assertGreater(abs(bridge.expense) / bridge.amount, Decimal("0.9"))
        self.assertLess(abs(helix.expense) / helix.amount, Decimal("0.3"))
        self.assertTrue(Contract.objects.filter(end_date__range=(self.T0, self.T0 + timedelta(days=30))).exists())
        self.assertTrue(Leave.objects.filter(start_date__gt=self.T0).exists())
        leader = User.objects.get(username="leader")
        self.assertTrue(Employee_Superior.objects.filter(superior__user=leader).exists())
        with patch("dashboard.business_sources.timezone.localdate", return_value=self.T0):
            employee_context = DashboardContext.personal(User.objects.get(username="employee"))
            leader_context = DashboardContext.personal(leader)
            self.assertTrue(business_sources.projects(employee_context, {"scope": "participated"})["__renderers__"]["kpi"]["value"])
            self.assertTrue(business_sources.projects(leader_context, {"scope": "managed", "late_only": True})["__renderers__"]["kpi"]["value"])
            self.assertTrue(business_sources.milestones(employee_context, {"scope": "mine", "due_within_days": "30"})["__renderers__"]["kpi"]["value"])
            self.assertTrue(business_sources.tasks(employee_context, {"scope": "mine"})["__renderers__"]["kpi"]["value"])
            self.assertTrue(business_sources.leaves(employee_context, {"scope": "mine"})["__renderers__"]["kpi"]["value"])
            self.assertTrue(business_sources.funds(leader_context, {"scope": "managed_projects"})["__renderers__"]["kpi"]["value"])
            self.assertTrue(business_sources.contracts(leader_context, {"ending_within_days": "30"})["__renderers__"]["kpi"]["value"])

    def test_reset_determinism_seed_and_relative_dates(self):
        self.generate()
        first = self.snapshot()
        with self.assertRaisesMessage(CommandError, "Existing operational data"):
            self.generate()
        self.generate(reset=True)
        self.assertEqual(first, self.snapshot())
        self.assertEqual(Dashboard.objects.count(), 3)
        self.generate(seed=43, reset=True)
        changed = self.snapshot()
        self.assertNotEqual(first["people"], changed["people"])
        self.assertNotEqual(first["funds"], changed["funds"])
        self.generate(date_value=self.T0 + timedelta(days=180), reset=True)
        shifted = self.snapshot()
        self.assertEqual([row[0] for row in first["projects"]], [row[0] for row in shifted["projects"]])
        self.assertEqual(shifted["projects"][0][1] - first["projects"][0][1], timedelta(days=180))

    def test_report_templates_are_available_for_demo_records(self):
        self.generate()
        employee = Employee.objects.get(first_name="Camille", last_name="ORREN")
        project = Project.objects.get(name="ORION — Optical Resilience")
        manager = get_user_model().objects.get(username="labmanager")
        client = APIClient()
        client.force_authenticate(manager)

        for entity, record, format_name, model, report_name, extension in (
            ("employee", employee, "word", EmployeeWordReport, "Demo Employee Report", ".docx"),
            ("project", project, "pdf", ProjectPDFReport, "Demo Project Report", ".html"),
        ):
            report = model.objects.get(name=report_name)
            report.full_clean()
            self.assertTrue(report.template.storage.exists(report.template.name))
            self.assertTrue(report.template.name.endswith(extension))
            response = client.get(f"/api/v1/reports/{entity}/{record.pk}/{format_name}/")
            self.assertEqual(response.status_code, 200)
            self.assertIn(report.pk, [item["id"] for item in response.json()["templates"]])

        first_ids = (EmployeeWordReport.objects.get(name="Demo Employee Report").pk,
                     ProjectPDFReport.objects.get(name="Demo Project Report").pk)
        self.generate(reset=True)
        self.assertEqual(first_ids, (EmployeeWordReport.objects.get(name="Demo Employee Report").pk,
                                     ProjectPDFReport.objects.get(name="Demo Project Report").pk))
        self.assertEqual(EmployeeWordReport.objects.filter(name="Demo Employee Report").count(), 1)
        self.assertEqual(ProjectPDFReport.objects.filter(name="Demo Project Report").count(), 1)

    def test_stable_namespaced_rng_and_reset_guard(self):
        ctx = DemoContext(self.T0, 42)
        self.assertEqual(ctx.rng_for("people", "a").randint(0, 10**12),
                         ctx.rng_for("people", "a").randint(0, 10**12))
        self.assertNotEqual(ctx.rng_for("people", "a").randint(0, 10**12),
                            ctx.rng_for("people", "b").randint(0, 10**12))
        with override_settings(DEBUG=False), patch("labsmanager.demo_data.runner.connection") as conn:
            conn.settings_dict = {"NAME": "production"}
            with self.assertRaisesMessage(CommandError, "Refusing --reset"):
                self.generate(reset=True)
