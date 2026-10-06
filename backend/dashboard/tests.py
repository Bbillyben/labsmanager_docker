from unittest.mock import patch
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Dashboard, WidgetInstance
from .registry import (DashboardContext, CORE_WIDGETS, TEMPLATES, TemplateWidget,
                       available_definitions, dashboard_registry, definition_for_template,
                       DataSource, WidgetDefinition)
from .api_v1 import validated_config
from . import business_sources
from rest_framework.exceptions import ValidationError


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
        expected = {"employee": 5, "leader": 7, "lab-manager": 7, "blank": 0}
        ids = [self.create(name, name) for name in expected]
        self.assertEqual(Dashboard.objects.filter(owner=self.user).count(), 4)
        self.assertEqual(Dashboard.objects.filter(owner=self.user, is_default=True).count(), 1)
        for (name, count), pk in zip(expected.items(), ids):
            self.assertEqual(Dashboard.objects.get(pk=pk).widgets.count(), count)
        leader_detail = self.client.get(f"/api/v1/dashboards/{ids[1]}/")
        self.assertEqual(leader_detail.status_code, 200)
        self.assertEqual(next(item for item in leader_detail.data["widgets"] if item["definition_key"] == "core.projects-count")["data"]["value"], 0)
        self.assertEqual(next(item for item in leader_detail.data["widgets"] if item["definition_key"] == "core.projects-count")["source_key"], "core.projects")
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

    def test_new_templates_are_copied_without_changing_existing_dashboards(self):
        old = self.create("Existing", "blank")
        WidgetInstance.objects.create(dashboard_id=old, definition_key="core.note", source_key="core.note", renderer_key="empty")
        for template, expected in (("employee", 5), ("leader", 7), ("lab-manager", 7), ("blank", 0)):
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
            self.assertEqual(len(widgets), len(TEMPLATES[template]))
            for index, (widget, item) in enumerate(zip(widgets, TEMPLATES[template])):
                self.assertEqual((widget.source_key, widget.renderer_key, widget.title),
                                 (item.source_key, item.renderer_key, item.title))
                self.assertEqual(widget.logical_order, index)
                self.assertEqual((widget.x, widget.y), ((index % 3) * 4, (index // 3) * 3))
                for key, value in item.config.items():
                    self.assertEqual(widget.config[key], value)

        before = Dashboard.objects.filter(owner=self.user).count()
        with patch("dashboard.api_v1.validated_config", side_effect=ValidationError({"config": "Invalid template"})):
            response = self.client.post("/api/v1/dashboards/", {"name": "Broken", "template": "employee"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Dashboard.objects.filter(owner=self.user).count(), before)

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

    def test_fund_progress_uses_visible_funds_and_signed_expense(self):
        from fund.models import Fund
        with patch.object(Fund, "get_instances_for_user", return_value=Fund.objects.filter(pk=self.fund.pk)):
            data = business_sources.funds(self.context, {"ending_within_days": "30"})["__renderers__"]
        self.assertEqual(data["kpi"]["value"], 1)
        self.assertEqual(data["progress-list"]["items"][0]["percent"], 40.0)
        self.assertIn("60", data["progress-list"]["items"][0]["secondary"])
        self.assertNotIn("HIDDEN-FUND", str(data))
        with patch.object(Fund, "get_instances_for_user", return_value=Fund.objects.filter(pk=self.fund.pk)):
            self.assertEqual(business_sources.funds(self.context, {"active_only": True})["__renderers__"]["kpi"]["value"], 1)

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
            self.assertEqual(business_sources.leaves(self.context, {"scope": "mine", "current_only": True})["__renderers__"]["kpi"]["value"], 0)
