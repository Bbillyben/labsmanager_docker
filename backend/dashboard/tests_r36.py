"""Focused R3.6 Project context, financial history and plugin tests."""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from expense.models import Expense_point
from fund.models import AmountHistory, Cost_Type, Fund, Fund_Institution
from project.models import Institution, Participant, Project
from staff.models import Employee

from .financial_sources import advancement_for_funds, expense_trend
from .context_service import context_lookup
from .models import Dashboard
from .registry import DashboardContext, DataSource, available_definitions


class AdvancementTests(SimpleTestCase):
    today = date(2026, 10, 4)

    def fund(self, amount, expense, start=-50, end=50):
        return SimpleNamespace(amount=Decimal(amount), expense=Decimal(expense),
                               start_date=self.today + timedelta(days=start) if start is not None else None,
                               end_date=self.today + timedelta(days=end) if end is not None else None)

    def test_ratio_and_amount_weighted_aggregation(self):
        self.assertAlmostEqual(advancement_for_funds([self.fund("100", "-50")], self.today)["ratio"], 1)
        self.assertLess(advancement_for_funds([self.fund("100", "-25")], self.today)["ratio"], 1)
        self.assertGreater(advancement_for_funds([self.fund("100", "-75")], self.today)["ratio"], 1)
        result = advancement_for_funds([self.fund("100", "-50"), self.fund("300", "-75")], self.today)
        self.assertAlmostEqual(result["ratio"], 125 / 200)
        self.assertAlmostEqual(result["budget_percent"], 31.25)

    def test_unavailable_and_boundary_dates(self):
        self.assertIsNone(advancement_for_funds([self.fund("0", "0")], self.today))
        self.assertIsNone(advancement_for_funds([self.fund("100", "-30", start=None)], self.today))
        self.assertIsNone(advancement_for_funds([self.fund("100", "-30", start=0, end=0)], self.today))
        self.assertIsNone(advancement_for_funds([self.fund("100", "-30", start=5, end=50)], self.today))
        self.assertAlmostEqual(advancement_for_funds([self.fund("100", "-120", start=-100, end=-1)], self.today)["ratio"], 1.2)


class ProjectDashboardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="project-dashboard-owner", password="test")
        self.hidden_user = User.objects.create_user(username="project-dashboard-hidden", password="test")
        self.employee = Employee.objects.create(first_name="Demo", last_name="Owner", user=self.user)
        self.project = Project.objects.create(name="Visible dashboard project", status=True)
        self.hidden_project = Project.objects.create(name="Hidden dashboard project", status=True)
        Participant.objects.create(project=self.project, employee=self.employee, status="l")
        self.institution = Institution.objects.create(short_name="R36A", name="Institute A")
        self.other_institution = Institution.objects.create(short_name="R36B", name="Institute B")
        self.funder = Fund_Institution.objects.create(short_name="R36F", name="Funder")
        self.cost = Cost_Type.objects.create(short_name="R36C", name="Personnel", is_hr=True)
        self.other_cost = Cost_Type.objects.create(short_name="R36D", name="Equipment")
        today = timezone.localdate()
        self.fund = Fund.objects.create(project=self.project, institution=self.institution, funder=self.funder,
                                        ref="VISIBLE", start_date=today - timedelta(days=90), end_date=today + timedelta(days=90))
        self.other_fund = Fund.objects.create(project=self.project, institution=self.other_institution, funder=self.funder,
                                              ref="OTHER", start_date=today - timedelta(days=90), end_date=today + timedelta(days=90))
        self.hidden_fund = Fund.objects.create(project=self.hidden_project, institution=self.institution, funder=self.funder,
                                               ref="HIDDEN", start_date=today - timedelta(days=90), end_date=today + timedelta(days=90))
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_project_dashboard_template_scope_and_denial(self):
        response = self.client.get(f"/api/v1/projects/{self.project.pk}/dashboard/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["scope"], "project")
        self.assertEqual(response.data["project_id"], self.project.pk)
        stored = Dashboard.objects.get(pk=response.data["id"])
        self.assertEqual(stored.context_object, self.project)
        self.assertEqual(stored.owner, self.user)
        self.assertEqual(len(response.data["widgets"]), 7)
        self.assertEqual([(item["source_key"], item["renderer_key"]) for item in response.data["widgets"]], [
            ("core.projects", "project-health-bars"), ("core.timeline", "calendar-grid"),
            ("core.tasks", "task-workload"), ("core.milestones", "deadline-list"),
            ("core.funds", "overview-list"), ("core.contracts", "contract-list"),
            ("core.expense-trend", "line-chart"),
        ])
        timeline_config = response.data["widgets"][1]["config"]
        self.assertEqual(timeline_config["tasks_project_scope"], "context")
        self.assertEqual(timeline_config["milestones_project_scope"], "context")
        rectangles = []
        for widget in response.data["widgets"]:
            self.assertLessEqual(widget["x"] + widget["width"], 12)
            box = (widget["x"], widget["y"], widget["x"] + widget["width"], widget["y"] + widget["height"])
            for other in rectangles:
                self.assertTrue(box[2] <= other[0] or other[2] <= box[0] or box[3] <= other[1] or other[3] <= box[1])
            rectangles.append(box)
        self.assertEqual(Dashboard.objects.filter(owner=self.user, scope="user").count(), 0)
        self.assertEqual(self.client.get(f"/api/v1/projects/{self.project.pk}/dashboard/").data["id"], response.data["id"])
        self.assertEqual(self.client.get(f"/api/v1/projects/{self.hidden_project.pk}/dashboard/").status_code, 404)
        self.client.force_authenticate(self.hidden_user)
        self.assertEqual(self.client.get(f"/api/v1/projects/{self.project.pk}/dashboard/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/dashboards/{response.data['id']}/").status_code, 404)

    def test_personal_and_future_context_storage_and_project_cascade(self):
        personal = Dashboard.objects.create(owner=self.user, name="Personal")
        self.assertIsNone(personal.context_content_type_id)
        self.assertIsNone(personal.context_object_id)
        self.assertIsNone(personal.context_object)
        future = Dashboard.objects.create(owner=self.user, name="Future employee", scope="employee",
                                          **context_lookup(self.employee))
        self.assertEqual(future.context_object, self.employee)
        self.assertEqual(DashboardContext.for_object(self.user, self.employee).scope, "employee")
        doomed_project = Project.objects.create(name="Context cascade")
        doomed = Dashboard.objects.create(owner=self.user, name="Doomed", scope="project",
                                          **context_lookup(doomed_project))
        doomed_project.delete()
        self.assertFalse(Dashboard.objects.filter(pk=doomed.pk).exists())
        self.assertEqual(Dashboard.objects.filter(pk__in=(personal.pk, future.pk)).count(), 2)

    def test_specific_project_options_and_widget_validation(self):
        dashboard = self.client.get(f"/api/v1/projects/{self.project.pk}/dashboard/").data
        catalog = self.client.get(f"/api/v1/projects/{self.project.pk}/dashboard/catalog/").data
        self.assertEqual([item["id"] for item in catalog["project_options"]], [self.project.pk])
        self.assertIn("core.expense-trend", {source["key"] for source in catalog["sources"]})
        endpoint = f"/api/v1/dashboards/{dashboard['id']}/widgets/"
        valid = self.client.post(endpoint, {"source_key": "core.expense-trend", "renderer_key": "line-chart",
                                            "config": {"project_scope": "specific_project", "project_id": self.project.pk}}, format="json")
        self.assertEqual(valid.status_code, 201, valid.data)
        denied = self.client.post(endpoint, {"source_key": "core.expense-trend", "renderer_key": "line-chart",
                                             "config": {"project_scope": "specific_project", "project_id": self.hidden_project.pk}}, format="json")
        self.assertEqual(denied.status_code, 400)
        self.assertEqual(self.client.delete(f"/api/v1/dashboards/{dashboard['id']}/").status_code, 400)

    def test_admin_navigation_capability_is_reported_by_backend(self):
        normal = self.client.get("/api/v1/me/").data
        self.assertFalse(normal["can_access_admin"])
        self.assertIsNone(normal["admin_url"])
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        staff = self.client.get("/api/v1/me/").data
        self.assertTrue(staff["can_access_admin"])
        self.assertEqual(staff["admin_url"], "/admin/")

    def test_history_effective_date_modes_groups_and_visibility(self):
        today = timezone.localdate()
        old = (today.replace(day=1) - timedelta(days=1)).replace(day=15)
        current = today.replace(day=2)
        first = Expense_point.objects.create(fund=self.fund, type=self.cost, amount=0, entry_date=old, value_date=old)
        second = Expense_point.objects.create(fund=self.fund, type=self.other_cost, amount=0, entry_date=old, value_date=old)
        third = Expense_point.objects.create(fund=self.other_fund, type=self.cost, amount=0, entry_date=old, value_date=old)
        hidden = Expense_point.objects.create(fund=self.hidden_fund, type=self.cost, amount=0, entry_date=old, value_date=old)
        AmountHistory.objects.create(content_object=first, amount=-30, delta=-30, value_date=old)
        AmountHistory.objects.create(content_object=first, amount=-50, delta=-20, value_date=current)
        AmountHistory.objects.create(content_object=second, amount=-10, delta=-10, value_date=old)
        AmountHistory.objects.create(content_object=third, amount=-15, delta=-15, value_date=current)
        AmountHistory.objects.create(content_object=hidden, amount=-999, delta=-999, value_date=old)
        context = DashboardContext.for_project(self.user, self.project)
        config = {"project_scope": "context", "display": "cumulative", "group_by": "total", "months": 3}
        total = expense_trend(context, config)
        self.assertEqual(total["series"][0]["points"][-1]["value"], 75)
        self.assertNotIn("999", str(total))
        period = expense_trend(context, {**config, "display": "period"})
        self.assertEqual(period["series"][0]["points"][-1]["value"], 35)
        for group, expected in (("fund", 2), ("cost_type", 2), ("institution", 2)):
            self.assertEqual(len([item for item in expense_trend(context, {**config, "group_by": group})["series"] if item.get("kind") != "reference"]), expected)
        fallback = AmountHistory.objects.create(content_object=first, amount=-55, delta=-5, value_date=None)
        self.assertEqual(fallback.created_at, today)
        self.assertEqual(expense_trend(context, config)["series"][0]["points"][-1]["value"], 80)

    def test_plugin_sources_follow_context_without_core_changes(self):
        received = []

        class Plugin:
            def get_dashboard_sources(self, context):
                return tuple(DataSource(f"fake.{key}", key, "Test", scopes, ("kpi",),
                                        lambda current, config: received.append(current) or {"value": 1},
                                        default_renderer="kpi") for key, scopes in (
                                            ("user", ("user",)), ("project", ("project",)),
                                            ("both", ("user", "project"))))

            def get_dashboard_widgets(self, context):
                return ()

        with patch("plugin.registry.registry.with_mixin", return_value=[Plugin()]):
            user_sources, user_defs = available_definitions(DashboardContext.personal(self.user))
            project_sources, project_defs = available_definitions(DashboardContext.for_project(self.user, self.project))
            self.assertIn("fake.user", {item.source_key for item in user_defs.values()})
            self.assertNotIn("fake.project", {item.source_key for item in user_defs.values()})
            self.assertIn("fake.project", {item.source_key for item in project_defs.values()})
            self.assertNotIn("fake.user", {item.source_key for item in project_defs.values()})
            self.assertIn("fake.both", {item.source_key for item in user_defs.values()})
            self.assertIn("fake.both", {item.source_key for item in project_defs.values()})
            project_sources["fake.project"].provider(DashboardContext.for_project(self.user, self.project), {})
            self.assertIs(received[-1].project, self.project)
