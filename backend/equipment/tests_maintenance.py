"""Maintenance API, financial boundary, and dedicated calendar regressions."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase

from expense.models import Expense
from labsmanager.tests import test_api_v1_funding

from .models import Equipment, EquipmentCategory, EquipmentExpenseLink, EquipmentMaintenance


class EquipmentMaintenanceTests(APITestCase):
    def setUp(self):
        test_api_v1_funding.ProjectFundingV1Tests.setUp(self)
        category = EquipmentCategory.objects.create(name="Microscopes")
        self.equipment = Equipment.objects.create(name="Scope", internal_reference="EQ-M1", category=category)
        self.other = Equipment.objects.create(name="Other", internal_reference="EQ-M2", category=category)
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="equipment", codename__in=(
                "view_equipment", "view_equipmentmaintenance", "add_equipmentmaintenance",
                "change_equipmentmaintenance", "delete_equipmentmaintenance",
                "view_equipmentexpenselink")))
        self.user = type(self.user).objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        self.url = f"/api/v1/equipment/{self.equipment.pk}/maintenances/"

    def payload(self, **updates):
        return {"title": "Annual inspection", "maintenance_type": "inspection", "status": "planned",
                "scheduled_date": "2026-05-12", "description": "Check optics", **updates}

    def test_create_validate_complete_cancel_delete_and_filters(self):
        self.assertEqual(self.client.post(self.url, self.payload(scheduled_date=None), format="json").status_code, 400)
        self.assertEqual(self.client.post(self.url, self.payload(scheduled_start_time="09:00"), format="json").status_code, 400)
        self.assertEqual(self.client.post(self.url, self.payload(scheduled_start_time="10:00", scheduled_end_time="09:00"), format="json").status_code, 400)
        self.assertEqual(self.client.post(self.url, self.payload(status="completed"), format="json").status_code, 400)
        created = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(created.status_code, 201, created.data)
        identifier = created.data["id"]
        detail = f"/api/v1/equipment/maintenances/{identifier}/"
        self.assertIsNone(created.data["scheduled_start_time"])
        self.assertEqual(self.client.patch(detail, {"title": "Updated"}, format="json").data["title"], "Updated")
        self.assertEqual(self.client.post(f"{detail}complete/", {"report": "Done"}, format="json").status_code, 400)
        completed = self.client.post(f"{detail}complete/", {"performed_date": "2026-05-13", "report": "Done"}, format="json")
        self.assertEqual(completed.status_code, 200, completed.data)
        self.assertEqual(completed.data["status"], "completed")
        self.assertEqual(completed.data["report"], "Done")
        self.assertEqual(self.client.get(self.url + "?status=planned").data["count"], 0)
        self.assertEqual(self.client.get(self.url + "?status=completed").data["count"], 1)
        self.assertEqual(self.client.get(self.url + "?maintenance_type=inspection").data["count"], 1)
        second = self.client.post(self.url, self.payload(title="Cancel me"), format="json")
        self.assertEqual(self.client.post(f"/api/v1/equipment/maintenances/{second.data['id']}/cancel/", {}, format="json").data["status"], "cancelled")
        self.assertEqual(self.client.delete(detail).status_code, 204)

    def test_financial_link_same_equipment_and_set_null(self):
        first = Expense.objects.create(fund_item=self.fund, type=self.other_type, date=date(2026, 5, 1), amount=Decimal("42.00"), expense_id="M-1")
        second = Expense.objects.create(fund_item=self.fund, type=self.other_type, date=date(2026, 5, 2), amount=Decimal("13.00"))
        link = EquipmentExpenseLink.objects.create(equipment=self.equipment, expense=first)
        wrong = EquipmentExpenseLink.objects.create(equipment=self.other, expense=second)
        self.assertEqual(self.client.post(self.url, self.payload(expense_link_id=wrong.pk), format="json").status_code, 400)
        created = self.client.post(self.url, self.payload(expense_link_id=link.pk), format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["expense_link"]["label"], "M-1")
        maintenance = EquipmentMaintenance.objects.get(pk=created.data["id"])
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="equipment", codename="change_equipmentexpenselink"))
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="expense", codename="change_expense"))
        self.user = type(self.user).objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        moved = self.client.patch(f"/api/v1/expenses/{first.pk}/business-assignments/",
                                  {"equipment_id": self.other.pk}, format="json")
        self.assertEqual(moved.status_code, 400, moved.data)
        link.equipment = self.other
        with self.assertRaises(ValidationError):
            link.save(update_fields=["equipment"])
        link.delete()
        maintenance.refresh_from_db()
        self.assertIsNone(maintenance.expense_link_id)
        self.assertTrue(Expense.objects.filter(pk=first.pk).exists())

    def test_permissions_and_no_financial_leak(self):
        expense = Expense.objects.create(fund_item=self.fund, type=self.other_type, date=date(2026, 5, 1), amount=Decimal("42.00"), expense_id="SECRET")
        link = EquipmentExpenseLink.objects.create(equipment=self.equipment, expense=expense)
        created = self.client.post(self.url, self.payload(expense_link_id=link.pk), format="json")
        identifier = created.data["id"]
        self.user.user_permissions.remove(Permission.objects.get(content_type__app_label="equipment", codename="view_equipmentexpenselink"))
        self.user = type(self.user).objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        hidden = self.client.get(f"/api/v1/equipment/maintenances/{identifier}/")
        self.assertIsNone(hidden.data["expense_link"])
        self.assertNotIn("42.00", str(hidden.data))
        self.assertEqual(self.client.get(f"{self.url}expense-options/").data, [])
        self.assertNotIn("SECRET", str(self.client.get(self.url + "calendar/?from=2026-05-01&to=2026-05-31").data))
        self.user.user_permissions.remove(Permission.objects.get(content_type__app_label="equipment", codename="change_equipmentmaintenance"))
        self.user = type(self.user).objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        self.assertEqual(self.client.patch(f"/api/v1/equipment/maintenances/{identifier}/", {"title": "Blocked"}, format="json").status_code, 403)
        self.user.user_permissions.remove(Permission.objects.get(content_type__app_label="equipment", codename="view_equipmentmaintenance"))
        self.user = type(self.user).objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/equipment/maintenances/{identifier}/").status_code, 403)

    def test_calendar_projection_is_bounded_and_isolated(self):
        all_day = self.client.post(self.url, self.payload(), format="json")
        timed = self.client.post(self.url, self.payload(title="Timed", scheduled_start_time="09:00", scheduled_end_time="10:00"), format="json")
        self.assertEqual(timed.status_code, 201, timed.data)
        query = "?from=2026-05-01&to=2026-05-31"
        general = self.client.get("/api/v1/equipment/maintenances/calendar/" + query)
        scoped = self.client.get(self.url + "calendar/" + query)
        self.assertEqual(general.status_code, 200, general.data)
        self.assertEqual(len(general.data["events"]), 2)
        self.assertEqual(general.data["events"], scoped.data["events"])
        events = {event["id"]: event for event in general.data["events"]}
        self.assertTrue(events[f"equipment-maintenance:{all_day.data['id']}"]["all_day"])
        self.assertFalse(events[f"equipment-maintenance:{timed.data['id']}"]["all_day"])
        self.assertEqual(self.client.get(self.url + "calendar/?from=2026-06-01&to=2026-06-30").data["events"], [])
        employees = self.client.get("/api/v1/calendars/employees/" + query)
        projects = self.client.get("/api/v1/calendars/projects/" + query)
        self.assertEqual(employees.status_code, 200)
        self.assertEqual(projects.status_code, 200)
        maintenance_ids = set(events)
        self.assertFalse(maintenance_ids.intersection(event["id"] for event in employees.data["events"]))
        self.assertFalse(maintenance_ids.intersection(event["id"] for event in projects.data["events"]))
        self.assertEqual(self.client.get("/api/v1/equipment/maintenances/calendar/" + query + f"&equipment={self.other.pk}").data["events"], [])
