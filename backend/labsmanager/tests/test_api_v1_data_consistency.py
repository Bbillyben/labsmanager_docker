"""Focused coverage for the first read-only consistency rule."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from endpoints.models import Milestones
from expense.models import Contract, Expense
from data_consistency.models import DataConsistencyException
from fund.models import Cost_Type, Fund, Fund_Institution
from project.models import Institution, Participant, Project
from staff.models import Employee


class DataConsistencyV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="consistency-reader")
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="expense", codename="view_contract",
        ))
        self.client.force_login(self.user)
        self.employee = Employee.objects.create(first_name="Alice", last_name="Example")
        self.project = Project.objects.create(name="Consistency project")
        self.leader = Employee.objects.create(first_name="Lead", last_name="Example")
        self.lead_participation = Participant.objects.create(
            project=self.project, employee=self.leader, status="l",
        )
        funder = Fund_Institution.objects.create(name="Funder", short_name="FUN")
        institution = Institution.objects.create(name="Institution", short_name="INS")
        self.fund = Fund.objects.create(
            project=self.project, funder=funder, institution=institution, ref="CONSISTENCY",
        )

    def contract(self):
        return Contract.objects.create(employee=self.employee, fund=self.fund, status="prov")

    def allow_decisions(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="data_consistency",
            codename__in=("add_dataconsistencyexception", "change_dataconsistencyexception"),
        ))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def accept(self, contract, reason=""):
        return self.client.post(
            f"/api/v1/data-consistency/issues/contract_employee_not_project_participant/{contract.pk}/accept/",
            {"employee_id": contract.employee_id, "project_id": contract.fund.project_id,
             "reason": reason}, format="json",
        )

    def issue_count(self, status="active"):
        response = self.client.get("/api/v1/data-consistency/issues/", {"status": status})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["count"]

    def rule_issues(self, rule_key, status="active"):
        response = self.client.get("/api/v1/data-consistency/issues/", {
            "rule_key": rule_key, "status": status,
        })
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["results"]

    def allow_fund_visibility(self):
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label__in=("fund", "project"),
            codename__in=("view_fund", "view_project"),
        ))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def allow_employee_visibility(self):
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="staff", codename="view_employee",
        ))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def set_project_dates(self):
        self.project.start_date = "2025-01-01"
        self.project.end_date = "2025-12-31"
        self.project.save(update_fields=["start_date", "end_date"])

    def test_contract_employee_dates_and_open_boundaries(self):
        self.allow_employee_visibility()
        self.employee.entry_date = "2025-01-01"
        self.employee.exit_date = "2025-12-31"
        self.employee.save(update_fields=["entry_date", "exit_date"])
        contract = self.contract()
        contract.start_date = "2025-02-01"
        contract.end_date = "2025-11-30"
        contract.save(update_fields=["start_date", "end_date"])
        rule = "contract_outside_employee_dates"
        self.assertEqual(self.rule_issues(rule), [])
        contract.start_date = "2024-12-01"
        contract.save(update_fields=["start_date"])
        self.assertEqual(self.rule_issues(rule)[0]["reason"], "starts_before_project")
        contract.start_date = "2025-02-01"
        contract.end_date = "2026-01-01"
        contract.save(update_fields=["start_date", "end_date"])
        self.assertEqual(self.rule_issues(rule)[0]["reason"], "ends_after_project")
        contract.start_date = None
        contract.save(update_fields=["start_date"])
        self.assertEqual(self.rule_issues(rule)[0]["reason"], "both")
        self.employee.entry_date = None
        self.employee.exit_date = None
        self.employee.save(update_fields=["entry_date", "exit_date"])
        self.assertEqual(self.rule_issues(rule), [])

    def test_milestone_and_task_dates_are_distinct(self):
        self.allow_fund_visibility()
        self.set_project_dates()
        milestone = Milestones.objects.create(project=self.project, name="Review", end_date="2025-06-01")
        task = Milestones.objects.create(project=self.project, name="Work", start_date="2025-03-01", end_date="2025-09-01")
        milestone_rule = "milestone_outside_project_dates"
        task_rule = "task_outside_project_dates"
        self.assertEqual(self.rule_issues(milestone_rule), [])
        self.assertEqual(self.rule_issues(task_rule), [])
        milestone.end_date = "2024-12-01"
        milestone.save(update_fields=["end_date"])
        self.assertEqual(self.rule_issues(milestone_rule)[0]["reason"], "starts_before_project")
        task.start_date = "2024-12-01"
        task.end_date = "2026-01-01"
        task.save(update_fields=["start_date", "end_date"])
        self.assertEqual(self.rule_issues(task_rule)[0]["reason"], "both")
        task.start_date = "2025-03-01"
        task.save(update_fields=["start_date"])
        self.assertEqual(self.rule_issues(task_rule)[0]["reason"], "ends_after_project")
        task.end_date = None
        task.save(update_fields=["end_date"])
        self.assertEqual(self.rule_issues(task_rule)[0]["reason"], "ends_after_project")
        self.project.start_date = None
        self.project.end_date = None
        self.project.save(update_fields=["start_date", "end_date"])
        self.assertEqual(self.rule_issues(milestone_rule), [])
        self.assertEqual(self.rule_issues(task_rule), [])

    def test_contract_fund_dates_and_open_boundaries(self):
        self.allow_fund_visibility()
        self.fund.start_date = "2025-01-01"
        self.fund.end_date = "2025-12-31"
        self.fund.save(update_fields=["start_date", "end_date"])
        contract = self.contract()
        contract.start_date = "2025-02-01"
        contract.end_date = "2025-11-30"
        contract.save(update_fields=["start_date", "end_date"])
        rule = "contract_outside_fund_dates"
        self.assertEqual(self.rule_issues(rule), [])
        contract.start_date = "2024-12-01"
        contract.end_date = "2026-01-01"
        contract.save(update_fields=["start_date", "end_date"])
        issue = self.rule_issues(rule)[0]
        self.assertEqual(issue["fund_id"], self.fund.pk)
        self.assertEqual(issue["reason"], "both")
        contract.start_date = None
        contract.end_date = "2025-11-30"
        contract.save(update_fields=["start_date", "end_date"])
        self.assertEqual(self.rule_issues(rule)[0]["reason"], "starts_before_project")
        self.fund.start_date = None
        self.fund.end_date = None
        self.fund.save(update_fields=["start_date", "end_date"])
        self.assertEqual(self.rule_issues(rule), [])

    def test_expense_uses_its_date_not_expense_point_value_date(self):
        self.allow_fund_visibility()
        self.fund.start_date = "2025-01-01"
        self.fund.end_date = "2025-12-31"
        self.fund.save(update_fields=["start_date", "end_date"])
        cost_type = Cost_Type.objects.create(short_name="TEST", name="Test expense")
        expense = Expense.objects.create(
            fund_item=self.fund, type=cost_type, date="2025-06-01", amount=10,
        )
        rule = "expense_outside_fund_dates"
        self.assertEqual(self.rule_issues(rule), [])
        expense.date = "2024-12-01"
        expense.save(update_fields=["date"])
        self.assertEqual(self.rule_issues(rule)[0]["reason"], "starts_before_project")
        expense.date = "2026-01-01"
        expense.save(update_fields=["date"])
        self.assertEqual(self.rule_issues(rule)[0]["reason"], "ends_after_project")
        self.fund.start_date = None
        self.fund.end_date = None
        self.fund.save(update_fields=["start_date", "end_date"])
        self.assertEqual(self.rule_issues(rule), [])

    def test_project_without_leader_needs_manual_correction(self):
        self.allow_fund_visibility()
        rule = "project_without_leader"
        self.assertEqual(self.rule_issues(rule), [])
        self.lead_participation.delete()
        issue = self.rule_issues(rule)[0]
        self.assertEqual(issue["project_id"], self.project.pk)
        self.assertNotIn("child_start_date", issue)
        self.allow_decisions()
        response = self.client.post(
            f"/api/v1/data-consistency/issues/{rule}/{self.project.pk}/accept/",
            {"project_id": self.project.pk}, format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(self.rule_issues(rule, "accepted")), 1)
        Participant.objects.create(project=self.project, employee=self.leader, status="l")
        self.assertEqual(self.rule_issues(rule), [])
        self.assertEqual(self.rule_issues(rule, "accepted"), [])

    def test_new_issue_identities_accept_and_invalidate_independently(self):
        self.allow_fund_visibility()
        self.allow_decisions()
        self.set_project_dates()
        self.fund.start_date = "2025-01-01"
        self.fund.end_date = "2025-12-31"
        self.fund.save(update_fields=["start_date", "end_date"])
        cost_type = Cost_Type.objects.create(short_name="TEST", name="Test expense")
        first = Expense.objects.create(fund_item=self.fund, type=cost_type, date="2026-01-01", amount=10)
        second = Expense.objects.create(fund_item=self.fund, type=cost_type, date="2026-02-01", amount=10)
        milestone = Milestones.objects.create(project=self.project, name="Late", end_date="2026-01-01")
        expense_rule = "expense_outside_fund_dates"
        planning_rule = "milestone_outside_project_dates"
        for rule, object_id in ((expense_rule, first.pk), (expense_rule, second.pk),
                                (planning_rule, milestone.pk)):
            response = self.client.post(
                f"/api/v1/data-consistency/issues/{rule}/{object_id}/accept/",
                {"project_id": self.project.pk}, format="json",
            )
            self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(self.rule_issues(expense_rule, "accepted")), 2)
        self.assertEqual(len(self.rule_issues(planning_rule, "accepted")), 1)
        first.date = "2025-06-01"
        first.save(update_fields=["date"])
        self.assertEqual(len(self.rule_issues(expense_rule, "accepted")), 1)
        first.date = "2026-03-01"
        first.save(update_fields=["date"])
        self.assertEqual(len(self.rule_issues(expense_rule)), 1)

    def test_contract_dates_inside_and_outside_project(self):
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="project", codename="view_project",
        ))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        self.project.start_date = "2025-01-01"
        self.project.end_date = "2025-12-31"
        self.project.save(update_fields=["start_date", "end_date"])
        contract = self.contract()
        contract.start_date = "2025-02-01"
        contract.end_date = "2025-11-30"
        contract.save(update_fields=["start_date", "end_date"])
        rule = "contract_outside_project_dates"
        self.assertEqual(self.rule_issues(rule), [])
        contract.start_date = "2024-12-01"
        contract.end_date = "2026-01-01"
        contract.save(update_fields=["start_date", "end_date"])
        issue = self.rule_issues(rule)[0]
        self.assertEqual(issue["contract_id"], contract.pk)
        self.assertEqual(issue["reason"], "both")
        self.assertEqual(issue["project_start_date"], "2025-01-01")
        self.assertEqual(issue["child_end_date"], "2026-01-01")

    def test_fund_dates_inside_outside_and_open_boundary(self):
        self.allow_fund_visibility()
        self.project.start_date = "2025-01-01"
        self.project.end_date = "2025-12-31"
        self.project.save(update_fields=["start_date", "end_date"])
        self.fund.start_date = "2025-02-01"
        self.fund.end_date = "2025-11-30"
        self.fund.save(update_fields=["start_date", "end_date"])
        rule = "fund_outside_project_dates"
        self.assertEqual(self.rule_issues(rule), [])
        self.fund.start_date = "2024-12-01"
        self.fund.end_date = "2026-01-01"
        self.fund.save(update_fields=["start_date", "end_date"])
        issue = self.rule_issues(rule)[0]
        self.assertEqual(issue["fund_id"], self.fund.pk)
        self.assertEqual(issue["reason"], "both")
        self.fund.start_date = None
        self.fund.end_date = "2025-11-30"
        self.fund.save(update_fields=["start_date", "end_date"])
        self.assertEqual(self.rule_issues(rule)[0]["reason"], "starts_before_project")

    def test_fund_exception_is_rule_specific_and_closes_when_project_extended(self):
        self.allow_fund_visibility()
        self.allow_decisions()
        self.project.start_date = "2025-01-01"
        self.project.end_date = "2025-12-31"
        self.project.save(update_fields=["start_date", "end_date"])
        self.fund.start_date = "2024-01-01"
        self.fund.end_date = "2026-12-31"
        self.fund.save(update_fields=["start_date", "end_date"])
        rule = "fund_outside_project_dates"
        response = self.client.post(
            f"/api/v1/data-consistency/issues/{rule}/{self.fund.pk}/accept/",
            {"project_id": self.project.pk}, format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.rule_issues(rule), [])
        self.assertEqual(len(self.rule_issues(rule, "accepted")), 1)
        self.project.start_date = "2024-01-01"
        self.project.end_date = "2026-12-31"
        self.project.save(update_fields=["start_date", "end_date"])
        exception = DataConsistencyException.objects.get(fund_id=self.fund.pk)
        self.assertEqual(exception.closed_reason, "changed")
        self.assertEqual(self.rule_issues(rule, "accepted"), [])
        self.assertEqual(self.rule_issues(rule), [])
        self.project.start_date = "2025-01-01"
        self.project.save(update_fields=["start_date"])
        self.assertEqual(len(self.rule_issues(rule)), 1)

    def test_fund_dates_do_not_leak_without_fund_visibility(self):
        self.project.start_date = "2025-01-01"
        self.project.save(update_fields=["start_date"])
        self.fund.start_date = "2024-01-01"
        self.fund.save(update_fields=["start_date"])
        self.assertEqual(self.rule_issues("fund_outside_project_dates"), [])

    def test_project_dates_do_not_leak_from_visible_contract(self):
        self.project.start_date = "2025-01-01"
        self.project.save(update_fields=["start_date"])
        contract = self.contract()
        contract.start_date = "2024-01-01"
        contract.save(update_fields=["start_date"])
        self.assertEqual(self.rule_issues("contract_outside_project_dates"), [])

    def test_participant_prevents_issue_regardless_of_dates(self):
        self.contract()
        Participant.objects.create(
            project=self.project, employee=self.employee, end_date="2020-01-01",
        )
        response = self.client.get("/api/v1/data-consistency/issues/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(self.client.get("/api/v1/data-consistency/summary/").data["total"], 0)

    def test_missing_participant_is_one_issue_per_contract_and_paginated(self):
        first = self.contract()
        second = self.contract()
        summary = self.client.get("/api/v1/data-consistency/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["total"], 2)
        self.assertEqual(summary.data["categories"], [{"key": "contracts", "count": 2}])
        first_page = self.client.get("/api/v1/data-consistency/issues/", {"limit": 1})
        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(first_page.data["count"], 2)
        issue = first_page.data["results"][0]
        self.assertEqual(issue["rule_key"], "contract_employee_not_project_participant")
        self.assertEqual(issue["contract_id"], first.pk)
        self.assertEqual(issue["employee_id"], self.employee.pk)
        self.assertEqual(issue["project_id"], self.project.pk)
        second_page = self.client.get("/api/v1/data-consistency/issues/", {"limit": 1, "offset": 1})
        self.assertEqual(second_page.data["results"][0]["contract_id"], second.pk)

    def test_contract_visibility_is_shared_with_hub(self):
        self.contract()
        other = get_user_model().objects.create_user(username="no-visible-contracts")
        self.client.force_login(other)
        self.assertEqual(self.client.get("/api/v1/data-consistency/summary/").data["total"], 0)
        self.assertEqual(self.client.get("/api/v1/data-consistency/issues/").data["count"], 0)
        self.client.logout()
        self.assertEqual(self.client.get("/api/v1/data-consistency/issues/").status_code, 401)

    def test_accept_and_reopen_only_the_current_contract_issue(self):
        contract = self.contract()
        self.allow_decisions()
        self.assertEqual(self.issue_count(), 1)
        accepted = self.accept(contract, "Intentional assignment")
        self.assertEqual(accepted.status_code, 201, accepted.data)
        exception = DataConsistencyException.objects.get(pk=accepted.data["exception"]["id"])
        self.assertEqual(exception.accepted_by, self.user)
        self.assertEqual(exception.reason, "Intentional assignment")
        self.assertEqual(self.issue_count(), 0)
        self.assertEqual(self.issue_count("accepted"), 1)
        self.assertEqual(self.client.get("/api/v1/data-consistency/summary/").data["accepted_total"], 1)
        reopened = self.client.post(f"/api/v1/data-consistency/exceptions/{exception.pk}/reopen/")
        self.assertEqual(reopened.status_code, 200, reopened.data)
        exception.refresh_from_db()
        self.assertEqual(exception.closed_reason, "reopened")
        self.assertIsNotNone(exception.closed_at)
        self.assertEqual(self.issue_count(), 1)
        self.assertEqual(self.issue_count("accepted"), 0)

    def test_resolved_then_reappeared_issue_does_not_inherit_exception(self):
        contract = self.contract()
        self.allow_decisions()
        self.assertEqual(self.accept(contract).status_code, 201)
        participant = Participant.objects.create(project=self.project, employee=self.employee)
        exception = DataConsistencyException.objects.get(contract_id=contract.pk)
        self.assertEqual(exception.closed_reason, "resolved")
        self.assertEqual(self.issue_count(), 0)
        participant.delete()
        self.assertEqual(self.issue_count(), 1)
        self.assertEqual(self.issue_count("accepted"), 0)

    def test_contract_employee_and_fund_project_changes_close_old_decisions(self):
        contract = self.contract()
        self.allow_decisions()
        self.assertEqual(self.accept(contract).status_code, 201)
        new_employee = Employee.objects.create(first_name="Bob", last_name="Example")
        contract.employee = new_employee
        contract.save(update_fields=["employee"])
        self.assertEqual(DataConsistencyException.objects.get(contract_id=contract.pk).closed_reason,
                         "relation_changed")
        self.assertEqual(self.issue_count(), 1)
        self.assertEqual(self.accept(contract).status_code, 201)
        new_project = Project.objects.create(name="Second consistency project")
        self.fund.project = new_project
        self.fund.save(update_fields=["project"])
        self.assertEqual(self.issue_count(), 1)
        self.assertEqual(self.issue_count("accepted"), 0)
        self.assertEqual(DataConsistencyException.objects.filter(contract_id=contract.pk,
                         closed_reason="relation_changed").count(), 2)

    def test_accept_requires_admin_permission_and_rechecks_issue(self):
        contract = self.contract()
        self.assertEqual(self.accept(contract).status_code, 403)
        self.allow_decisions()
        participant = Participant.objects.create(project=self.project, employee=self.employee)
        self.assertEqual(self.accept(contract).status_code, 409)
        participant.delete()
        stale = self.client.post(
            f"/api/v1/data-consistency/issues/contract_employee_not_project_participant/{contract.pk}/accept/",
            {"employee_id": contract.employee_id, "project_id": self.project.pk + 99}, format="json",
        )
        self.assertEqual(stale.status_code, 409)

    def test_dashboard_catalog_and_action_capabilities_use_backend_permissions(self):
        self.contract()
        self.assertEqual(self.client.get("/api/v1/data-consistency/summary/").data["capabilities"],
                         {"can_accept": False, "can_reopen": False})
        self.assertFalse(self.client.get("/api/v1/me/").data["capabilities"]["manage_data_consistency"])
        self.allow_decisions()
        self.assertEqual(self.client.get("/api/v1/data-consistency/summary/").data["capabilities"],
                         {"can_accept": True, "can_reopen": True})
        self.assertTrue(self.client.get("/api/v1/me/").data["capabilities"]["manage_data_consistency"])
        catalog = self.client.get("/api/v1/dashboards/catalog/")
        self.assertEqual(catalog.status_code, 200, catalog.data)
        self.assertIn("core.data-consistency", {source["key"] for source in catalog.data["sources"]})
        self.assertIn("core.data-consistency", {definition["key"] for definition in catalog.data["definitions"]})
        dashboard = self.client.post("/api/v1/dashboards/", {"name": "Review", "template": "blank"}, format="json")
        widget = self.client.post(f"/api/v1/dashboards/{dashboard.data['id']}/widgets/",
                                  {"source_key": "core.data-consistency", "renderer_key": "data-consistency",
                                   "config": {}}, format="json")
        self.assertEqual(widget.status_code, 201, widget.data)
        self.assertEqual(widget.data["data"]["summary_url"], "/api/v1/data-consistency/summary/")
