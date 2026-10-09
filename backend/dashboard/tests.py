from unittest.mock import patch
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Dashboard, WidgetInstance
from .registry import (DashboardContext, CORE_WIDGETS, TEMPLATES, TemplateWidget,
                       available_definitions, dashboard_registry, definition_for_template,
                       DataSource, WidgetDefinition)
from .api_v1 import validated_config
from .template_service import _find_free_position, _fits_position, _template_size
from . import business_sources
from rest_framework.exceptions import ValidationError


class DashboardProjectHealthHelperTests(SimpleTestCase):
    def test_deadline_and_pace_boundaries(self):
        today = timezone.localdate()
        relative = business_sources._project_deadline_relative
        self.assertEqual(relative({"start_date": (today + timedelta(days=5)).isoformat(),
                                   "end_date": (today + timedelta(days=100)).isoformat()}, today),
                         {"state": "starts_in", "count": 5, "unit": "days"})
        self.assertEqual(relative({"start_date": None, "end_date": today.isoformat()}, today)["state"], "ends_today")
        self.assertEqual(relative({"start_date": None, "end_date": (today - timedelta(days=3)).isoformat()}, today),
                         {"state": "ended_ago", "count": 3, "unit": "days"})
        self.assertEqual(relative({"start_date": None, "end_date": None}, today)["state"], "unknown")
        project = SimpleNamespace(start_date=today, end_date=today + timedelta(days=100))
        self.assertEqual(business_sources._project_temporal_percent(project, today), 0.0)
        project.end_date = None
        self.assertIsNone(business_sources._project_temporal_percent(project, today))
        pace = business_sources._project_funding_pace
        self.assertEqual(pace({"temporal_percent": 50, "financial": {"percent": 25}}),
                         {"applicable": True, "ratio": 0.5, "state": "below", "tone": "danger"})
        self.assertEqual(pace({"temporal_percent": 0.5, "financial": {"percent": 25}})["state"], "not_applicable")
        self.assertEqual(pace({"temporal_percent": 50, "financial": None})["state"], "not_applicable")


class DashboardTemplatePlacementTests(SimpleTestCase):
    def test_size_defaults_and_clamps_to_definition_and_grid(self):
        definition = WidgetDefinition("test", "Test", "Test", "kpi", "test.source",
                                      default_size=(4, 3), min_size=(2, 2), max_size=(8, 6))
        item = lambda **layout: TemplateWidget("test.source", "kpi", **layout)
        self.assertEqual(_template_size(item(), definition), (4, 3))
        self.assertEqual(_template_size(item(width=30, height=20), definition), (8, 6))
        self.assertEqual(_template_size(item(width=1, height=1), definition), (2, 2))
        self.assertEqual(_template_size(item(width=7), definition), (7, 3))
        wide = WidgetDefinition("wide", "Wide", "Test", "kpi", "test.source", max_size=(24, 24))
        self.assertEqual(_template_size(item(width=30), wide), (12, 3))

    def test_position_checks_boundaries_collisions_and_first_free_cell(self):
        occupied = [(0, 0, 12, 7), (0, 7, 6, 5)]
        self.assertFalse(_fits_position(-1, 0, 4, 3, occupied))
        self.assertFalse(_fits_position(0, -1, 4, 3, occupied))
        self.assertFalse(_fits_position(9, 7, 4, 3, occupied))
        self.assertFalse(_fits_position(6, 3, 6, 5, occupied))
        self.assertTrue(_fits_position(6, 7, 4, 3, occupied))
        self.assertEqual(_find_free_position(4, 3, occupied), (6, 7))


class DashboardApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="dashboard-owner", password="test")
        self.other = User.objects.create_user(username="dashboard-other", password="test")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def create(self, name="Personal", template="employee"):
        response = self.client.post("/api/v1/dashboards/", {"name": name, "template": template}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def test_templates_are_copied_and_multiple_dashboards_are_owned(self):
        expected = {"employee": 5, "leader": 8, "lab-manager": 6, "blank": 0}
        ids = [self.create(name, name) for name in expected]
        self.assertEqual(Dashboard.objects.filter(owner=self.user).count(), 4)
        self.assertEqual(Dashboard.objects.filter(owner=self.user, is_default=True).count(), 1)
        for (name, count), pk in zip(expected.items(), ids):
            self.assertEqual(Dashboard.objects.get(pk=pk).widgets.count(), count)
        leader_detail = self.client.get(f"/api/v1/dashboards/{ids[1]}/")
        self.assertEqual(leader_detail.status_code, 200)
        health = next(item for item in leader_detail.data["widgets"] if item["source_key"] == "core.projects")
        self.assertEqual(health["renderer_key"], "project-health-bars")
        self.assertEqual(health["data"]["summary"]["count"], 0)
        self.assertEqual([row["id"] for row in self.client.get("/api/v1/dashboards/").data], ids)
        self.assertEqual(CORE_WIDGETS[0].key, "core.quick-links")

    def test_default_reorder_duplicate_and_delete(self):
        first = self.create()
        second = self.create("Blank", "blank")
        self.assertEqual(self.client.post(f"/api/v1/dashboards/{second}/default/").status_code, 200)
        self.assertFalse(Dashboard.objects.get(pk=first).is_default)
        self.assertEqual(self.client.patch("/api/v1/dashboards/reorder/", {"ids": [second, first]}, format="json").status_code, 200)
        self.assertEqual(list(Dashboard.objects.filter(owner=self.user).values_list("pk", flat=True)), [second, first])
        duplicate = self.client.post(f"/api/v1/dashboards/{first}/duplicate/")
        self.assertEqual(duplicate.status_code, 201)
        copied = Dashboard.objects.get(pk=duplicate.data["id"])
        self.assertFalse(copied.is_default)
        self.assertEqual(copied.widgets.count(), 5)
        self.assertFalse(set(copied.widgets.values_list("pk", flat=True)) & set(Dashboard.objects.get(pk=first).widgets.values_list("pk", flat=True)))
        self.assertEqual(self.client.delete(f"/api/v1/dashboards/{second}/").status_code, 204)
        self.assertTrue(Dashboard.objects.get(pk=first).is_default)
        self.client.delete(f"/api/v1/dashboards/{first}/")
        self.client.delete(f"/api/v1/dashboards/{copied.pk}/")
        self.assertEqual(Dashboard.objects.filter(owner=self.user).count(), 0)

    def test_database_rejects_two_defaults(self):
        self.create()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Dashboard.objects.create(owner=self.user, name="Invalid", is_default=True)

    def test_list_repairs_legacy_missing_default_deterministically(self):
        first = Dashboard.objects.create(owner=self.user, name="Later", position=5)
        earlier = Dashboard.objects.create(owner=self.user, name="Earlier", position=2)
        response = self.client.get("/api/v1/dashboards/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], earlier.pk)
        self.assertTrue(Dashboard.objects.get(pk=earlier.pk).is_default)
        self.assertFalse(Dashboard.objects.get(pk=first.pk).is_default)

    def test_widgets_layout_config_and_missing_definition(self):
        pk = self.create("Blank", "blank")
        endpoint = f"/api/v1/dashboards/{pk}/widgets/"
        first = self.client.post(endpoint, {"definition_key": "core.note"}, format="json")
        second = self.client.post(endpoint, {"definition_key": "core.note"}, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertNotEqual(first.data["id"], second.data["id"])
        self.assertEqual(self.client.post(endpoint, {"definition_key": "core.quick-links"}, format="json").status_code, 201)
        self.assertEqual(self.client.post(endpoint, {"definition_key": "core.quick-links"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(f'{endpoint}{first.data["id"]}/', {"title": "My note", "config": {"message": "Hello"}}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(f'{endpoint}{first.data["id"]}/', {"config": {"unknown": "x"}}, format="json").status_code, 400)
        rows = [{"id": first.data["id"], "x": 2, "y": 4, "width": 5, "height": 3, "logical_order": 2}]
        self.assertEqual(self.client.patch(f"/api/v1/dashboards/{pk}/layout/", {"widgets": rows}, format="json").status_code, 200)
        self.assertEqual(WidgetInstance.objects.get(pk=first.data["id"]).x, 2)
        bad = [{**rows[0], "width": 13}]
        self.assertEqual(self.client.patch(f"/api/v1/dashboards/{pk}/layout/", {"widgets": bad}, format="json").status_code, 400)
        missing = WidgetInstance.objects.create(dashboard_id=pk, definition_key="missing.plugin.widget", renderer_key="empty")
        detail = self.client.get(f"/api/v1/dashboards/{pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertFalse(next(item for item in detail.data["widgets"] if item["id"] == str(missing.pk))["available"])
        self.assertEqual(self.client.delete(f"{endpoint}{missing.pk}/").status_code, 204)

    def test_other_owner_is_hidden_and_catalog_is_filtered(self):
        pk = self.create()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/v1/dashboards/{pk}/").status_code, 404)
        self.assertEqual(self.client.patch(f"/api/v1/dashboards/{pk}/", {"name": "x"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/v1/dashboards/{pk}/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/v1/dashboards/{pk}/duplicate/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/v1/dashboards/{pk}/widgets/", {"definition_key": "core.note"}, format="json").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/dashboards/").data, [])
        catalog = self.client.get("/api/v1/dashboards/catalog/")
        self.assertEqual(catalog.status_code, 200)
        self.assertEqual(catalog.data["scope"], "user")
        keys = {item["key"] for item in catalog.data["definitions"]}
        self.assertTrue({"core.note", "core.expense-trend", "core.financial-advancement"}.issubset(keys))

    def test_registry_context_and_plugin_contract(self):
        context = DashboardContext.personal(self.user)
        self.assertEqual(context.scope, "user")
        _, available = available_definitions(context)
        self.assertIn("core.note", available)
        with patch("dashboard.registry.dashboard_registry", return_value=({}, {"core.note": CORE_WIDGETS[1]})):
            _, filtered = available_definitions(context)
            self.assertNotIn("core.note", filtered)
        from plugin.base.DashboardPluginMixin import DashboardPluginMixin
        self.assertTrue(callable(DashboardPluginMixin.get_dashboard_sources))
        self.assertTrue(callable(DashboardPluginMixin.get_dashboard_widgets))

        class PilotPlugin:
            def get_dashboard_sources(self, context):
                return [DataSource("pilot.source", "Pilot", "Test", ("user",), ("empty",), lambda context, config: {})]

            def get_dashboard_widgets(self, context):
                return [WidgetDefinition("pilot.widget", "Pilot", "Test", "empty", "pilot.source")]

        from plugin import registry as plugin_registry
        with patch.object(plugin_registry, "with_mixin", return_value=[PilotPlugin()]):
            sources, widgets = dashboard_registry(context)
            self.assertIn("pilot.source", sources)
            self.assertIn("pilot.widget", widgets)

        class BrokenPlugin(PilotPlugin):
            def get_dashboard_widgets(self, context):
                return [WidgetDefinition("core.note", "Duplicate", "Test", "empty", "pilot.source")]

        with patch.object(plugin_registry, "with_mixin", return_value=[BrokenPlugin()]):
            _, widgets = dashboard_registry(context)
            self.assertIn("core.note", widgets)
            self.assertNotIn("pilot.widget", widgets)
        self.assertNotIn("core.note", available_definitions(DashboardContext("project", self.user))[1])

        class SourceOnlyPlugin(PilotPlugin):
            def get_dashboard_widgets(self, context):
                return []

        with patch.object(plugin_registry, "with_mixin", return_value=[SourceOnlyPlugin()]):
            sources, widgets = dashboard_registry(context)
            self.assertIn("pilot.source", sources)
            self.assertIn("pilot.source", widgets)
            self.assertEqual(widgets["pilot.source"].renderer_key, "empty")

    def test_declarative_configuration_defaults_required_choices_and_unknown(self):
        source = DataSource("test.source", "Test", "Test", ("user",), ("kpi",), lambda context, config: {},
                            config_fields={"required": {"type": "string", "required": True},
                                           "choice": {"type": "choice", "choices": ["a", "b"], "default": "a"},
                                           "limit": {"type": "integer", "min": 1, "max": 5, "default": 2}})
        definition = WidgetDefinition("test.widget", "Test", "Test", "kpi", "test.source")
        self.assertEqual(validated_config({"required": "yes"}, source, definition, "kpi"), {"required": "yes", "choice": "a", "limit": 2})
        for invalid in ({}, {"required": "yes", "choice": "z"}, {"required": "yes", "limit": 6}, {"required": "yes", "unknown": 1}):
            with self.assertRaises(ValidationError):
                validated_config(invalid, source, definition, "kpi")

    def test_same_project_source_supports_two_renderers_and_validates_config(self):
        from project.models import Project
        visible = Project.objects.create(name="A visible dashboard project", status=True)
        inactive = Project.objects.create(name="B inactive dashboard project", status=False)
        hidden = Project.objects.create(name="Hidden dashboard project", status=True)
        with patch.object(Project, "get_instances_for_user", return_value=Project.objects.exclude(pk=hidden.pk)):
            pk = self.create("Blank", "blank")
            endpoint = f"/api/v1/dashboards/{pk}/widgets/"
            kpi = self.client.post(endpoint, {"source_key": "core.projects", "renderer_key": "kpi",
                                              "config": {"active_only": True, "limit": 3}}, format="json")
            listing = self.client.post(endpoint, {"source_key": "core.projects", "renderer_key": "compact-list", "config": {"limit": 1}}, format="json")
            self.assertEqual(kpi.status_code, 201, kpi.data)
            self.assertEqual(listing.status_code, 201, listing.data)
            self.assertEqual(kpi.data["data"]["value"], 1)
            self.assertEqual([item["label"] for item in listing.data["data"]["items"]], [visible.name])
            self.assertNotIn(hidden.name, str(listing.data["data"]))
            self.assertNotIn(inactive.name, str(listing.data["data"]))
            self.assertEqual(kpi.data["source_key"], listing.data["source_key"])
            self.assertEqual(self.client.post(endpoint, {"source_key": "core.projects", "renderer_key": "progress-list"}, format="json").status_code, 400)
            self.assertEqual(self.client.post(endpoint, {"source_key": "core.projects", "config": {"limit": 0}}, format="json").status_code, 400)
            self.assertEqual(self.client.post(endpoint, {"source_key": "core.projects", "config": {"active_only": "yes"}}, format="json").status_code, 400)
            self.assertEqual(self.client.post(endpoint, {"source_key": "core.projects", "config": {"scope": "forbidden"}}, format="json").status_code, 400)
            self.assertEqual(self.client.post(endpoint, {"source_key": "core.projects", "config": {"unknown": 1}}, format="json").status_code, 400)
            change = self.client.patch(f'{endpoint}{kpi.data["id"]}/', {"renderer_key": "compact-list"}, format="json")
            self.assertEqual(change.status_code, 200, change.data)
            self.assertEqual(change.data["id"], kpi.data["id"])
            self.assertEqual(change.data["data"]["items"][0]["label"], visible.name)
            self.assertEqual(WidgetInstance.objects.get(pk=kpi.data["id"]).renderer_key, "compact-list")

    def test_funding_overview_accepts_existing_fund_configuration(self):
        pk = self.create("Blank", "blank")
        catalog = self.client.get("/api/v1/dashboards/catalog/")
        funding = next(item for item in catalog.data["definitions"] if item["key"] == "core.funds")
        self.assertEqual(funding["default_size"], (6, 5))
        config = {"project_scope": "all_visible", "scope": "managed_projects",
                  "active_only": True, "ending_within_days": "60", "limit": 3}
        response = self.client.post(f"/api/v1/dashboards/{pk}/widgets/",
                                    {"source_key": "core.funds", "renderer_key": "overview-list",
                                     "config": config}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["config"], config)
        self.assertEqual(response.data["data"]["summary"]["count"], 0)

    def test_deadline_timeline_accepts_existing_milestone_configuration(self):
        pk = self.create("Blank", "blank")
        config = {"project_scope": "all_visible", "scope": "mine", "status": "all",
                  "overdue_only": False, "due_within_days": "30", "limit": 4}
        response = self.client.post(f"/api/v1/dashboards/{pk}/widgets/",
                                    {"source_key": "core.milestones", "renderer_key": "deadline-list",
                                     "config": config}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["config"], config)
        self.assertEqual(response.data["data"]["summary"]["count"], 0)

    def test_new_templates_are_copied_without_changing_existing_dashboards(self):
        old = self.create("Existing", "blank")
        WidgetInstance.objects.create(dashboard_id=old, definition_key="core.note", source_key="core.note", renderer_key="empty")
        for template, expected in (("employee", 5), ("leader", 8), ("lab-manager", 6), ("blank", 0)):
            pk = self.create(template, template)
            self.assertEqual(Dashboard.objects.get(pk=pk).widgets.count(), expected)
            detail = self.client.get(f"/api/v1/dashboards/{pk}/")
            self.assertEqual(detail.status_code, 200)
            self.assertFalse(any(item["error"] for item in detail.data["widgets"]))
        self.assertEqual(Dashboard.objects.get(pk=old).widgets.count(), 1)

    def test_business_templates_preserve_config_and_layout_atomically(self):
        self.assertIsNone(TemplateWidget.__hash__)
        self.assertIsNone(DataSource.__hash__)
        self.assertIsNone(WidgetDefinition.__hash__)
        for template in ("employee", "leader", "lab-manager", "blank"):
            pk = self.create(template, template)
            widgets = list(Dashboard.objects.get(pk=pk).widgets.order_by("logical_order"))
            expected_items = [item for item in TEMPLATES[template]
                              if not (item.source_key == "core.employee-workload" and item.config.get("scope") == "single")
                              and item.source_key != "core.data-consistency"]
            self.assertEqual(len(widgets), len(expected_items))
            rectangles = []
            for index, (widget, item) in enumerate(zip(widgets, expected_items)):
                self.assertEqual((widget.source_key, widget.renderer_key, widget.title),
                                 (item.source_key, item.renderer_key, item.title))
                self.assertEqual(widget.logical_order, index)
                self.assertLessEqual(widget.x + widget.width, 12)
                box = (widget.x, widget.y, widget.x + widget.width, widget.y + widget.height)
                for other in rectangles:
                    self.assertTrue(box[2] <= other[0] or other[2] <= box[0] or box[3] <= other[1] or other[3] <= box[1])
                rectangles.append(box)
                for key, value in item.config.items():
                    self.assertEqual(widget.config[key], value)

        before = Dashboard.objects.filter(owner=self.user).count()
        with patch("dashboard.api_v1.validated_config", side_effect=ValidationError({"config": "Invalid template"})):
            response = self.client.post("/api/v1/dashboards/", {"name": "Broken", "template": "employee"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Dashboard.objects.filter(owner=self.user).count(), before)

    def test_employee_template_resolves_visible_self_and_keeps_all_four_metrics(self):
        from staff.models import Employee
        employee = Employee.objects.create(first_name="Template", last_name="Employee", user=self.user)
        pk = self.create("Employee", "employee")
        widgets = list(Dashboard.objects.get(pk=pk).widgets.order_by("logical_order"))
        self.assertEqual([(item.source_key, item.renderer_key) for item in widgets], [
            ("core.employee-workload", "employee-workload"), ("core.projects", "project-portfolio"),
            ("core.tasks", "task-workload"), ("core.milestones", "deadline-list"),
            ("core.timeline", "calendar-grid"), ("core.leaves", "compact-list"),
        ])
        self.assertEqual(widgets[0].config["employee_id"], employee.pk)
        detail = self.client.get(f"/api/v1/dashboards/{pk}/")
        self.assertEqual([metric["key"] for metric in detail.data["widgets"][0]["data"]["metrics"]], [
            "project_allocation", "open_tasks", "open_milestones", "open_work_items",
        ])
        self.assertFalse(any(item["error"] for item in detail.data["widgets"]))

    def test_template_renderers_match_catalog_and_admin_widget_is_capability_gated(self):
        sources, _ = available_definitions(DashboardContext.personal(self.user))
        for template, items in TEMPLATES.items():
            for item in items:
                self.assertIn(item.renderer_key, sources[item.source_key].compatible_renderers,
                              (template, item.source_key, item.renderer_key))
        self.assertEqual(TEMPLATES["blank"], ())
        self.assertNotIn("core.data-consistency", Dashboard.objects.get(
            pk=self.create("Manager", "lab-manager")
        ).widgets.values_list("source_key", flat=True))
        self.user.is_staff = True
        self.user.save(update_fields=("is_staff",))
        manager = Dashboard.objects.get(pk=self.create("Staff manager", "lab-manager"))
        self.assertIn("core.data-consistency", manager.widgets.values_list("source_key", flat=True))

    def test_template_layout_uses_explicit_positions_and_falls_back_without_overlap(self):
        layout = (
            TemplateWidget("core.tasks", "task-workload", x=0, y=0, width=12, height=7),
            TemplateWidget("core.milestones", "deadline-list", x=6, y=3, width=6, height=5),
            TemplateWidget("core.funds", "overview-list", x=11, y=0, width=30, height=1),
            TemplateWidget("core.contracts", "contract-list", x=3),
            TemplateWidget("core.projects", "project-portfolio", y=2),
        )
        with patch.dict(TEMPLATES, {"layout-case": layout}):
            dashboard = Dashboard.objects.get(pk=self.create("Layout", "layout-case"))
        widgets = list(dashboard.widgets.order_by("logical_order"))
        self.assertEqual([(item.x, item.y, item.width, item.height) for item in widgets], [
            (0, 0, 12, 7), (0, 7, 6, 5), (0, 12, 12, 2), (6, 7, 4, 3), (0, 14, 6, 5),
        ])
        self.assertEqual([item.logical_order for item in widgets], list(range(len(layout))))

    def test_template_definition_resolution_uses_stable_source_and_renderer_keys(self):
        first = WidgetDefinition("first", "First", "Test", "kpi", "shared.source")
        second = WidgetDefinition("second", "Second", "Test", "compact-list", "shared.source")
        definitions = {first.key: first, second.key: second}
        self.assertIs(definition_for_template(definitions, TemplateWidget("shared.source", "compact-list", {"nested": {"a": 1}})), second)
        self.assertIs(definition_for_template(definitions, TemplateWidget("shared.source", "alert-list")), first)
        self.assertIsNone(definition_for_template(definitions, TemplateWidget("missing.source", "kpi")))


class DashboardBusinessSourceTests(TestCase):
    def setUp(self):
        from project.models import Institution, Project, Participant
        from fund.models import Fund, Fund_Institution
        from expense.models import Contract
        from endpoints.models import Milestones
        from staff.models import Employee, Employee_Superior
        from leave.models import Leave, Leave_Type
        self.today = timezone.localdate()
        self.user = get_user_model().objects.create_user(username="dashboard-business", password="test")
        self.employee = Employee.objects.create(first_name="Alice", last_name="Able", user=self.user, is_active=True,
                                                entry_date=self.today + timedelta(days=4))
        self.subordinate = Employee.objects.create(first_name="Bob", last_name="Below", is_active=True,
                                                   exit_date=self.today + timedelta(days=20))
        self.hidden_employee = Employee.objects.create(first_name="Hidden", last_name="Person")
        Employee_Superior.objects.create(superior=self.employee, employee=self.subordinate)
        self.project = Project.objects.create(name="Visible work", status=True, end_date=self.today - timedelta(days=1))
        self.other_project = Project.objects.create(name="Other visible", status=True, end_date=self.today + timedelta(days=40))
        self.inactive_project = Project.objects.create(name="Inactive visible", status=False)
        self.hidden_project = Project.objects.create(name="Hidden work", status=True)
        Participant.objects.create(project=self.project, employee=self.employee, status="l")
        institution = Institution.objects.create(short_name="LAB", name="Laboratory")
        funder = Fund_Institution.objects.create(short_name="FND", name="Funder")
        self.fund = Fund.objects.create(project=self.project, funder=funder, institution=institution,
                                        ref="VISIBLE-FUND", amount=Decimal("100"), expense=Decimal("-40"),
                                        start_date=self.today - timedelta(days=30), end_date=self.today + timedelta(days=20))
        self.hidden_fund = Fund.objects.create(project=self.hidden_project, funder=funder, institution=institution,
                                               ref="HIDDEN-FUND")
        self.contract = Contract.objects.create(employee=self.employee, fund=self.fund,
                                                start_date=self.today - timedelta(days=10), end_date=self.today + timedelta(days=10))
        self.hidden_contract = Contract.objects.create(employee=self.hidden_employee, fund=self.hidden_fund)
        self.milestone = Milestones.objects.create(project=self.project, name="Next milestone", end_date=self.today + timedelta(days=5))
        self.task = Milestones.objects.create(project=self.project, name="Overdue task",
                                             start_date=self.today - timedelta(days=10), end_date=self.today - timedelta(days=1))
        self.task.employee.add(self.employee)
        self.hidden_milestone = Milestones.objects.create(project=self.hidden_project, name="Hidden milestone")
        leave_type = Leave_Type.objects.create(short_name="AL", name="Annual leave")
        self.leave = Leave.objects.create(employee=self.employee, type=leave_type,
                                          start_date=self.today + timedelta(days=3), end_date=self.today + timedelta(days=5))
        Leave.objects.create(employee=self.hidden_employee, type=leave_type,
                             start_date=self.today + timedelta(days=3), end_date=self.today + timedelta(days=5))
        self.context = DashboardContext.personal(self.user)

    def test_projects_and_planning_use_only_visible_projects(self):
        from project.models import Project
        with patch.object(Project, "get_instances_for_user", return_value=Project.objects.exclude(pk=self.hidden_project.pk)):
            data = business_sources.projects(self.context, {"scope": "managed", "late_only": True, "limit": 1})["__renderers__"]
            self.assertEqual(data["kpi"]["value"], 1)
            self.assertEqual(data["alert-list"]["items"][0]["severity"], "danger")
            self.assertEqual(data["compact-list"]["items"][0]["label"], self.project.name)
            active = business_sources.projects(self.context, {"active_only": True})["__renderers__"]
            self.assertEqual(active["kpi"]["value"], 2)
            milestones = business_sources.milestones(self.context, {"due_within_days": "7", "limit": 5})["__renderers__"]
            self.assertEqual(milestones["kpi"]["value"], 1)
            self.assertEqual(milestones["compact-list"]["items"][0]["label"], self.milestone.name)
            tasks = business_sources.tasks(self.context, {"scope": "mine", "overdue_only": True})["__renderers__"]
            self.assertEqual(tasks["kpi"]["value"], 1)
            self.assertEqual(tasks["alert-list"]["items"][0]["severity"], "danger")

    def test_milestone_deadline_payload_is_filtered_and_prioritizes_open_issues(self):
        from endpoints.models import Milestones
        from project.models import Project
        overdue = Milestones.objects.create(project=self.project, name="Overdue ethics",
                                            end_date=self.today - timedelta(days=2))
        Milestones.objects.create(project=self.project, name="Completed report", status=True,
                                  end_date=self.today - timedelta(days=10))
        with patch.object(Project, "get_instances_for_user", return_value=Project.objects.filter(pk=self.project.pk)):
            data = business_sources.milestones(self.context, {"status": "all", "limit": 2})["__renderers__"]
            soon = business_sources.milestones(self.context, {"due_within_days": "7"})["__renderers__"]
            late = business_sources.milestones(self.context, {"overdue_only": True})["__renderers__"]
            tasks = business_sources.tasks(self.context, {})["__renderers__"]
        timeline = data["deadline-list"]
        self.assertEqual(timeline["summary"], {"count": 3, "overdue_count": 1, "due_soon_count": 1})
        self.assertEqual([item["key"] for item in timeline["items"]], [str(overdue.pk), str(self.milestone.pk)])
        self.assertEqual(timeline["items"][0]["state"], "overdue")
        self.assertEqual(timeline["items"][0]["days_until"], -2)
        self.assertEqual(timeline["items"][1]["project_name"], self.project.name)
        self.assertEqual(data["compact-list"]["items"][0]["label"], "Overdue ethics")
        self.assertEqual(data["alert-list"]["items"][0]["severity"], "danger")
        self.assertNotIn("deadline", data["compact-list"])
        self.assertNotIn("deadline", data["alert-list"])
        self.assertEqual(soon["deadline-list"]["summary"]["count"], 1)
        self.assertEqual(soon["deadline-list"]["summary"]["overdue_count"], 0)
        self.assertEqual(late["deadline-list"]["summary"]["count"], 1)
        self.assertNotIn("deadline-list", tasks)

    def test_task_workload_prioritizes_attention_and_counts_only_filtered_tasks(self):
        from endpoints.models import Milestones
        from project.models import Project
        from settings.models import LMUserSetting
        from staff.models import Employee
        LMUserSetting.objects.create(user=self.user, key="DASHBOARD_MILESTONES_STALE_TO_MONTH", value="1")
        near = Milestones.objects.create(project=self.project, name="Due tomorrow",
                                        start_date=self.today, end_date=self.today + timedelta(days=1))
        near.employee.add(self.subordinate)
        later = Milestones.objects.create(project=self.project, name="Later work",
                                         start_date=self.today, end_date=self.today + timedelta(days=45))
        later.employee.add(self.employee)
        done = Milestones.objects.create(project=self.project, name="Done work", status=True,
                                        start_date=self.today - timedelta(days=8), end_date=self.today - timedelta(days=5))
        done.employee.add(self.employee)
        with patch.object(Project, "get_instances_for_user", return_value=Project.objects.filter(pk=self.project.pk)), patch.object(
            Employee, "get_instances_for_user", return_value=Employee.objects.filter(pk=self.employee.pk)
        ):
            data = business_sources.tasks(self.context, {"status": "all", "limit": 4})["__renderers__"]
            workload = data["task-workload"]
            self.assertEqual(workload["summary"], {"count": 4, "overdue_count": 1, "due_soon_count": 1})
            self.assertEqual([row["key"] for row in workload["items"]], [
                str(self.task.pk), str(near.pk), str(later.pk), str(done.pk),
            ])
            self.assertEqual([row["state"] for row in workload["items"]], ["overdue", "due_soon", "later", "done"])
            self.assertEqual(workload["items"][0]["assignees"][0]["href"], f"/app/employees/{self.employee.pk}")
            self.assertIsNone(workload["items"][1]["assignees"][0]["href"])
            self.assertEqual(workload["items"][1]["project_name"], self.project.name)
            self.assertNotIn("task-workload", data["compact-list"])
            self.assertNotIn("task-workload", data["alert-list"])
            self.assertEqual(business_sources.tasks(self.context, {"status": "open"})["__renderers__"]["task-workload"]["summary"],
                             {"count": 3, "overdue_count": 1, "due_soon_count": 1})
            self.assertEqual(business_sources.tasks(self.context, {"overdue_only": True})["__renderers__"]["task-workload"]["summary"],
                             {"count": 1, "overdue_count": 1, "due_soon_count": 0})
            self.assertEqual(business_sources.tasks(self.context, {"due_within_days": "7"})["__renderers__"]["task-workload"]["summary"],
                             {"count": 1, "overdue_count": 0, "due_soon_count": 1})
            self.assertEqual(business_sources.tasks(self.context, {"scope": "mine"})["__renderers__"]["task-workload"]["summary"]["count"], 2)
            self.assertEqual(business_sources.tasks(self.context, {
                "project_scope": "specific_project", "project_id": self.project.pk,
            })["__renderers__"]["task-workload"]["summary"]["count"], 3)

    def test_fund_progress_uses_visible_funds_and_signed_expense(self):
        from fund.models import Fund
        from settings.models import LMUserSetting
        LMUserSetting.objects.create(user=self.user, key="DASHBOARD_FUND_STALE_TO_MONTH", value="1")
        with patch.object(Fund, "get_instances_for_user", return_value=Fund.objects.filter(pk=self.fund.pk)):
            data = business_sources.funds(self.context, {"ending_within_days": "30"})["__renderers__"]
        self.assertEqual(data["kpi"]["value"], 1)
        self.assertEqual(data["progress-list"]["items"][0]["percent"], 40.0)
        self.assertIn("60", data["progress-list"]["items"][0]["secondary"])
        self.assertEqual(data["overview-list"]["summary"]["amount"], 100.0)
        self.assertEqual(data["overview-list"]["summary"]["spent"], 40.0)
        self.assertEqual(data["overview-list"]["summary"]["percent"], 40.0)
        self.assertEqual(data["overview-list"]["summary"]["attention_count"], 1)
        self.assertEqual(data["overview-list"]["items"][0]["status"], "ending_soon")
        self.assertNotIn("overview", data["progress-list"])
        self.assertNotIn("HIDDEN-FUND", str(data))
        with patch.object(Fund, "get_instances_for_user", return_value=Fund.objects.filter(pk=self.fund.pk)):
            self.assertEqual(business_sources.funds(self.context, {"active_only": True})["__renderers__"]["kpi"]["value"], 1)

    def test_fund_overview_uses_the_same_filters_and_config_as_existing_renderers(self):
        from fund.models import Fund
        from dashboard.registry import CORE_RENDERERS, dashboard_registry
        sources, _ = dashboard_registry(self.context)
        source = sources["core.funds"]
        self.assertIn("overview-list", source.compatible_renderers)
        self.assertEqual(source.default_renderer, "overview-list")
        self.assertIn("overview-list", CORE_RENDERERS)
        self.assertEqual(set(source.config_fields), {"project_scope", "project_id", "scope", "active_only", "ending_within_days", "limit"})
        with patch.object(Fund, "get_instances_for_user", return_value=Fund.objects.filter(pk=self.fund.pk)):
            data = business_sources.funds(self.context, {"ending_within_days": "7", "limit": 1})["__renderers__"]
        self.assertEqual(data["overview-list"]["summary"]["count"], 0)
        self.assertEqual(data["overview-list"]["items"], [])
        self.assertIsNone(data["overview-list"]["summary"]["percent"])

    def test_contracts_reuse_hub_visibility_and_deadline_filters(self):
        from expense import contract_hub_api_v1
        from expense.models import Contract
        with patch.object(contract_hub_api_v1, "visible_contracts", return_value=Contract.objects.filter(pk=self.contract.pk)):
            data = business_sources.contracts(self.context, {"active_only": True, "current_only": True,
                                                              "ending_within_days": "30"})["__renderers__"]
        self.assertEqual(data["kpi"]["value"], 1)
        self.assertEqual(data["alert-list"]["items"][0]["severity"], "warning")
        self.assertNotIn(str(self.hidden_employee), str(data))
        with patch.object(contract_hub_api_v1, "visible_contracts", return_value=Contract.objects.filter(pk=self.contract.pk)):
            self.assertEqual(business_sources.contracts(self.context, {"stale_only": True})["__renderers__"]["kpi"]["value"], 1)

    def test_enhanced_sources_keep_distinct_generic_renderer_choices(self):
        from dashboard.registry import dashboard_registry
        sources, _ = dashboard_registry(self.context)
        for key, enhanced in (("core.funds", "overview-list"), ("core.milestones", "deadline-list"),
                              ("core.contracts", "contract-list"), ("core.employees", "employee-movements"),
                              ("core.tasks", "task-workload")):
            source = sources[key]
            self.assertEqual(source.default_renderer, enhanced)
            self.assertTrue({"compact-list", "alert-list", enhanced}.issubset(source.compatible_renderers))

    def test_project_portfolio_reuses_funding_and_explicit_attention_signals(self):
        from endpoints.models import Milestones
        from fund.models import Fund
        from project.models import Project
        from dashboard.financial_sources import advancement_for_funds
        self.project.start_date = self.today - timedelta(days=10)
        self.project.end_date = self.today + timedelta(days=10)
        self.project.save()
        self.other_project.end_date = self.today + timedelta(days=300)
        self.other_project.save()
        earlier = Milestones.objects.create(project=self.project, name="Earlier open milestone",
                                            end_date=self.today + timedelta(days=2))
        Milestones.objects.create(project=self.project, name="Late milestone",
                                  end_date=self.today - timedelta(days=3))
        with patch.object(Project, "get_instances_for_user", return_value=Project.objects.filter(
            pk__in=[self.project.pk, self.other_project.pk]
        )), patch.object(Fund, "get_instances_for_user", return_value=Fund.objects.filter(pk=self.fund.pk)):
            payload = business_sources.projects(self.context, {"limit": 5})["__renderers__"]
        data = payload["project-portfolio"]
        self.assertEqual(data["summary"], {"count": 2, "active_count": 2,
                                            "ending_soon_count": 1, "attention_count": 1})
        row = next(item for item in data["items"] if item["key"] == str(self.project.pk))
        self.assertEqual(row["temporal_percent"], 50.0)
        self.assertEqual(row["financial"]["percent"], advancement_for_funds([self.fund], today=self.today)["budget_percent"])
        self.assertEqual(row["financial_delta"], -10.0)
        self.assertEqual(row["financial_state"], {"key": "on_track", "tone": "success"})
        self.assertEqual(row["next_milestone"]["title"], earlier.name)
        self.assertEqual(row["next_milestone"]["relative_state"], "upcoming")
        self.assertEqual(row["overdue_task_count"], 1)
        self.assertEqual(row["overdue_milestone_count"], 1)
        self.assertEqual({signal["key"] for signal in row["attention_signals"]},
                         {"overdue_tasks", "overdue_milestones", "project_ending_soon"})
        self.assertEqual(next(signal["count"] for signal in row["attention_signals"]
                              if signal["key"] == "overdue_milestones"), 1)
        sources, definitions = dashboard_registry(self.context)
        self.assertEqual(sources["core.projects"].default_renderer, "project-portfolio")
        self.assertEqual(definitions["core.projects-count"].renderer_key, "project-portfolio")
        self.assertTrue({"kpi", "compact-list", "alert-list", "project-portfolio"}.issubset(sources["core.projects"].compatible_renderers))

    def test_project_portfolio_financial_gap_and_missing_percentages(self):
        from fund.models import Fund
        from project.models import Project
        self.project.start_date = self.today - timedelta(days=100)
        self.project.end_date = self.today + timedelta(days=100)
        self.project.save()
        self.task.status = True
        self.task.save()
        visible = Project.objects.filter(pk=self.project.pk)
        funds = Fund.objects.filter(pk=self.fund.pk)
        def payload():
            with patch.object(Project, "get_instances_for_user", return_value=visible), \
                 patch.object(Fund, "get_instances_for_user", return_value=funds):
                return business_sources.projects(self.context, {"limit": 1})["__renderers__"]["project-portfolio"]

        self.fund.expense = Decimal("-70")
        self.fund.save()
        ahead = payload()
        row = ahead["items"][0]
        self.assertEqual(row["financial_delta"], 20.0)
        self.assertEqual(row["financial_state"]["key"], "funding_ahead")
        self.assertEqual(ahead["summary"]["attention_count"], 1)
        self.assertIn({"key": "funding_ahead", "delta": 20.0, "tone": "warning"}, row["attention_signals"])

        self.fund.expense = Decimal("-20")
        self.fund.save()
        behind = payload()["items"][0]
        self.assertEqual(behind["financial_delta"], -30.0)
        self.assertEqual(behind["financial_state"]["key"], "funding_behind")

        self.project.start_date = None
        self.project.save()
        no_time = payload()["items"][0]
        self.assertIsNone(no_time["financial_delta"])
        self.assertIsNone(no_time["financial_state"])
        self.project.start_date = self.today - timedelta(days=100)
        self.project.save()
        funds = Fund.objects.none()
        no_funding = payload()["items"][0]
        self.assertIsNone(no_funding["financial_delta"])
        self.assertIsNone(no_funding["financial_state"])

    def test_project_health_bars_groups_visible_work_contracts_and_pace(self):
        from endpoints.models import Milestones
        from expense.models import Contract
        from fund.models import Fund
        from project.models import Project
        from settings.models import LMUserSetting

        self.project.start_date = self.today - timedelta(days=10)
        self.project.end_date = self.today + timedelta(days=10)
        self.project.save()
        LMUserSetting.objects.create(user=self.user, key="DASHBOARD_MILESTONES_STALE_TO_MONTH", value="1")
        LMUserSetting.objects.create(user=self.user, key="DASHBOARD_CONTRACT_STALE_TO_MONTH", value="1")
        Milestones.objects.create(project=self.project, name="Late milestone", end_date=self.today - timedelta(days=1))
        Milestones.objects.create(project=self.project, name="Future milestone", end_date=self.today + timedelta(days=90))
        Milestones.objects.create(project=self.project, name="Undated milestone")
        Milestones.objects.create(project=self.project, name="Due task", start_date=self.today - timedelta(days=1),
                                  end_date=self.today + timedelta(days=2))
        Milestones.objects.create(project=self.project, name="Later task", start_date=self.today,
                                  end_date=self.today + timedelta(days=90))
        expired_active = Contract.objects.create(employee=self.employee, fund=self.fund, is_active=True,
                                                  start_date=self.today - timedelta(days=30), end_date=self.today - timedelta(days=1))
        expired_inactive = Contract.objects.create(employee=self.employee, fund=self.fund, is_active=False,
                                                    start_date=self.today - timedelta(days=30), end_date=self.today - timedelta(days=1))
        later = Contract.objects.create(employee=self.employee, fund=self.fund, is_active=True,
                                        start_date=self.today - timedelta(days=1), end_date=self.today + timedelta(days=90))
        Fund.objects.create(project=self.project, funder=self.fund.funder, institution=self.fund.institution,
                            ref="INVISIBLE-SAME-PROJECT", amount=Decimal("1000"), expense=Decimal("-1000"),
                            start_date=self.today - timedelta(days=30), end_date=self.today + timedelta(days=20))
        visible_projects = Project.objects.filter(pk=self.project.pk)
        visible_funds = Fund.objects.filter(pk=self.fund.pk)
        visible_contracts = Contract.objects.filter(pk__in=[self.contract.pk, expired_active.pk,
                                                            expired_inactive.pk, later.pk])

        def health():
            with patch.object(Project, "get_instances_for_user", return_value=visible_projects), \
                 patch.object(Fund, "get_instances_for_user", return_value=visible_funds), \
                 patch("expense.contract_hub_api_v1.visible_contracts", return_value=visible_contracts):
                return business_sources.projects(self.context, {"limit": 1})["__renderers__"]["project-health-bars"]

        row = health()["items"][0]
        self.assertEqual(row["milestones"], {"total": 4, "upcoming_count": 1, "imminent_count": 1,
                                              "overdue_count": 1, "unscheduled_count": 1})
        self.assertEqual(row["tasks"], {"total": 3, "upcoming_count": 1, "imminent_count": 1,
                                         "overdue_count": 1, "unscheduled_count": 0})
        self.assertEqual(row["contracts"], {"total": 3, "active_count": 1,
                                             "ending_soon_count": 1, "expired_rh_active_count": 1})
        self.assertEqual(row["funding"]["percent"], 40.0)
        self.assertEqual(row["deadline"]["percent"], 50.0)
        self.assertEqual(row["deadline"]["relative"], {"state": "ends_in", "count": 10, "unit": "days"})
        self.assertEqual(row["funding_pace"], {"applicable": True, "ratio": 0.8,
                                                "state": "aligned", "tone": "success"})

        self.fund.expense = Decimal("-110")
        self.fund.save()
        overspent = health()["items"][0]
        self.assertEqual(overspent["funding"]["percent"], 110.0)
        self.assertEqual(overspent["funding"]["tone"], "danger")
        self.assertEqual(overspent["funding_pace"], {"applicable": True, "ratio": 2.2,
                                                      "state": "above", "tone": "danger"})

        self.project.start_date = self.today
        self.project.save()
        self.assertEqual(health()["items"][0]["funding_pace"]["state"], "not_applicable")
        visible_funds = Fund.objects.none()
        self.assertIsNone(health()["items"][0]["funding"])

    def test_project_health_bars_preserves_source_choices_and_contract_visibility(self):
        from expense.models import Contract
        from project.models import Project
        from dashboard.registry import dashboard_registry
        sources, _ = dashboard_registry(self.context)
        self.assertEqual(sources["core.projects"].default_renderer, "project-portfolio")
        self.assertIn("project-health-bars", sources["core.projects"].compatible_renderers)
        self.assertIn("project-portfolio", sources["core.projects"].compatible_renderers)
        with patch.object(Project, "get_instances_for_user", return_value=Project.objects.filter(pk=self.project.pk)), \
             patch("expense.contract_hub_api_v1.visible_contracts", return_value=Contract.objects.none()):
            data = business_sources.projects(self.context, {"limit": 1})["__renderers__"]["project-health-bars"]
        self.assertEqual(data["items"][0]["contracts"]["total"], 0)

    def test_employee_workload_single_allocation_and_open_items(self):
        from endpoints.models import Milestones
        from project.models import Participant, Project
        from staff.models import Employee
        from dashboard.employee_workload_sources import workload
        self.project.start_date = self.today - timedelta(days=20)
        self.project.end_date = self.today + timedelta(days=20)
        self.project.save()
        Participant.objects.filter(project=self.project, employee=self.employee).update(quotity=Decimal("0.800"))
        Participant.objects.create(project=self.other_project, employee=self.employee, quotity=Decimal("0.500"))
        Participant.objects.create(project=self.inactive_project, employee=self.employee, quotity=Decimal("0.900"))
        self.milestone.employee.add(self.employee)
        done = Milestones.objects.create(project=self.project, name="Done task", status=True,
                                         start_date=self.today - timedelta(days=1))
        done.employee.add(self.employee)
        self.contract.quotity = Decimal("0.900")
        self.contract.save()
        with patch.object(Employee, "get_instances_for_user", return_value=Employee.objects.filter(pk=self.employee.pk)), \
             patch.object(Project, "get_instances_for_user", return_value=Project.objects.filter(
                 pk__in=[self.project.pk, self.other_project.pk, self.inactive_project.pk]
             )):
            data = workload(self.context, {"scope": "single", "employee_id": self.employee.pk, "metric": "open_tasks"})
        self.assertEqual(data["mode"], "single")
        metrics = {item["key"]: item for item in data["metrics"]}
        self.assertEqual([metrics[key]["value"] for key in (
            "project_allocation", "open_tasks", "open_milestones", "open_work_items"
        )], [130.0, 1, 1, 2])
        self.assertEqual(metrics["project_allocation"]["reference_value"], 100)
        self.assertIsNone(metrics["open_tasks"]["reference_value"])

    def test_employee_workload_team_and_subordinates_respect_visibility(self):
        from endpoints.models import Milestones
        from project.models import Project
        from staff.models import Employee, Team, TeamMate
        from dashboard.employee_workload_sources import workload
        team = Team.objects.create(name="Work team", leader=self.employee)
        TeamMate.objects.create(team=team, employee=self.subordinate)
        for name in ("Bob task A", "Bob task B"):
            item = Milestones.objects.create(project=self.project, name=name,
                                             start_date=self.today - timedelta(days=2))
            item.employee.add(self.subordinate)
        with patch.object(Employee, "get_instances_for_user", return_value=Employee.objects.filter(
            pk__in=[self.employee.pk, self.subordinate.pk]
        )), patch.object(Project, "get_instances_for_user", return_value=Project.objects.filter(pk=self.project.pk)), \
             patch("staff.team_api_v1.visible_teams", return_value=Team.objects.filter(pk=team.pk)):
            comparison = workload(self.context, {"scope": "team", "team_id": team.pk, "metric": "open_tasks"})
            subordinate = workload(self.context, {"scope": "subordinates", "metric": "project_allocation"})
        self.assertEqual(comparison["mode"], "comparison")
        self.assertEqual([(item["employee_id"], item["value"]) for item in comparison["items"]],
                         [(self.subordinate.pk, 2), (self.employee.pk, 1)])
        self.assertEqual(comparison["unit"], "count")
        self.assertIsNone(comparison["reference_value"])
        self.assertEqual(subordinate["mode"], "single")
        self.assertEqual(subordinate["employee"]["id"], self.subordinate.pk)

    def test_employee_workload_config_rejects_invisible_targets(self):
        from staff.models import Employee, Team
        sources, definitions = dashboard_registry(self.context)
        source = sources["core.employee-workload"]
        definition = definitions["core.employee-workload"]
        team = Team.objects.create(name="Visible team", leader=self.employee)
        with patch.object(Employee, "get_instances_for_user", return_value=Employee.objects.filter(pk=self.employee.pk)), \
             patch("staff.team_api_v1.visible_teams", return_value=Team.objects.filter(pk=team.pk)):
            config = validated_config({"scope": "single", "employee_id": self.employee.pk},
                                      source, definition, "employee-workload", self.context)
            self.assertEqual(config["employee_id"], self.employee.pk)
            with self.assertRaises(ValidationError):
                validated_config({"scope": "single", "employee_id": self.hidden_employee.pk},
                                 source, definition, "employee-workload", self.context)
            team_config = validated_config({"scope": "team", "team_id": team.pk},
                                           source, definition, "employee-workload", self.context)
            self.assertEqual(team_config["team_id"], team.pk)
            with self.assertRaises(ValidationError):
                validated_config({"scope": "subordinates", "employee_id": self.employee.pk},
                                 source, definition, "employee-workload", self.context)

    def test_timeline_combines_visible_tasks_and_milestones_with_independent_filters(self):
        from dashboard.timeline_sources import timeline
        from dashboard.registry import CORE_RENDERERS, dashboard_registry
        from project.models import Project
        sources, _ = dashboard_registry(self.context)
        self.assertEqual(sources["core.timeline"].default_renderer, "timeline-calendar")
        self.assertEqual(set(sources["core.timeline"].compatible_renderers), {"timeline-calendar", "calendar-grid"})
        self.assertEqual(sources["core.tasks"].default_renderer, "task-workload")
        self.assertEqual(sources["core.milestones"].default_renderer, "deadline-list")
        self.assertIn("timeline-calendar", CORE_RENDERERS)
        self.assertIn("calendar-grid", CORE_RENDERERS)
        self.task.employee.add(self.hidden_employee)
        visible = Project.objects.exclude(pk=self.hidden_project.pk)
        with patch.object(Project, "get_instances_for_user", return_value=visible):
            data = timeline(self.context, {"tasks_scope": "mine", "milestones_scope": "all_visible"})
            self.assertEqual({item["id"] for item in data["events"]},
                             {f"tasks:{self.task.pk}", f"milestones:{self.milestone.pk}"})
            self.assertNotIn(str(self.hidden_employee), str(data))
            tasks = timeline(self.context, {"include_milestones": False, "tasks_scope": "mine"})
            self.assertEqual({item["source_type"] for item in tasks["events"]}, {"tasks"})
            milestones = timeline(self.context, {"include_tasks": False})
            self.assertEqual({item["source_type"] for item in milestones["events"]}, {"milestones"})
            self.assertEqual(timeline(self.context, {"include_tasks": False, "milestones_scope": "mine"})["events"], [])
            self.assertEqual(timeline(self.context, {"tasks_status": "done", "milestones_status": "done"})["events"], [])

    def test_timeline_horizon_and_earlier_overdue_count(self):
        from dashboard.timeline_sources import timeline
        from endpoints.models import Milestones
        from project.models import Project
        old = Milestones.objects.create(project=self.project, name="Old overdue",
                                        end_date=self.today - timedelta(days=3))
        visible_overdue = Milestones.objects.create(project=self.project, name="Visible overdue",
                                                    end_date=self.today - timedelta(days=2))
        far = Milestones.objects.create(project=self.project, name="Far milestone",
                                        end_date=self.today + timedelta(days=15))
        visible = Project.objects.exclude(pk=self.hidden_project.pk)
        with patch.object(Project, "get_instances_for_user", return_value=visible):
            data = timeline(self.context, {"include_tasks": False, "calendar_days": "14"})
            self.assertEqual(data["window_start"], (self.today - timedelta(days=2)).isoformat())
            self.assertEqual(data["window_end"], (self.today + timedelta(days=14)).isoformat())
            self.assertEqual(data["earlier_overdue_count"], 1)
            self.assertNotIn(f"milestones:{old.pk}", [item["id"] for item in data["events"]])
            self.assertIn(f"milestones:{visible_overdue.pk}", [item["id"] for item in data["events"]])
            self.assertNotIn(f"milestones:{far.pk}", [item["id"] for item in data["events"]])
            longer = timeline(self.context, {"include_tasks": False, "calendar_days": "21"})
            self.assertIn(f"milestones:{far.pk}", [item["id"] for item in longer["events"]])

    def test_timeline_namespaced_project_scope_is_validated(self):
        from dashboard.registry import dashboard_registry
        sources, definitions = dashboard_registry(self.context)
        source = sources["core.timeline"]
        definition = definitions["core.timeline"]
        with self.assertRaises(ValidationError):
            validated_config({"tasks_project_scope": "specific_project", "tasks_project_id": self.hidden_project.pk},
                             source, definition, "timeline-calendar", self.context)
        config = validated_config({"tasks_project_scope": "specific_project", "tasks_project_id": self.project.pk},
                                  source, definition, "timeline-calendar", self.context)
        self.assertEqual(config["tasks_project_id"], self.project.pk)

    def test_contract_overview_uses_personal_stale_setting_and_keeps_generic_lists(self):
        from expense import contract_hub_api_v1
        from expense.models import Contract
        from settings.models import LMUserSetting
        later = Contract.objects.create(employee=self.employee, fund=self.fund,
                                        start_date=self.today, end_date=self.today + timedelta(days=45))
        setting = LMUserSetting.objects.create(user=self.user, key="DASHBOARD_CONTRACT_STALE_TO_MONTH", value="0")
        with patch.object(contract_hub_api_v1, "visible_contracts", return_value=Contract.objects.filter(pk__in=[self.contract.pk, later.pk])):
            data = business_sources.contracts(self.context, {"limit": 2})["__renderers__"]
            self.assertEqual(data["contract-list"]["summary"], {"count": 2, "ending_soon_count": 1, "stale_count": 0})
            self.assertEqual(data["contract-list"]["items"][0]["state"], "ending_soon")
            self.assertEqual(data["contract-list"]["items"][0]["project_name"], self.project.name)
            self.assertEqual(data["contract-list"]["items"][0]["employee_name"], str(self.employee))
            self.assertEqual(data["compact-list"]["items"][0]["label"], str(self.employee))
            self.assertEqual(data["alert-list"]["items"][0]["severity"], "warning")
            self.assertNotIn("contracts", data["compact-list"])
            self.assertNotIn("contracts", data["alert-list"])
            self.assertEqual(business_sources.contracts(self.context, {"stale_only": True})["__renderers__"]["kpi"]["value"], 0)
            setting.value = "2"
            setting.save()
            stale = business_sources.contracts(self.context, {"stale_only": True})["__renderers__"]["contract-list"]
            self.assertEqual(stale["summary"]["stale_count"], 2)
            self.assertEqual(stale["items"][1]["state"], "stale")

    def test_employee_and_leave_sources_intersect_employee_visibility(self):
        from staff.models import Employee
        with patch.object(Employee, "get_instances_for_user", return_value=Employee.objects.exclude(pk=self.hidden_employee.pk)):
            team = business_sources.employees(self.context, {"scope": "subordinates", "active_only": True})["__renderers__"]
            self.assertEqual(team["kpi"]["value"], 1)
            self.assertEqual(team["compact-list"]["items"][0]["label"], str(self.subordinate))
            arrivals = business_sources.employees(self.context, {"movement": "arrivals", "within_days": "7"})["__renderers__"]
            self.assertEqual(arrivals["kpi"]["value"], 1)
            departures = business_sources.employees(self.context, {"movement": "departures", "within_days": "30"})["__renderers__"]
            self.assertEqual(departures["kpi"]["value"], 1)
            leave = business_sources.leaves(self.context, {"scope": "mine", "upcoming_days": "7"})["__renderers__"]
            self.assertEqual(leave["kpi"]["value"], 1)
            self.assertEqual(leave["compact-list"]["items"][0]["label"], "Annual leave")
            self.assertNotIn(str(self.hidden_employee), str(leave))

    def test_employee_movements_summary_and_rows_follow_the_filtered_scope(self):
        from staff.models import Employee, Employee_Status, Employee_Type, Team
        role = Employee_Type.objects.create(name="Engineer", shortname="ENG")
        Employee_Status.objects.create(employee=self.employee, type=role)
        team = Team.objects.create(name="Team A", leader=self.employee)
        visible = Employee.objects.exclude(pk=self.hidden_employee.pk)
        with patch.object(Employee, "get_instances_for_user", return_value=visible), patch.object(
            Team, "get_instances_for_user", return_value=Team.objects.filter(pk=team.pk)
        ):
            data = business_sources.employees(self.context, {"within_days": "30", "limit": 2})["__renderers__"]
            self.assertEqual(data["employee-movements"]["summary"], {"count": 2, "arrivals_count": 1, "departures_count": 1})
            self.assertEqual([row["state"] for row in data["employee-movements"]["items"]], ["leaving", "arriving"])
            arrival = data["employee-movements"]["items"][1]
            self.assertEqual(arrival["role"], "Engineer")
            self.assertEqual(arrival["team_name"], "Team A")
            self.assertEqual(arrival["team_href"], f"/app/teams/{team.pk}")
            self.assertEqual(arrival["days_until"], 4)
            self.assertEqual(data["compact-list"]["items"][0]["label"], str(self.employee))
            self.assertNotIn("employee-movements", data["compact-list"])
            self.assertNotIn("employee-movements", data["alert-list"])
            arrival_only = business_sources.employees(self.context, {"movement": "arrivals", "within_days": "30"})["__renderers__"]["employee-movements"]
            self.assertEqual(arrival_only["summary"], {"count": 1, "arrivals_count": 1, "departures_count": 0})
            departure_only = business_sources.employees(self.context, {"movement": "departures", "within_days": "30"})["__renderers__"]["employee-movements"]
            self.assertEqual(departure_only["summary"], {"count": 1, "arrivals_count": 0, "departures_count": 1})
            short_window = business_sources.employees(self.context, {"within_days": "7"})["__renderers__"]["employee-movements"]
            self.assertEqual(short_window["summary"], {"count": 2, "arrivals_count": 1, "departures_count": 0})
            self_only = business_sources.employees(self.context, {"scope": "self"})["__renderers__"]["employee-movements"]
            self.assertEqual(self_only["summary"]["count"], 1)
            project_only = business_sources.employees(self.context, {
                "project_scope": "specific_project", "project_id": self.project.pk,
            })["__renderers__"]["employee-movements"]
            self.assertEqual(project_only["summary"], {"count": 1, "arrivals_count": 1, "departures_count": 0})
            Employee.objects.filter(pk=self.subordinate.pk).update(is_active=False)
            active_only = business_sources.employees(self.context, {"active_only": True})["__renderers__"]["employee-movements"]
            self.assertEqual(active_only["summary"], {"count": 1, "arrivals_count": 1, "departures_count": 0})
            self.assertEqual(business_sources.leaves(self.context, {"scope": "mine", "current_only": True})["__renderers__"]["kpi"]["value"], 0)
