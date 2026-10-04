"""Financial explorers reuse Project/Fund visibility for rows and exports."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.test import APITestCase

from expense.models import Contract, Contract_type, Expense
from fund.models import Budget, Fund_Item
from staff.models import Employee_Type

class FinancialToolsTests(APITestCase):
    def setUp(self):
        from .test_api_v1_funding import ProjectFundingV1Tests
        ProjectFundingV1Tests.setUp(self)
        self.type.is_hr = True
        self.type.save()
        self.hidden_item = Fund_Item.objects.create(fund=self.hidden_fund, type=self.type, amount=Decimal("900.00"))
        self.budget = Budget.objects.create(fund=self.fund, cost_type=self.type, amount=Decimal("100.00"), desc="Visible budget")
        self.hidden_budget = Budget.objects.create(fund=self.hidden_fund, cost_type=self.type, amount=Decimal("900.00"), desc="Secret budget")
        self.expense = Expense.objects.create(fund_item=self.fund, type=self.type, date=date(2026, 3, 1), amount=Decimal("-20.00"), expense_id="OPEN-1", desc="Visible salary")
        self.hidden_expense = Expense.objects.create(fund_item=self.hidden_fund, type=self.type, date=date(2026, 4, 1), amount=Decimal("-900.00"), expense_id="SECRET-1")
        self.contract_type = Contract_type.objects.create(name="Fixed")
        self.employee_type = Employee_Type.objects.create(name="Researcher", shortname="RES")
        self.contract = Contract.objects.create(employee=self.employee, fund=self.fund, contract_type=self.contract_type,
                                                start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        self.hidden_contract = Contract.objects.create(employee=self.employee, fund=self.hidden_fund, contract_type=self.contract_type,
                                                       start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))

    def ids(self, kind, **params):
        response = self.client.get(f"/api/v1/{kind}/", params)
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        return [item["id"] for item in response.data["results"]]

    def test_visibility_read_only_and_pagination(self):
        for kind, visible, hidden in (("fund-items", self.item, self.hidden_item), ("budgets", self.budget, self.hidden_budget),
                                      ("expenses", self.expense, self.hidden_expense)):
            self.assertEqual(self.ids(kind), [visible.pk])
            self.assertNotIn(hidden.pk, self.ids(kind, limit=1))
            self.assertEqual(self.client.post(f"/api/v1/{kind}/", {}, format="json").status_code, 405)
            self.assertEqual(self.client.patch(f"/api/v1/{kind}/", {}, format="json").status_code, 405)

    def test_authenticated_user_without_visible_parent_gets_empty_lists(self):
        self.client.force_login(get_user_model().objects.create_user(username="financial-empty"))
        for kind in ("fund-items", "budgets", "expenses"):
            self.assertEqual(self.ids(kind), [])
            self.assertEqual(self.client.get(f"/api/v1/{kind}/export/", {"format": "csv"}).status_code, 200)

    def test_fund_item_filters_count_and_scoped_contract_sheet(self):
        self.assertEqual(self.ids("fund-items", type=self.type.pk, project=self.project.pk, participant=self.employee.pk,
                                  institution=self.institution.pk, funder=self.funder.pk, fundref="A-1", available=50), [self.item.pk])
        self.assertEqual(self.ids("fund-items", available=101), [])
        self.assertEqual(self.ids("fund-items", active="false"), [self.item.pk] if not self.fund.is_active else [])
        self.assertEqual(self.ids("fund-items", active="true"), [self.item.pk] if self.fund.is_active else [])
        self.assertEqual(self.ids("fund-items", project=self.hidden.pk), [])
        row = self.client.get("/api/v1/fund-items/").data["results"][0]
        self.assertEqual(row["contract_count"], 1)
        contracts = self.client.get(f"/api/v1/fund-items/{self.item.pk}/contracts/")
        self.assertEqual([item["id"] for item in contracts.data], [self.contract.pk])
        self.assertEqual(self.client.get(f"/api/v1/fund-items/{self.hidden_item.pk}/contracts/").status_code, 404)
        self.type.is_hr = False
        self.type.save()
        self.assertIsNone(self.client.get("/api/v1/fund-items/").data["results"][0]["contract_count"])

    def test_budget_filters_and_available_use_model_convention(self):
        self.assertEqual(self.client.get("/api/v1/budgets/").data["results"][0]["contract_types"], [])
        self.assertEqual(self.ids("budgets", type=self.type.pk, project=self.project.pk, institution=self.institution.pk,
                                  funder=self.funder.pk, fundref="A-1", available=100), [self.budget.pk])
        self.assertEqual(self.ids("budgets", available=101), [])
        self.budget.contract_type.add(self.contract_type)
        self.budget.employee = self.employee
        self.budget.emp_type = self.employee_type
        self.budget.save()
        self.assertEqual(self.ids("budgets", contract_type=self.contract_type.pk), [self.budget.pk])
        self.assertEqual(self.ids("budgets", employee=self.employee.pk, emp_type=self.employee_type.pk), [self.budget.pk])
        self.assertEqual(self.ids("budgets", contract_type=999999), [])

    def test_expense_filters_dates_are_inclusive_and_export_is_visible(self):
        self.assertEqual(self.ids("expenses", after="2026-03-01", before="2026-03-01", type=self.type.pk,
                                  desc="salary", project=self.project.pk, funder=self.funder.pk, institution=self.institution.pk,
                                  status="r", fundref="A-1", expense_id="OPEN"), [self.expense.pk])
        self.assertEqual(self.ids("expenses", after="2026-03-02"), [])
        self.assertEqual(self.ids("expenses", ordering="expense_id", limit=1), [self.expense.pk])
        for kind in ("fund-items", "budgets", "expenses"):
            response = self.client.get(f"/api/v1/{kind}/export/", {"format": "csv", "limit": 1})
            self.assertEqual(response.status_code, 200, getattr(response, "data", None))
            self.assertNotIn(b"SECRET", response.content)
            self.assertNotIn(b"Secret budget", response.content)
        self.assertEqual(self.client.get("/api/v1/financial/organizations/", {"kind": "funders", "search": "SECRET"}).data["results"], [])
        self.assertEqual(self.client.get("/api/v1/financial/organizations/", {"kind": "funders", "id": "bad"}).status_code, 400)

    def test_stale_uses_historical_dashboard_slot(self):
        with patch("fund.financial_tools_api_v1.getDashboardTimeSlot", return_value={"from": date(2026, 1, 1), "to": date(2026, 12, 31)}) as slot:
            self.assertEqual(self.ids("fund-items", stale="true"), [self.item.pk])
            self.assertEqual(self.ids("fund-items", stale="false"), [])
            self.assertEqual(slot.call_count, 2)
