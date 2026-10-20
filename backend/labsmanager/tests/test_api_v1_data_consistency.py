"""Focused coverage for Data Consistency rules and actions."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from endpoints.models import Milestones
from expense.models import Contract, Expense
from data_consistency.models import DataConsistencyException
from data_consistency.api_v1 import accept_current_issue
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
        self.assertIsNone(issue["correction_action"])
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="project", codename="change_project",
        ))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        self.assertEqual(self.rule_issues(rule)[0]["correction_action"], "extend_dates")

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
        self.assertFalse(issue["can_add_participant"])
        self.allow_fund_visibility()
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="project", codename="add_participant",
        ))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        self.assertTrue(self.rule_issues("contract_employee_not_project_participant")[0]["can_add_participant"])
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

    def test_batch_accept_selected_rechecks_identity_and_reports_stale_items(self):
        first, second = self.contract(), self.contract()
        self.allow_decisions()
        url = "/api/v1/data-consistency/issues/contract_employee_not_project_participant/accept-batch/"
        payload = {"mode": "selected", "selected_count": 2, "reason": "Reviewed", "issues": [
            {"id": first.pk, "project_id": self.project.pk, "employee_id": self.employee.pk},
            {"id": second.pk, "project_id": self.project.pk, "employee_id": self.employee.pk},
        ]}
        replacement = Employee.objects.create(first_name="Bob", last_name="Example")
        second.employee = replacement
        second.save(update_fields=["employee"])
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, {"initially_selected": 2, "processed": 2,
                                         "succeeded": 1, "skipped": 1, "failed": 0})
        self.assertEqual(DataConsistencyException.objects.get(contract_id=first.pk).reason, "Reviewed")
        self.assertFalse(DataConsistencyException.objects.filter(contract_id=second.pk).exists())

    def test_batch_accept_global_includes_other_pages_and_respects_exclusions(self):
        contracts = [self.contract() for _ in range(28)]
        self.allow_decisions()
        url = "/api/v1/data-consistency/issues/contract_employee_not_project_participant/accept-batch/"
        first_page = self.client.get("/api/v1/data-consistency/issues/")
        self.assertEqual(first_page.data["count"], 28)
        self.assertEqual(len(first_page.data["results"]), 25)
        response = self.client.post(url, {"mode": "all", "excluded_ids": [contracts[0].pk],
                                          "selected_count": 27}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["succeeded"], 27)
        self.assertEqual(response.data["skipped"], 0)
        self.assertEqual(self.issue_count(), 1)
        self.assertFalse(DataConsistencyException.objects.filter(contract_id=contracts[0].pk).exists())
        self.assertTrue(DataConsistencyException.objects.filter(contract_id=contracts[-1].pk).exists())

    def test_batch_accept_enforces_permission_and_rule_scope(self):
        contract = self.contract()
        url = "/api/v1/data-consistency/issues/contract_employee_not_project_participant/accept-batch/"
        payload = {"mode": "selected", "selected_count": 1, "issues": [
            {"id": contract.pk, "project_id": self.project.pk, "employee_id": self.employee.pk},
        ]}
        self.assertEqual(self.client.post(url, payload, format="json").status_code, 403)
        self.allow_decisions()
        wrong_rule = self.client.post(
            "/api/v1/data-consistency/issues/contract_outside_project_dates/accept-batch/",
            payload, format="json",
        )
        self.assertEqual(wrong_rule.status_code, 200, wrong_rule.data)
        self.assertEqual(wrong_rule.data["succeeded"], 0)
        self.assertEqual(wrong_rule.data["skipped"], 1)
        self.assertEqual(self.issue_count(), 1)

        limited = get_user_model().objects.create_user(username="exception-only")
        limited.user_permissions.add(Permission.objects.get(
            content_type__app_label="data_consistency", codename="add_dataconsistencyexception",
        ))
        self.client.force_login(limited)
        invisible = self.client.post(url, payload, format="json")
        self.assertEqual(invisible.status_code, 200, invisible.data)
        self.assertEqual(invisible.data["succeeded"], 0)
        self.assertEqual(invisible.data["skipped"], 1)
        self.assertFalse(DataConsistencyException.objects.filter(contract_id=contract.pk).exists())

    def test_batch_accept_reports_partial_execution_failures(self):
        first, second = self.contract(), self.contract()
        self.allow_decisions()

        def accept_or_fail(user, rule, object_id, reason, expected=None):
            if object_id == second.pk:
                raise RuntimeError("Simulated item failure")
            return accept_current_issue(user, rule, object_id, reason, expected)

        with patch("data_consistency.api_v1.accept_current_issue", side_effect=accept_or_fail):
            response = self.client.post(
                "/api/v1/data-consistency/issues/contract_employee_not_project_participant/accept-batch/",
                {"mode": "selected", "selected_count": 2, "issues": [
                    {"id": first.pk, "project_id": self.project.pk, "employee_id": self.employee.pk},
                    {"id": second.pk, "project_id": self.project.pk, "employee_id": self.employee.pk},
                ]}, format="json",
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, {"initially_selected": 2, "processed": 2,
                                         "succeeded": 1, "skipped": 0, "failed": 1})
        self.assertTrue(DataConsistencyException.objects.filter(contract_id=first.pk).exists())
        self.assertFalse(DataConsistencyException.objects.filter(contract_id=second.pk).exists())

    def test_date_correction_unit_and_batch_share_current_parent_state(self):
        self.allow_decisions()
        self.allow_fund_visibility()
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="project", codename="change_project"))
        self.set_project_dates()
        first, second, third = self.contract(), self.contract(), self.contract()
        for contract, end in ((first, "2026-01-31"), (second, "2026-01-15"), (third, "2026-03-01")):
            contract.start_date = "2025-02-01"
            contract.end_date = end
            contract.save(update_fields=["start_date", "end_date"])
        rule = "contract_outside_project_dates"
        unit = self.client.post(f"/api/v1/data-consistency/issues/{rule}/{first.pk}/correct/",
                                {"project_id": self.project.pk, "employee_id": self.employee.pk}, format="json")
        self.assertEqual(unit.status_code, 200, unit.data)
        self.project.refresh_from_db()
        self.assertEqual(str(self.project.end_date), "2026-01-31")
        self.project.end_date = "2025-12-31"
        self.project.save(update_fields=["end_date"])
        result = self.client.post(f"/api/v1/data-consistency/issues/{rule}/correct-batch/", {
            "mode": "selected", "selected_count": 3,
            "issues": [{"id": item.pk, "project_id": self.project.pk, "employee_id": self.employee.pk}
                       for item in (first, second, third)],
        }, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data, {"selected": 3, "corrected": 2, "already_resolved": 1,
                                       "ignored": 0, "failed": 0})
        self.project.refresh_from_db()
        self.assertEqual(str(self.project.end_date), "2026-03-01")
        self.assertEqual(self.rule_issues(rule), [])

    def test_date_batch_global_exclusion_permissions_and_partial_failure(self):
        self.allow_fund_visibility()
        self.set_project_dates()
        first, second = self.contract(), self.contract()
        for contract in (first, second):
            contract.start_date = "2025-02-01"
            contract.end_date = "2026-01-31"
            contract.save(update_fields=["start_date", "end_date"])
        rule = "contract_outside_project_dates"
        url = f"/api/v1/data-consistency/issues/{rule}/correct-batch/"
        payload = {"mode": "all", "selected_count": 1, "excluded_ids": [first.pk]}
        denied = self.client.post(url, payload, format="json")
        self.assertEqual(denied.status_code, 200, denied.data)
        self.assertEqual(denied.data["ignored"], 1)
        self.allow_decisions()
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="project", codename="change_project"))
        result = self.client.post(url, payload, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data["selected"], 1)
        self.assertEqual(result.data["corrected"], 1)
        self.assertEqual(self.rule_issues(rule), [])

    def test_participant_batch_uses_contract_dates_and_resolves_shared_occurrences(self):
        first, second = self.contract(), self.contract()
        first.start_date, first.end_date = "2025-02-01", "2025-06-30"
        second.start_date, second.end_date = "2025-07-01", "2025-12-31"
        first.save(update_fields=["start_date", "end_date"])
        second.save(update_fields=["start_date", "end_date"])
        self.allow_decisions()
        self.allow_fund_visibility()
        self.allow_employee_visibility()
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="project", codename="add_participant"))
        summary = self.client.get("/api/v1/data-consistency/summary/")
        rules = {row["rule_key"]: row for row in summary.data["rules"]}
        self.assertEqual(rules["contract_employee_not_project_participant"]["correction_action"], "add_participants")
        self.assertIsNone(rules["project_without_leader"]["correction_action"])
        response = self.client.post(
            "/api/v1/data-consistency/issues/contract_employee_not_project_participant/correct-batch/",
            {"mode": "selected", "selected_count": 2, "issues": [
                {"id": item.pk, "project_id": self.project.pk, "employee_id": self.employee.pk}
                for item in (first, second)]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, {"selected": 2, "corrected": 1, "already_resolved": 1,
                                         "ignored": 0, "failed": 0})
        participants = Participant.objects.filter(project=self.project, employee=self.employee)
        self.assertEqual(participants.count(), 1)
        participant = participants.get()
        self.assertEqual(str(participant.start_date), "2025-02-01")
        self.assertEqual(str(participant.end_date), "2025-06-30")
        self.assertEqual(participant.status, "p")
        self.assertEqual(str(participant.quotity), "0.000")
        self.assertEqual(self.rule_issues("contract_employee_not_project_participant"), [])

    def test_participant_batch_global_exclusions_and_permissions(self):
        contracts = []
        for index in range(26):
            employee = Employee.objects.create(first_name=f"Person{index}", last_name="Example")
            contracts.append(Contract.objects.create(employee=employee, fund=self.fund, status="prov",
                                                     start_date="2025-01-01", end_date="2025-12-31"))
        self.allow_fund_visibility()
        self.allow_employee_visibility()
        url = "/api/v1/data-consistency/issues/contract_employee_not_project_participant/correct-batch/"
        first_page = self.client.get("/api/v1/data-consistency/issues/")
        self.assertEqual(first_page.data["count"], 26)
        self.assertEqual(len(first_page.data["results"]), 25)
        payload = {"mode": "all", "selected_count": 25, "excluded_ids": [contracts[0].pk]}
        denied = self.client.post(url, payload, format="json")
        self.assertEqual(denied.status_code, 200, denied.data)
        self.assertEqual(denied.data["ignored"], 25)
        self.assertEqual(Participant.objects.filter(project=self.project).count(), 1)
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="project", codename="add_participant"))
        result = self.client.post(url, payload, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data, {"selected": 25, "corrected": 25, "already_resolved": 0,
                                       "ignored": 0, "failed": 0})
        self.assertFalse(Participant.objects.filter(project=self.project, employee=contracts[0].employee).exists())
        self.assertTrue(Participant.objects.filter(project=self.project, employee=contracts[-1].employee).exists())

    def test_participant_batch_rechecks_existing_participation_and_contract_dates(self):
        contract = self.contract()
        contract.start_date = "2025-03-01"
        contract.end_date = "2025-08-31"
        contract.save(update_fields=["start_date", "end_date"])
        self.allow_fund_visibility()
        self.allow_employee_visibility()
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="project", codename="add_participant"))
        payload = {"mode": "selected", "selected_count": 1, "issues": [
            {"id": contract.pk, "project_id": self.project.pk, "employee_id": self.employee.pk}]}
        Participant.objects.create(project=self.project, employee=self.employee,
                                   start_date="2024-01-01", end_date="2024-12-31")
        result = self.client.post(
            "/api/v1/data-consistency/issues/contract_employee_not_project_participant/correct-batch/",
            payload, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data["already_resolved"], 1)
        self.assertEqual(Participant.objects.filter(project=self.project, employee=self.employee).count(), 1)

    def test_participant_batch_uses_each_contract_on_distinct_projects(self):
        other_project = Project.objects.create(name="Second consistency project")
        other_fund = Fund.objects.create(project=other_project, funder=self.fund.funder,
                                         institution=self.fund.institution, ref="SECOND")
        first = self.contract()
        second = Contract.objects.create(employee=self.employee, fund=other_fund, status="prov")
        first.start_date, first.end_date = "2025-01-01", "2025-04-30"
        second.start_date, second.end_date = "2025-09-01", "2026-02-28"
        first.save(update_fields=["start_date", "end_date"])
        second.save(update_fields=["start_date", "end_date"])
        self.allow_fund_visibility()
        self.allow_employee_visibility()
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="project", codename="add_participant"))
        response = self.client.post(
            "/api/v1/data-consistency/issues/contract_employee_not_project_participant/correct-batch/",
            {"mode": "selected", "selected_count": 2, "issues": [
                {"id": first.pk, "project_id": self.project.pk, "employee_id": self.employee.pk},
                {"id": second.pk, "project_id": other_project.pk, "employee_id": self.employee.pk}]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["corrected"], 2)
        first_part = Participant.objects.get(project=self.project, employee=self.employee)
        second_part = Participant.objects.get(project=other_project, employee=self.employee)
        self.assertEqual(str(first_part.start_date), "2025-01-01")
        self.assertEqual(str(first_part.end_date), "2025-04-30")
        self.assertEqual(str(second_part.start_date), "2025-09-01")
        self.assertEqual(str(second_part.end_date), "2026-02-28")

    def test_participant_batch_isolates_a_failed_contract(self):
        first = self.contract()
        second_employee = Employee.objects.create(first_name="Other", last_name="Example")
        second = Contract.objects.create(employee=second_employee, fund=self.fund, status="prov")
        first.start_date, first.end_date = "2025-01-01", "2025-06-30"
        second.start_date, second.end_date = None, "2025-12-31"
        first.save(update_fields=["start_date", "end_date"])
        second.save(update_fields=["start_date", "end_date"])
        self.allow_fund_visibility()
        self.allow_employee_visibility()
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="project", codename="add_participant"))
        result = self.client.post(
            "/api/v1/data-consistency/issues/contract_employee_not_project_participant/correct-batch/",
            {"mode": "all", "selected_count": 2}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data, {"selected": 2, "corrected": 1, "already_resolved": 0,
                                       "ignored": 0, "failed": 1})
        self.assertTrue(Participant.objects.filter(project=self.project, employee=self.employee).exists())
        self.assertFalse(Participant.objects.filter(project=self.project, employee=second_employee).exists())

    def test_participant_batch_does_not_redirect_a_stale_selection(self):
        contract = self.contract()
        replacement = Employee.objects.create(first_name="Replacement", last_name="Example")
        self.allow_fund_visibility()
        self.allow_employee_visibility()
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="project", codename="add_participant"))
        selected = {"id": contract.pk, "project_id": self.project.pk,
                    "employee_id": self.employee.pk}
        contract.employee = replacement
        contract.save(update_fields=["employee"])
        result = self.client.post(
            "/api/v1/data-consistency/issues/contract_employee_not_project_participant/correct-batch/",
            {"mode": "selected", "selected_count": 1, "issues": [selected]}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data["ignored"], 1)
        self.assertFalse(Participant.objects.filter(project=self.project, employee=replacement).exists())

    def test_date_batch_explicit_ids_across_pages_and_partial_failure(self):
        self.allow_decisions()
        self.allow_fund_visibility()
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="project", codename="change_project"))
        self.set_project_dates()
        contracts = [self.contract() for _ in range(26)]
        for contract in contracts:
            contract.start_date = "2025-02-01"
            contract.end_date = "2026-01-31"
            contract.save(update_fields=["start_date", "end_date"])
        rule = "contract_outside_project_dates"
        page = self.client.get("/api/v1/data-consistency/issues/", {"rule_key": rule})
        self.assertEqual(page.data["count"], 26)
        self.assertEqual(len(page.data["results"]), 25)
        from data_consistency.corrections import correct_date_issue

        def correct_or_fail(request, selected_rule, object_id, expected=None):
            if object_id == contracts[-1].pk:
                raise RuntimeError("Simulated item failure")
            return correct_date_issue(request, selected_rule, object_id, expected)

        with patch("data_consistency.api_v1.correct_date_issue", side_effect=correct_or_fail):
            result = self.client.post(f"/api/v1/data-consistency/issues/{rule}/correct-batch/", {
                "mode": "selected", "selected_count": 2,
                "issues": [{"id": item.pk, "project_id": self.project.pk, "employee_id": self.employee.pk}
                           for item in (contracts[0], contracts[-1])],
            }, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data, {"selected": 2, "corrected": 1, "already_resolved": 0,
                                       "ignored": 0, "failed": 1})
        self.project.refresh_from_db()
        self.assertEqual(str(self.project.end_date), "2026-01-31")
        self.assertEqual(self.rule_issues(rule), [])

    def test_employee_and_fund_date_corrections_use_existing_write_validation(self):
        self.allow_decisions()
        self.allow_employee_visibility()
        self.allow_fund_visibility()
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="fund", codename="change_fund"))
        self.employee.entry_date = "2025-01-01"
        self.employee.exit_date = "2025-12-31"
        self.employee.save(update_fields=["entry_date", "exit_date"])
        self.fund.start_date = "2025-01-01"
        self.fund.end_date = "2025-12-31"
        self.fund.save(update_fields=["start_date", "end_date"])
        contract = self.contract()
        contract.start_date = "2024-12-01"
        contract.end_date = "2026-01-01"
        contract.save(update_fields=["start_date", "end_date"])
        for rule in ("contract_outside_employee_dates", "contract_outside_fund_dates"):
            result = self.client.post(f"/api/v1/data-consistency/issues/{rule}/correct-batch/", {
                "mode": "all", "selected_count": 1,
            }, format="json")
            self.assertEqual(result.status_code, 200, result.data)
            self.assertEqual(result.data["corrected"], 1)
            self.assertEqual(self.rule_issues(rule), [])
        self.employee.refresh_from_db()
        self.fund.refresh_from_db()
        self.assertEqual(str(self.employee.entry_date), "2024-12-01")
        self.assertEqual(str(self.employee.exit_date), "2026-01-01")
        self.assertEqual(str(self.fund.start_date), "2024-12-01")
        self.assertEqual(str(self.fund.end_date), "2026-01-01")
