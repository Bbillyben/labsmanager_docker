"""Equipment Dashboard KPI scope, visibility, and registration checks."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from equipment.models import Equipment, EquipmentCategory, EquipmentMaintenance, EquipmentResponsibility
from staff.models import Employee

from .equipment_sources import my_equipment, overdue_maintenance, upcoming_maintenance
from .registry import DashboardContext, available_definitions


class EquipmentDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="equipment-dashboard")
        self.employee = Employee.objects.create(first_name="Ada", last_name="Lovelace", user=self.user)
        category = EquipmentCategory.objects.create(name="Dashboard equipment")
        self.own = Equipment.objects.create(name="Own", internal_reference="DASH-E1", category=category)
        self.other = Equipment.objects.create(name="Other", internal_reference="DASH-E2", category=category)
        self.future = Equipment.objects.create(name="Future", internal_reference="DASH-E3", category=category)
        self.past = Equipment.objects.create(name="Past", internal_reference="DASH-E4", category=category)
        today = timezone.localdate()
        for _ in range(2):
            EquipmentResponsibility.objects.create(equipment=self.own, employee=self.employee, start_date=today)
        EquipmentResponsibility.objects.create(equipment=self.future, employee=self.employee, start_date=today + timedelta(days=1))
        EquipmentResponsibility.objects.create(equipment=self.past, employee=self.employee, end_date=today - timedelta(days=1))
        self.context = DashboardContext.personal(self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def grant(self, *codenames):
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="equipment", codename__in=codenames))
        for cache in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache, None)

    def maintenance(self, equipment, scheduled_date, status="planned"):
        return EquipmentMaintenance.objects.create(
            equipment=equipment, title="Inspection", maintenance_type="inspection",
            scheduled_date=scheduled_date, status=status,
            performed_date=scheduled_date if status == "completed" else None,
        )

    def test_current_responsibility_is_distinct_and_permission_filtered(self):
        self.assertEqual(my_equipment(self.context, {})["value"], 0)
        self.grant("view_equipment")
        self.assertEqual(my_equipment(self.context, {})["value"], 1)
        self.assertEqual(my_equipment(DashboardContext.personal(get_user_model().objects.create_user(username="no-employee")), {})["value"], 0)

    def test_maintenance_dates_status_scope_and_horizon(self):
        today = timezone.localdate()
        self.grant("view_equipment", "view_equipmentmaintenance")
        self.maintenance(self.own, today)
        self.maintenance(self.own, today + timedelta(days=30), "in_progress")
        self.maintenance(self.other, today + timedelta(days=31))
        self.maintenance(self.other, today + timedelta(days=10))
        self.maintenance(self.other, today - timedelta(days=1))
        self.maintenance(self.own, today - timedelta(days=2), "completed")
        self.maintenance(self.own, today + timedelta(days=3), "cancelled")
        self.assertEqual(upcoming_maintenance(self.context, {})["value"], 3)
        self.assertEqual(upcoming_maintenance(self.context, {"scope": "mine"})["value"], 2)
        self.assertEqual(upcoming_maintenance(self.context, {"scope": "mine", "within_days": 7})["value"], 1)
        self.assertEqual(overdue_maintenance(self.context, {})["value"], 1)
        self.assertEqual(overdue_maintenance(self.context, {"scope": "mine"})["value"], 0)

    def test_catalog_scopes_and_permissions(self):
        keys = {item["key"] for item in self.client.get("/api/v1/dashboards/catalog/").data["sources"]}
        self.assertNotIn("core.my-equipment", keys)
        self.grant("view_equipment")
        self.assertIn("core.my-equipment", {item["key"] for item in self.client.get("/api/v1/dashboards/catalog/").data["sources"]})
        self.assertNotIn("core.upcoming-maintenance", {item["key"] for item in self.client.get("/api/v1/dashboards/catalog/").data["sources"]})
        self.grant("view_equipmentmaintenance")
        catalog = self.client.get("/api/v1/dashboards/catalog/").data
        by_key = {item["key"]: item for item in catalog["sources"]}
        self.assertEqual(by_key["core.my-equipment"]["supported_scopes"], ("user",))
        self.assertEqual(by_key["core.upcoming-maintenance"]["config_fields"]["within_days"]["default"], 30)
        self.assertEqual(by_key["core.overdue-maintenance"]["config_fields"]["scope"]["choices"], ["all_visible", "mine"])
        self.assertTrue({"core.my-equipment", "core.upcoming-maintenance", "core.overdue-maintenance"} <=
                        {item["key"] for item in catalog["definitions"]})
        self.assertFalse({"core.my-equipment", "core.upcoming-maintenance", "core.overdue-maintenance"} &
                         available_definitions(DashboardContext("project", self.user))[1].keys())

    def test_standard_widget_creation_validation_and_refresh(self):
        self.grant("view_equipment", "view_equipmentmaintenance")
        dashboard = self.client.post("/api/v1/dashboards/", {"name": "Equipment", "template": "blank"}, format="json")
        self.assertEqual(dashboard.status_code, 201, dashboard.data)
        url = f"/api/v1/dashboards/{dashboard.data['id']}/widgets/"
        for key in ("core.my-equipment", "core.upcoming-maintenance", "core.overdue-maintenance"):
            created = self.client.post(url, {"source_key": key}, format="json")
            self.assertEqual(created.status_code, 201, created.data)
            self.assertEqual(created.data["renderer_key"], "kpi")
            self.assertFalse(created.data["error"])
        self.assertEqual(self.client.post(url, {"source_key": "core.upcoming-maintenance", "config": {"within_days": 366}}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"source_key": "core.overdue-maintenance", "config": {"scope": "project"}}, format="json").status_code, 400)
        self.maintenance(self.own, timezone.localdate() + timedelta(days=2))
        refreshed = self.client.get(f"/api/v1/dashboards/{dashboard.data['id']}/").data
        values = {item["source_key"]: item["data"]["value"] for item in refreshed["widgets"]}
        self.assertEqual(values, {"core.my-equipment": 1, "core.upcoming-maintenance": 1, "core.overdue-maintenance": 0})
        self.user.user_permissions.remove(Permission.objects.get(codename="view_equipmentmaintenance", content_type__app_label="equipment"))
        for cache in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(cache, None)
        hidden = self.client.get(f"/api/v1/dashboards/{dashboard.data['id']}/").data
        self.assertFalse([item for item in hidden["widgets"] if item["source_key"] == "core.upcoming-maintenance"][0]["available"])
