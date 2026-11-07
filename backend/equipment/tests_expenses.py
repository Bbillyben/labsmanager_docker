"""Focused Equipment expense link, permission, and financial regression tests."""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from rest_framework.test import APITestCase

from expense.models import Contract, Contract_expense, Expense
from fund.models import Fund
from labsmanager.tests import test_api_v1_funding
from settings.models import LMProjectSetting

from .models import Equipment, EquipmentCategory, EquipmentExpenseLink


class EquipmentExpenseTests(APITestCase):
    def setUp(self):
        test_api_v1_funding.ProjectFundingV1Tests.setUp(self)
        self.category = EquipmentCategory.objects.create(name="Scope")
        self.equipment = Equipment.objects.create(name="Scope A", internal_reference="EQ-A", category=self.category)
        self.other_equipment = Equipment.objects.create(name="Scope B", internal_reference="EQ-B", category=self.category)
        self.second_fund = Fund.objects.create(project=self.project, funder=self.funder,
                                               institution=self.institution, start_date=date(2026, 1, 1),
                                               end_date=date(2026, 12, 31), ref="A-2")
        LMProjectSetting.set_setting("EXPENSE_CALCULATION", "e", change_user=None, project=self.project)
        self.url = f"/api/v1/equipment/{self.equipment.pk}/expenses/"
        self.grant("equipment", "view_equipment", "view_equipmentexpenselink", "add_equipmentexpenselink",
                   "change_equipmentexpenselink", "delete_equipmentexpenselink")
        self.grant("expense", "add_expense", "change_expense", "delete_expense")

    def grant(self, app, *codes):
        self.user.user_permissions.add(*Permission.objects.filter(content_type__app_label=app, codename__in=codes))
        self.user = type(self.user).objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def revoke(self, app, code):
        self.user.user_permissions.remove(Permission.objects.get(content_type__app_label=app, codename=code))
        self.user = type(self.user).objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def payload(self, fund=None, **extra):
        return {"fund_id": (fund or self.fund).pk, "expense_id": "EQ-EXP", "desc": "Equipment purchase",
                "date": "2026-03-01", "type_id": self.other_type.pk, "amount": "42.00",
                "nature": "purchase", **extra}

    def expense(self, fund=None):
        return Expense.objects.create(fund_item=fund or self.fund, type=self.other_type,
                                      date=date(2026, 3, 1), amount=Decimal("42.00"))

    def test_model_cardinality_and_cascades(self):
        first, second = self.expense(), self.expense(self.second_fund)
        EquipmentExpenseLink.objects.create(equipment=self.equipment, expense=first, nature="purchase")
        EquipmentExpenseLink.objects.create(equipment=self.equipment, expense=second, nature="repair")
        self.assertEqual(self.equipment.expense_links.count(), 2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            EquipmentExpenseLink.objects.create(equipment=self.other_equipment, expense=first)
        with self.assertRaises(ProtectedError):
            self.equipment.delete()
        EquipmentExpenseLink.objects.get(expense=first).delete()
        self.assertTrue(Expense.objects.filter(pk=first.pk).exists())
        second.delete()
        self.assertFalse(EquipmentExpenseLink.objects.filter(expense_id=second.pk).exists())

    def test_create_list_multi_fund_edit_nature_unlink_and_delete(self):
        first = self.client.post(self.url, self.payload(), format="json")
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post(self.url, self.payload(self.second_fund, expense_id="SECOND"), format="json")
        self.assertEqual(second.status_code, 201, second.data)
        listed = self.client.get(self.url)
        self.assertEqual(listed.status_code, 200, listed.data)
        self.assertEqual(listed.data["count"], 2)
        self.assertEqual({row["fund"]["id"] for row in listed.data["results"]}, {self.fund.pk, self.second_fund.pk})
        self.assertEqual(listed.data["total_visible"], "84.00")
        detail = f"{self.url}{first.data['id']}/"
        self.assertEqual(self.client.patch(detail, {"nature": "maintenance"}, format="json").data["nature"], "maintenance")
        self.assertEqual(self.client.patch(detail, {"desc": "Serviced"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(detail).status_code, 204)
        self.assertTrue(Expense.objects.filter(pk=first.data["id"], desc="Serviced").exists())
        self.assertEqual(self.client.delete(f"{self.url}{second.data['id']}/delete-expense/").status_code, 204)
        self.assertFalse(Expense.objects.filter(pk=second.data["id"]).exists())

    def test_association_conflict_and_atomic_creation(self):
        expense = self.expense()
        linked = self.client.post(self.url, {"existing_expense_id": expense.pk, "nature": "other"}, format="json")
        self.assertEqual(linked.status_code, 201, linked.data)
        self.assertEqual(self.client.post(self.url, {"existing_expense_id": expense.pk}, format="json").status_code, 409)
        count = Expense.objects.count()
        invalid = self.client.post(self.url, self.payload(type_id=999999), format="json")
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(Expense.objects.count(), count)
        self.assertEqual(self.client.post(self.url, self.payload(fund_id=999999), format="json").status_code, 404)

    def test_separate_link_and_financial_rights_and_existing_api_boundary(self):
        expense = self.expense()
        link = EquipmentExpenseLink.objects.create(equipment=self.equipment, expense=expense)
        self.revoke("equipment", "view_equipmentexpenselink")
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/funds/{self.fund.pk}/expenses/").data["count"], 0)
        self.assertEqual(self.client.patch(f"/api/v1/funds/{self.fund.pk}/expenses/{expense.pk}/", {"desc": "Hidden"}, format="json").status_code, 404)
        self.grant("equipment", "view_equipmentexpenselink")
        self.revoke("expense", "change_expense")
        self.grant("fund", "view_fund")
        self.participation.status = "a"
        self.participation.save(update_fields=["status"])
        self.assertEqual(self.client.patch(f"{self.url}{expense.pk}/", {"desc": "Forbidden"}, format="json").status_code, 403)
        self.assertEqual(self.client.patch(f"{self.url}{expense.pk}/", {"nature": "repair"}, format="json").status_code, 403)
        self.participation.status = "l"
        self.participation.save(update_fields=["status"])
        self.assertEqual(self.client.patch(f"{self.url}{expense.pk}/", {"nature": "repair"}, format="json").status_code, 200)
        self.revoke("equipment", "delete_equipmentexpenselink")
        self.assertEqual(self.client.delete(f"{self.url}{expense.pk}/").status_code, 403)
        self.assertEqual(self.client.delete(f"{self.url}{expense.pk}/delete-expense/").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/v1/funds/{self.fund.pk}/expenses/{expense.pk}/").status_code, 403)
        self.assertTrue(EquipmentExpenseLink.objects.filter(pk=link.pk).exists())

    def test_invisible_equipment_or_fund_is_not_exposed(self):
        expense = self.expense(self.hidden_fund)
        EquipmentExpenseLink.objects.create(equipment=self.equipment, expense=expense)
        self.assertEqual(self.client.get(self.url).data["count"], 0)
        self.assertEqual(self.client.post(self.url, {"existing_expense_id": expense.pk}, format="json").status_code, 404)
        self.revoke("equipment", "view_equipment")
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_contract_expense_can_coexist_and_contract_api_respects_link_rights(self):
        contract = Contract.objects.create(employee=self.employee, fund=self.fund, status="prov")
        expense = Contract_expense.objects.create(
            contract=contract, fund_item=self.fund, type=self.type,
            date=date(2026, 3, 1), amount=Decimal("20.00"),
        )
        EquipmentExpenseLink.objects.create(equipment=self.equipment, expense=expense)
        detail = f"/api/v1/projects/{self.project.pk}/contracts/{contract.pk}/"
        self.revoke("equipment", "view_equipmentexpenselink")
        hidden = self.client.get(detail)
        self.assertEqual(hidden.status_code, 200, hidden.data)
        self.assertEqual(hidden.data["expenses"], [])
        self.grant("equipment", "view_equipmentexpenselink")
        visible = self.client.get(detail)
        self.assertEqual([row["id"] for row in visible.data["expenses"]], [expense.pk])
        self.revoke("equipment", "delete_equipmentexpenselink")
        self.assertEqual(self.client.delete(detail).status_code, 403)
        self.assertTrue(Contract_expense.objects.filter(pk=expense.pk).exists())

    def test_expense_centered_assignment_workflow(self):
        expense = self.expense()
        url = f"/api/v1/expenses/{expense.pk}/business-assignments/"
        empty = self.client.get(url)
        self.assertEqual(empty.status_code, 200, empty.data)
        self.assertIsNone(empty.data["equipment"])
        self.assertTrue(empty.data["capabilities"]["can_link"])
        created = self.client.post(url, {"equipment_id": self.equipment.pk, "nature": "purchase"}, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["equipment"]["internal_reference"], "EQ-A")
        self.assertEqual(self.client.post(url, {"equipment_id": self.other_equipment.pk, "nature": "other"}, format="json").status_code, 409)
        changed = self.client.patch(url, {"equipment_id": self.other_equipment.pk, "nature": "repair"}, format="json")
        self.assertEqual(changed.status_code, 200, changed.data)
        self.assertEqual(changed.data["equipment"]["id"], self.other_equipment.pk)
        self.assertEqual(changed.data["nature"], "repair")
        self.assertEqual(EquipmentExpenseLink.objects.filter(expense=expense).count(), 1)
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(EquipmentExpenseLink.objects.filter(expense=expense).exists())
        self.assertEqual(Expense.objects.get(pk=expense.pk).amount, Decimal("42.00"))

    def test_expense_centered_permissions_and_validation(self):
        expense = self.expense()
        url = f"/api/v1/expenses/{expense.pk}/business-assignments/"
        self.assertEqual(self.client.post(url, {"equipment_id": self.equipment.pk, "nature": "invalid"}, format="json").status_code, 400)
        self.assertFalse(EquipmentExpenseLink.objects.filter(expense=expense).exists())
        self.revoke("equipment", "add_equipmentexpenselink")
        self.assertEqual(self.client.post(url, {"equipment_id": self.equipment.pk, "nature": "purchase"}, format="json").status_code, 403)
        self.grant("equipment", "add_equipmentexpenselink")
        self.assertEqual(self.client.post(url, {"equipment_id": 999999, "nature": "purchase"}, format="json").status_code, 404)
        self.assertEqual(self.client.post(url, {"equipment_id": self.equipment.pk, "nature": "purchase"}, format="json").status_code, 201)
        self.revoke("equipment", "view_equipmentexpenselink")
        self.assertEqual(self.client.get(url).status_code, 404)
        self.grant("equipment", "view_equipmentexpenselink")
        self.revoke("equipment", "change_equipmentexpenselink")
        self.assertEqual(self.client.patch(url, {"nature": "repair"}, format="json").status_code, 403)
        self.revoke("equipment", "delete_equipmentexpenselink")
        self.assertEqual(self.client.delete(url).status_code, 403)
