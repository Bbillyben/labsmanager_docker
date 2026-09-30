from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from expense.models import Expense
from fund.models import Budget, Contribution
from settings.models import LMProjectSetting

from .test_api_v1_funding import ProjectFundingV1Tests


class ProjectBudgetsV1Tests(APITestCase):
    """Project visibility and change rules also govern the shared Budget base."""

    def setUp(self):
        ProjectFundingV1Tests.setUp(self)
        self.type.is_hr = True
        self.type.save()
        self.budget = Budget.objects.create(fund=self.fund, cost_type=self.type, amount=Decimal("100.00"), desc="Staff")
        self.hidden_budget = Budget.objects.create(fund=self.hidden_fund, cost_type=self.type, amount=Decimal("100.00"))
        self.contribution = Contribution.objects.create(fund=self.fund, cost_type=self.other_type,
                                                        amount=Decimal("75.00"), start_date=date(2026, 1, 1),
                                                        end_date=date(2026, 6, 30), desc="Partner")
        LMProjectSetting.set_setting("EXPENSE_CALCULATION", "e", change_user=None, project=self.project)

    grant = ProjectFundingV1Tests.grant

    def url(self, kind, item=None, project=None):
        name = f"project-{kind}-detail" if item else f"project-{kind}s"
        kwargs = {"pk": (project or self.project).pk}
        if item:
            kwargs["item_id"] = item.pk
        return reverse(f"api_v1:{name}", kwargs=kwargs)

    def expense_url(self, item=None, budget=None):
        kwargs = {"pk": self.project.pk, "budget_id": (budget or self.budget).pk}
        if item:
            kwargs["expense_id"] = item.pk
        return reverse("api_v1:project-budget-expense-detail" if item else "api_v1:project-budget-expenses", kwargs=kwargs)

    def test_budget_visibility_capabilities_and_crud(self):
        response = self.client.get(self.url("budget"))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([item["id"] for item in response.data["items"]], [self.budget.pk])
        self.assertTrue(response.data["capabilities"]["can_add"])
        self.assertEqual(response.data["items"][0]["available"], "100.00")
        self.assertEqual(self.client.get(self.url("budget", self.hidden_budget)).status_code, 404)
        self.assertEqual(self.client.get(self.url("budget", project=self.hidden)).status_code, 404)
        created = self.client.post(self.url("budget"), {"fund_id": self.fund.pk, "cost_type_id": self.type.pk,
                                                         "amount": "50.00", "desc": "Second"}, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        item = Budget.objects.get(pk=created.data["id"])
        self.assertEqual(self.client.patch(self.url("budget", item), {"amount": "60.00"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(self.url("budget", item), {"cost_type_id": self.other_type.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(self.url("budget", item)).status_code, 204)
        self.assertFalse(Budget.objects.filter(pk=item.pk).exists())
        self.assertEqual(self.client.post(self.url("budget"), {"fund_id": self.hidden_fund.pk,
                                                         "cost_type_id": self.type.pk}, format="json").status_code, 400)

    def test_read_only_project_can_read_but_cannot_mutate(self):
        self.participation.status = "p"
        self.participation.save()
        self.grant("view_fund", "fund")
        for kind, item in (("budget", self.budget), ("contribution", self.contribution)):
            response = self.client.get(self.url(kind))
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(len(response.data["items"]), 1)
            self.assertFalse(response.data["capabilities"]["can_add"])
            self.assertFalse(response.data["items"][0]["capabilities"]["can_change"])
            self.assertEqual(self.client.post(self.url(kind), {}, format="json").status_code, 403)
            self.assertEqual(self.client.patch(self.url(kind, item), {"amount": "1.00"}, format="json").status_code, 403)
            self.assertEqual(self.client.delete(self.url(kind, item)).status_code, 403)
        self.assertEqual(self.client.get(self.expense_url()).status_code, 200)

    def test_hr_validation_and_contribution_dates(self):
        non_hr = {"fund_id": self.fund.pk, "cost_type_id": self.other_type.pk, "amount": "10.00",
                  "employee_id": self.employee.pk}
        self.assertEqual(self.client.post(self.url("budget"), non_hr, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.url("contribution"), non_hr, format="json").status_code, 400)
        invalid = {"fund_id": self.fund.pk, "cost_type_id": self.other_type.pk, "amount": "10.00",
                   "start_date": "2026-05-01", "end_date": "2026-04-01"}
        self.assertEqual(self.client.post(self.url("contribution"), invalid, format="json").status_code, 400)
        invalid["end_date"] = "2026-06-01"
        created = self.client.post(self.url("contribution"), invalid, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        item = Contribution.objects.get(pk=created.data["id"])
        self.assertNotIn("expenses", created.data)
        self.assertEqual(self.client.patch(self.url("contribution", item), {"end_date": "2026-07-01"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(self.url("contribution", item)).status_code, 204)
        self.assertEqual(self.client.get(f"/api/v1/projects/{self.project.pk}/contributions/{self.contribution.pk}/expenses/").status_code, 404)

    def test_budget_expenses_are_scoped_and_recalculate(self):
        payload = {"expense_id": "B-1", "desc": "Salary", "date": "2026-03-01",
                   "type_id": self.type.pk, "amount": "20.00"}
        created = self.client.post(self.expense_url(), payload, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        expense = Expense.objects.get(pk=created.data["id"])
        self.assertEqual(expense.budget_item_id, self.budget.pk)
        self.assertEqual(expense.fund_item_id, self.fund.pk)
        self.budget.refresh_from_db()
        self.assertEqual(self.budget.expense, Decimal("20.00"))
        detail = self.client.get(self.url("budget", self.budget)).data
        self.assertEqual((detail["expense"], detail["available"], detail["consumption_ratio"]),
                         ("20.00", "80.00", "0.2"))
        self.assertEqual(self.client.get(self.expense_url()).data["count"], 1)
        self.assertEqual(self.client.post(self.expense_url(), {**payload, "budget_id": self.hidden_budget.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.expense_url(budget=self.hidden_budget), payload, format="json").status_code, 404)
        self.assertEqual(self.client.patch(self.expense_url(expense), {"budget_id": None}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.expense_url(expense), {"amount": "30.00"}, format="json").status_code, 200)
        self.budget.refresh_from_db()
        self.assertEqual(self.budget.available, Decimal("70.00"))
        self.grant("delete_expense", "expense")
        self.assertEqual(self.client.delete(self.expense_url(expense)).status_code, 204)
        self.budget.refresh_from_db()
        self.assertEqual(self.budget.expense, Decimal("0.00"))
        self.assertEqual(self.budget.available, Decimal("100.00"))

    def test_deleting_budget_preserves_historical_expense_cascade(self):
        expense = Expense.objects.create(fund_item=self.fund, budget_item=self.budget, type=self.type,
                                         date=date(2026, 3, 1), amount=Decimal("10.00"))
        self.assertEqual(self.client.delete(self.url("budget", self.budget)).status_code, 204)
        self.assertFalse(Budget.objects.filter(pk=self.budget.pk).exists())
        self.assertFalse(Expense.objects.filter(pk=expense.pk).exists())
