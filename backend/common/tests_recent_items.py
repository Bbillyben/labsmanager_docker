from datetime import date
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from common.models import RecentItem
from fund.models import Budget, Cost_Type, Fund, Fund_Institution
from expense.models import Contract, Contract_type
from global_search.business_providers import FundSearchProvider
from project.models import Institution, Participant, Project
from staff.models import Employee, Team


class RecentItemsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="recent-reader")
        self.other_user = get_user_model().objects.create_user(username="recent-other")
        self.employee = Employee.objects.create(first_name="Jean", last_name="Dupont", user=self.user)
        self.project = Project.objects.create(name="Visible project")
        self.hidden = Project.objects.create(name="Hidden project")
        self.participant = Participant.objects.create(project=self.project, employee=self.employee, status="l")
        funder = Fund_Institution.objects.create(name="Agency", short_name="ANR")
        manager = Institution.objects.create(name="University", short_name="UNI")
        self.fund = Fund.objects.create(project=self.project, funder=funder, institution=manager,
                                        ref="FUND-42", start_date=date(2026, 1, 1), end_date=date(2027, 1, 1))
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = "/api/v1/recent-items/"

    def post(self, url_id, obj_id=None):
        return self.client.post(self.url, {"url_id": url_id, "obj_id": obj_id}, format="json")

    def test_object_and_page_tracking_are_unique_and_ordered(self):
        self.assertEqual(self.post("project", self.project.pk).status_code, 201)
        self.assertEqual(self.post("calendar").status_code, 404)
        permission = Permission.objects.get(codename="display_calendar", content_type__app_label="common")
        self.user.user_permissions.add(permission)
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.post("calendar").status_code, 201)
        page = RecentItem.objects.get(user=self.user, url_id="calendar")
        self.assertEqual(self.post("calendar").status_code, 200)
        page.refresh_from_db()
        self.assertEqual(RecentItem.objects.filter(user=self.user, url_id="calendar").count(), 1)
        self.assertEqual(self.post("project", self.project.pk).status_code, 200)
        self.assertEqual(RecentItem.objects.filter(user=self.user).count(), 2)
        self.assertEqual([item["url_id"] for item in self.client.get(self.url).data], ["project", "calendar"])
        self.assertLessEqual(page.last_viewed_at, RecentItem.objects.get(user=self.user, url_id="project").last_viewed_at)
        RecentItem.objects.create(user=self.other_user, url_id="calendar")
        self.assertEqual(RecentItem.objects.filter(url_id="calendar").count(), 2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            RecentItem.objects.create(user=self.user, url_id="calendar")

    def test_fund_destination_matches_global_search_and_lost_access_disappears(self):
        response = self.post("fund", self.fund.pk)
        self.assertEqual(response.status_code, 201, response.data)
        expected = f"/app/projects/{self.project.pk}/funding#fund-row-{self.fund.pk}"
        self.assertEqual(response.data["url"], expected)
        self.assertEqual(FundSearchProvider().make_result(self.fund, score=0, match_reason="Recent").url, expected)
        self.assertEqual(self.client.get(self.url).data[0]["url"], expected)
        self.participant.delete()
        self.assertEqual(self.client.get(self.url).data, [])
        self.assertEqual(RecentItem.objects.filter(user=self.user).count(), 1)

    def test_invalid_hidden_and_deleted_destinations(self):
        self.assertEqual(self.post("unknown", 1).status_code, 400)
        self.assertEqual(self.post("project", None).status_code, 400)
        self.assertEqual(self.post("project", -1).status_code, 400)
        self.assertEqual(self.post("calendar", self.project.pk).status_code, 400)
        self.assertEqual(self.post("project", self.hidden.pk).status_code, 404)
        self.assertEqual(self.post("project", self.project.pk).status_code, 201)
        self.project.delete()
        self.assertEqual(self.client.get(self.url).data, [])

    def test_page_capability_is_rechecked(self):
        permission = Permission.objects.get(codename="display_calendar", content_type__app_label="common")
        self.user.user_permissions.add(permission)
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.post("calendar").status_code, 201)
        self.user.user_permissions.remove(permission)
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(self.url).data, [])

    def test_employee_contract_team_budget_and_organization_destinations(self):
        self.assertEqual(self.post("employee", self.employee.pk).data["url"], f"/app/employees/{self.employee.pk}")
        team = Team.objects.create(name="Visible team", leader=self.employee)
        self.assertEqual(self.post("team", team.pk).data["url"], f"/app/teams/{team.pk}")
        contract = Contract.objects.create(employee=self.employee, fund=self.fund,
                                           contract_type=Contract_type.objects.create(name="Research"))
        self.assertEqual(self.post("contract", contract.pk).data["url"],
                         f"/app/tools/contracts?employee={self.employee.pk}")
        budget = Budget.objects.create(fund=self.fund, cost_type=Cost_Type.objects.create(name="Equipment", short_name="EQ"),
                                       amount=100, desc="Equipment budget")
        self.assertEqual(self.post("budget", budget.pk).data["url"], f"/app/projects/{self.project.pk}/budgets")
        self.assertEqual(self.post("institution", self.fund.institution_id).status_code, 404)
        permission = Permission.objects.get(codename="display_infos", content_type__app_label="common")
        self.user.user_permissions.add(permission)
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.post("institution", self.fund.institution_id).data["url"],
                         f"/app/organizations/institutions/{self.fund.institution_id}")
        self.assertEqual(self.post("funder", self.fund.funder_id).data["url"],
                         f"/app/organizations/funders/{self.fund.funder_id}")

    def test_page_destinations_and_overscan_after_unavailable_items(self):
        for url_id, url in (("fund-explorer", "/app/tools/fund-items"),
                            ("budget-explorer", "/app/tools/budgets"), ("expenses", "/app/tools/expenses")):
            self.assertEqual(self.post(url_id).data["url"], url)
        for number in range(12):
            RecentItem.objects.create(user=self.user, url_id="project", obj_id=900000 + number)
        response = self.client.get(self.url)
        self.assertEqual([item["url_id"] for item in response.data], ["expenses", "budget-explorer", "fund-explorer"])
