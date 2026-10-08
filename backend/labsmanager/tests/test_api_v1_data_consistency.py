"""Focused coverage for the first read-only consistency rule."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from expense.models import Contract
from data_consistency.models import DataConsistencyException
from fund.models import Fund, Fund_Institution
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
