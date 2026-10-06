from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from expense.models import Contract, Contract_expense, Expense, Expense_point
from fund.models import Budget, Cost_Type
from settings.models import LMProjectSetting

from .test_api_v1_funding import ProjectFundingV1Tests


class ExpenseV1Tests(APITestCase):
    """Reuse the Funding fixture while covering the new Expense boundary."""

    def setUp(self):
        ProjectFundingV1Tests.setUp(self)
        self.type.is_hr = True
        self.type.save()
        self.contract = Contract.objects.create(employee=self.employee, fund=self.fund)
        self.hidden_contract = Contract.objects.create(employee=self.employee, fund=self.hidden_fund)
        self.budget = Budget.objects.create(fund=self.fund, cost_type=self.type, amount=Decimal("500.00"))
        self.hidden_budget = Budget.objects.create(fund=self.hidden_fund, cost_type=self.type, amount=Decimal("500.00"))
        LMProjectSetting.set_setting("EXPENSE_CALCULATION", "e", change_user=None, project=self.project)

    grant = ProjectFundingV1Tests.grant

    def url(self, item=None):
        name = "fund-expense-detail" if item else "fund-expenses"
        kwargs = {"fund_id": self.fund.pk}
        if item:
            kwargs["expense_id"] = item.pk
        return reverse(f"api_v1:{name}", kwargs=kwargs)

    def payload(self, **kwargs):
        return {"expense_id": "REF-01", "desc": "First expense", "date": "2026-03-01", "type_id": self.type.pk,
                "amount": "20.00", **kwargs}

    def test_promotion_and_demotion_keep_parent_and_single_aggregate(self):
        created = self.client.post(self.url(), self.payload(), format="json")
        self.assertEqual(created.status_code, 201, created.data)
        item = Expense.objects.get(pk=created.data["id"])
        promoted = self.client.patch(self.url(item), {"contract_id": self.contract.pk}, format="json")
        self.assertEqual(promoted.status_code, 200, promoted.data)
        self.assertTrue(Contract_expense.objects.filter(pk=item.pk, contract=self.contract).exists())
        self.assertEqual(Expense.objects.filter(fund_item=self.fund).count(), 1)
        self.assertEqual(Expense_point.objects.get(fund=self.fund, type=self.type).amount, Decimal("-20.00"))
        demoted = self.client.patch(self.url(item), {"contract_id": None}, format="json")
        self.assertEqual(demoted.status_code, 200, demoted.data)
        self.assertTrue(Expense.objects.filter(pk=item.pk).exists())
        self.assertFalse(Contract_expense.objects.filter(pk=item.pk).exists())
        self.assertEqual(Expense.objects.filter(fund_item=self.fund).count(), 1)

    def test_hr_and_relation_validation(self):
        created = self.client.post(self.url(), self.payload(type_id=self.other_type.pk), format="json")
        self.assertEqual(created.status_code, 201, created.data)
        item = Expense.objects.get(pk=created.data["id"])
        self.assertEqual(self.client.patch(self.url(item), {"contract_id": self.contract.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.url(item), {"contract_id": self.contract.pk, "type_id": self.type.pk}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(self.url(item), {"type_id": self.other_type.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.url(item), {"contract_id": self.hidden_contract.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.url(item), {"budget_id": self.hidden_budget.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.url(item), {"budget_id": self.budget.pk}, format="json").status_code, 200)

    def test_negative_default_status_filters_and_sync(self):
        response = self.client.post(self.url(), self.payload(amount="-12.00"), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["status"], "r")
        self.assertEqual(response.data["amount"], "-12.00")
        self.assertEqual(self.client.get(self.url(), {"search": "REF-01"}).data["count"], 1)
        self.assertEqual(self.client.get(self.url(), {"search": "First"}).data["count"], 1)
        self.assertEqual(self.client.get(self.url(), {"type": self.other_type.pk}).data["count"], 0)
        self.assertEqual(self.client.get(self.url(), {"date_from": "2026-04-01"}).data["count"], 0)
        self.assertEqual(self.client.get(self.url(), {"date_to": "2026-02-01"}).data["count"], 0)
        self.assertEqual(self.client.get(self.url(), {"search": "REF-01", "type": self.type.pk, "date_from": "2026-03-01", "date_to": "2026-03-31"}).data["count"], 1)
        sync = reverse("api_v1:fund-expense-sync", kwargs={"fund_id": self.fund.pk})
        self.assertEqual(self.client.post(sync).status_code, 200)
        self.participation.status = "p"
        self.participation.save()
        self.grant("view_fund", "fund")
        self.assertEqual(self.client.post(sync).status_code, 403)
        self.participation.status = "l"
        self.participation.save()
        self.assertEqual(self.client.post(sync).status_code, 200)

    def test_simple_mode_and_contract_scope(self):
        LMProjectSetting.set_setting("EXPENSE_CALCULATION", "s", change_user=None, project=self.project)
        self.assertEqual(self.client.post(self.url(), self.payload(), format="json").status_code, 403)
        created = self.client.post(self.url(), self.payload(contract_id=self.contract.pk, budget_id=self.budget.pk), format="json")
        self.assertEqual(created.status_code, 201, created.data)
        contract_url = reverse("api_v1:contract-expenses", kwargs={"employee_id": self.employee.pk, "contract_id": self.contract.pk})
        self.assertEqual(self.client.get(contract_url).data["count"], 1)
        hidden_url = reverse("api_v1:fund-expenses", kwargs={"fund_id": self.hidden_fund.pk})
        self.assertEqual(self.client.get(hidden_url).status_code, 404)

    def test_budget_only_simple_mode_and_hybrid_sync(self):
        LMProjectSetting.set_setting("EXPENSE_CALCULATION", "s", change_user=None, project=self.project)
        self.assertTrue(self.client.get(self.url()).data["capabilities"]["can_add"])
        created = self.client.post(self.url(), self.payload(budget_id=self.budget.pk), format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.budget.refresh_from_db()
        self.assertEqual(self.budget.expense, Decimal("20.00"))
        self.assertEqual(self.point.amount, Decimal("-30.00"))
        sync = reverse("api_v1:fund-expense-sync", kwargs={"fund_id": self.fund.pk})
        self.assertFalse(self.client.get(self.url()).data["capabilities"]["can_sync_expenses"])
        self.assertEqual(self.client.post(sync).status_code, 403)
        LMProjectSetting.set_setting("EXPENSE_CALCULATION", "h", change_user=None, project=self.project)
        self.assertTrue(self.client.get(self.url()).data["capabilities"]["can_sync_expenses"])
        self.assertEqual(self.client.post(sync).status_code, 200)
        self.point.refresh_from_db()
        self.assertEqual(self.point.amount, Decimal("-20.00"))

    def test_edit_type_delete_and_fund_totals(self):
        self.grant("delete_expense", "expense")
        created = self.client.post(self.url(), self.payload(), format="json")
        self.assertEqual(created.status_code, 201, created.data)
        item = Expense.objects.get(pk=created.data["id"])
        self.assertEqual(self.client.patch(self.url(item), {"type_id": self.other_type.pk, "amount": "-5.00"}, format="json").status_code, 200)
        self.fund.refresh_from_db()
        self.assertEqual(Expense_point.objects.get(fund=self.fund, type=self.type).amount, Decimal("0.00"))
        self.assertEqual(Expense_point.objects.get(fund=self.fund, type=self.other_type).amount, Decimal("5.00"))
        self.assertEqual(self.fund.expense, Decimal("5.00"))
        self.assertEqual(self.client.delete(self.url(item)).status_code, 204)
        self.fund.refresh_from_db()
        self.assertEqual(self.fund.expense, Decimal("0.00"))
        self.assertFalse(Expense.objects.filter(pk=item.pk).exists())

    def test_contract_collection_is_strictly_scoped_and_paginated(self):
        another = Contract.objects.create(employee=self.employee, fund=self.fund)
        first = self.client.post(self.url(), self.payload(contract_id=self.contract.pk), format="json")
        second = self.client.post(self.url(), self.payload(expense_id="OTHER", contract_id=another.pk), format="json")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        scoped = reverse("api_v1:contract-expenses", kwargs={"employee_id": self.employee.pk, "contract_id": self.contract.pk})
        response = self.client.get(scoped)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], first.data["id"])
        from_contract = self.client.post(scoped, self.payload(expense_id="IN-CONTRACT", budget_id=self.budget.pk), format="json")
        self.assertEqual(from_contract.status_code, 201, from_contract.data)
        self.assertEqual(Contract_expense.objects.get(pk=from_contract.data["id"]).contract_id, self.contract.pk)
        self.assertEqual(from_contract.data["budget"]["id"], self.budget.pk)
        self.assertEqual(self.client.get(self.url(), {"page_size": 1}).data["count"], 3)
        self.assertIsNotNone(self.client.get(self.url(), {"page_size": 1}).data["next"])
        other_detail = reverse("api_v1:contract-expense-detail", kwargs={"employee_id": self.employee.pk, "contract_id": self.contract.pk, "expense_id": second.data["id"]})
        self.assertEqual(self.client.patch(other_detail, {"amount": "99.00"}, format="json").status_code, 404)

    def test_read_only_user_sees_data_but_cannot_mutate(self):
        created = self.client.post(self.url(), self.payload(), format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.participation.status = "p"
        self.participation.save()
        self.grant("view_fund", "fund")
        listing = self.client.get(self.url())
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["count"], 1)
        self.assertFalse(listing.data["capabilities"]["can_add"])
        self.assertFalse(listing.data["results"][0]["capabilities"]["can_change"])
        self.assertEqual(self.client.post(self.url(), self.payload(), format="json").status_code, 403)
        item_url = self.url(Expense.objects.get(pk=created.data["id"]))
        self.assertEqual(self.client.patch(item_url, {"amount": "1.00"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(item_url).status_code, 403)

    def test_all_historical_statuses_have_the_same_financial_aggregation(self):
        for status in ("e", "r", "p"):
            response = self.client.post(self.url(), self.payload(expense_id=status, status=status, amount="10.00"), format="json")
            self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Expense.objects.filter(fund_item=self.fund).count(), 3)
        point = Expense_point.objects.get(fund=self.fund, type=self.type)
        self.assertEqual(point.amount, Decimal("-30.00"))
        self.fund.refresh_from_db()
        self.assertEqual(self.fund.expense, Decimal("-30.00"))
