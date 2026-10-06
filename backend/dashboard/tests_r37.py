"""FrenchHollidayPlugin as a concrete Dashboard source, from registry to API."""

import json
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import translation
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from plugin.samples.FrenchHollidayPlugin.FrenchHollidayPlugin import FrenchHollidayPlugin
from project.models import Project

from .api_v1 import validated_config
from .models import WidgetInstance
from .registry import DashboardContext, available_definitions


SOURCE = "frenchholliday.upcoming-holidays"
TODAY = date(2026, 10, 4)


class FrenchHolidaySourceTests(SimpleTestCase):
    def setUp(self):
        self.plugin = FrenchHollidayPlugin()
        self.context = DashboardContext.personal(object())

    def test_source_contract_contexts_and_config_validation(self):
        source = self.plugin.get_dashboard_sources(self.context)[0]
        self.assertTrue(self.plugin.mixin_enabled("dashboard"))
        self.assertEqual(source.key, SOURCE)
        self.assertEqual(source.supported_scopes, ("user", "project"))
        self.assertEqual(source.compatible_renderers, ("kpi", "compact-list"))
        self.assertEqual(source.default_renderer, "kpi")
        with translation.override("fr"):
            self.assertEqual(str(source.label), "Jours fériés et vacances à venir")
            self.assertEqual(str(source.config_fields["horizon_days"]["label"]), "Horizon (jours)")
        with patch("plugin.registry.registry.with_mixin", return_value=[self.plugin]) as active:
            for context in (self.context, DashboardContext("project", self.context.user, object())):
                sources, definitions = available_definitions(context)
                self.assertIn(SOURCE, sources)
                self.assertIn(SOURCE, definitions)
                self.assertEqual(validated_config({}, sources[SOURCE], definitions[SOURCE], "kpi"),
                                 {"horizon_days": 180, "limit": 5})
            active.assert_called_with("dashboard", active=True)
        with patch("plugin.registry.registry.with_mixin", return_value=[]):
            self.assertNotIn(SOURCE, available_definitions(self.context)[1])
        for invalid in ({"horizon_days": 0}, {"horizon_days": 366}, {"limit": 0},
                        {"limit": 13}, {"limit": True}, {"unknown": 1}):
            with self.assertRaises(ValidationError):
                validated_config(invalid, source, self.plugin_definition(), "kpi")

    def plugin_definition(self):
        with patch("plugin.registry.registry.with_mixin", return_value=[self.plugin]):
            return available_definitions(self.context)[1][SOURCE]

    def test_local_files_zone_order_horizon_and_empty_payload_without_writes(self):
        with TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "vac.json").write_text(json.dumps([
                {"zones": "Zone B", "start_date": "2026-10-15T00:00:00+00:00",
                 "end_date": "2026-10-25T00:00:00+00:00", "description": "Vacances de la Toussaint"},
                {"zones": "Zone A", "start_date": "2026-10-06T00:00:00+00:00",
                 "end_date": "2026-10-08T00:00:00+00:00", "description": "Zone A only"},
            ]), encoding="utf-8")
            (folder / "dayoff.json").write_text(json.dumps({
                "2026-10-03": "Past", "2026-10-11": "Day off two", "2026-10-07": "Day off one",
                "2026-12-31": "Beyond horizon",
            }), encoding="utf-8")
            with (patch.object(FrenchHollidayPlugin, "get_static_folder", return_value=folder),
                  patch.object(FrenchHollidayPlugin, "get_setting", side_effect=lambda *args, key: {
                      "FHP_VACATION_ZONE": "Zone B", "FHP_COLOR": "#abcdef", "FHP_TITLE": False,
                  }[key]),
                  patch("plugin.samples.FrenchHollidayPlugin.FrenchHollidayPlugin.timezone.localdate", return_value=TODAY),
                  patch.object(FrenchHollidayPlugin, "FHP_pull") as pull):
                source = self.plugin.get_dashboard_sources(self.context)[0]
                user_payload = source.provider(self.context, {"horizon_days": 20, "limit": 2})["__renderers__"]
                project_payload = source.provider(DashboardContext("project", object(), object()),
                                                  {"horizon_days": 20, "limit": 5})["__renderers__"]
                self.assertEqual([item["label"] for item in user_payload["compact-list"]["items"][:2]],
                                 ["Day off one", "Day off two"])
                self.assertEqual(user_payload["kpi"]["label"], "Day off one")
                self.assertEqual([item["date"] for item in project_payload["compact-list"]["items"]],
                                 ["2026-10-07", "2026-10-11", "2026-10-15"])
                self.assertNotIn("Zone A only", str(project_payload))
                self.assertNotIn("Beyond horizon", str(project_payload))
                self.assertEqual(source.provider(self.context, {"horizon_days": 1})["__renderers__"]["compact-list"],
                                 {"items": []})
                self.assertEqual(source.provider(self.context, {"horizon_days": 1})["__renderers__"]["kpi"]["value"], "—")
                pull.assert_not_called()


class FrenchHolidayDashboardApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="holiday-dashboard", password="test", email="test@example.org")
        self.project = Project.objects.create(name="Holiday dashboard project", status=True)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.plugin = FrenchHollidayPlugin()

    def test_personal_and_project_catalog_widgets_and_missing_plugin(self):
        from common.calendar import LabsManagerCalendarEvent
        event = LabsManagerCalendarEvent(
            id="frenchholliday:dayoff:2026-10-11", title="", start=TODAY + timedelta(days=7),
            end=TODAY + timedelta(days=8), source="frenchholliday", kind="public_holiday",
            description="Holiday name",
        )
        with (patch("plugin.registry.registry.with_mixin", return_value=[self.plugin]),
              patch.object(FrenchHollidayPlugin, "get_vacation_events", return_value=[event]),
              patch("plugin.samples.FrenchHollidayPlugin.FrenchHollidayPlugin.timezone.localdate", return_value=TODAY)):
            personal = self.client.post("/api/v1/dashboards/", {"name": "Holidays", "template": "blank"}, format="json")
            self.assertEqual(personal.status_code, 201, personal.data)
            project = self.client.get(f"/api/v1/projects/{self.project.pk}/dashboard/")
            self.assertEqual(project.status_code, 200, project.data)
            for dashboard_id, catalog_url in (
                (personal.data["id"], "/api/v1/dashboards/catalog/"),
                (project.data["id"], f"/api/v1/projects/{self.project.pk}/dashboard/catalog/"),
            ):
                catalog = self.client.get(catalog_url)
                self.assertEqual(catalog.status_code, 200, catalog.data)
                source = next(item for item in catalog.data["sources"] if item["key"] == SOURCE)
                self.assertEqual(source["compatible_renderers"], ("kpi", "compact-list"))
                endpoint = f"/api/v1/dashboards/{dashboard_id}/widgets/"
                kpi = self.client.post(endpoint, {"source_key": SOURCE, "renderer_key": "kpi"}, format="json")
                listing = self.client.post(endpoint, {"source_key": SOURCE, "renderer_key": "compact-list",
                                                      "config": {"horizon_days": 30, "limit": 3}}, format="json")
                self.assertEqual(kpi.status_code, 201, kpi.data)
                self.assertEqual(listing.status_code, 201, listing.data)
                self.assertEqual(kpi.data["data"]["label"], "Holiday name")
                self.assertEqual(listing.data["data"]["items"][0]["label"], "Holiday name")
                self.assertEqual(listing.data["data"]["items"][0]["date"], "2026-10-11")
                self.assertEqual(self.client.post(endpoint, {"source_key": SOURCE, "config": {"horizon_days": 0}}, format="json").status_code, 400)
                self.assertEqual(self.client.post(endpoint, {"source_key": SOURCE, "config": {"limit": 13}}, format="json").status_code, 400)
            project_widget = WidgetInstance.objects.filter(dashboard_id=project.data["id"], source_key=SOURCE).first()
            self.assertIsNotNone(project_widget)

        with patch("plugin.registry.registry.with_mixin", return_value=[]):
            self.assertNotIn(SOURCE, {item["key"] for item in self.client.get("/api/v1/dashboards/catalog/").data["sources"]})
            detail = self.client.get(f"/api/v1/dashboards/{personal.data['id']}/")
            self.assertEqual(detail.status_code, 200)
            missing = [item for item in detail.data["widgets"] if item["source_key"] == SOURCE]
            self.assertEqual(len(missing), 2)
            self.assertTrue(all(not item["available"] and item["data"] is None for item in missing))
            self.assertEqual(self.client.delete(f"/api/v1/dashboards/{personal.data['id']}/widgets/{missing[0]['id']}/").status_code, 204)
