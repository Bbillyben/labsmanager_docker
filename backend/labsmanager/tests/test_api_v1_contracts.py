"""Contract v1 scopes and context-specific mutation authority."""

from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase

from expense.models import Contract, Contract_expense
from project.models import Participant
from staff.models import Employee

class ContractV1Tests(APITestCase):
    def setUp(self):
        from .test_api_v1_funding import ProjectFundingV1Tests
        ProjectFundingV1Tests.setUp(self)
        self.participant = Employee.objects.create(first_name="Ada", last_name="Participant")
        self.outsider = Employee.objects.create(first_name="Ona", last_name="Outsider")
        Participant.objects.create(project=self.project, employee=self.participant, status="p")
        self.allowed = Contract.objects.create(employee=self.participant, fund=self.fund, quotity=Decimal("0.500"), status="prov")
        self.outside_employee = Contract.objects.create(employee=self.outsider, fund=self.fund)
        self.outside_project = Contract.objects.create(employee=self.participant, fund=self.hidden_fund)
        self.type.is_hr = True
        self.type.save()

    def grant(self, codename, app):
        from .test_api_v1_funding import ProjectFundingV1Tests
        ProjectFundingV1Tests.grant(self, codename, app)

    def collection_url(self, project=None):
        return reverse("api_v1:project-contracts", kwargs={"project_id": (project or self.project).pk})

    def detail_url(self, contract=None, project=None):
        return reverse("api_v1:project-contract-detail", kwargs={"project_id": (project or self.project).pk, "contract_id": (contract or self.allowed).pk})

    def payload(self, employee=None, fund=None):
        return {"employee_id": (employee or self.participant).pk, "fund_id": (fund or self.fund).pk,
                "status": "prov", "start_date": "2026-01-01", "end_date": "2026-12-31", "quotity": "0.500"}

    def test_project_collection_filters_project_and_participants(self):
        response = self.client.get(self.collection_url())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([item["id"] for item in response.data["items"]], [self.allowed.pk])
        self.assertTrue(response.data["capabilities"]["can_add"])
        self.assertEqual(self.client.get(self.detail_url(self.outside_employee)).status_code, 404)
        self.assertEqual(self.client.get(self.detail_url(self.outside_project)).status_code, 404)
        self.assertEqual(self.client.get(self.collection_url(self.hidden)).status_code, 404)

    def test_project_leader_manages_participant_without_hr_permission(self):
        self.assertFalse(self.user.has_perm("staff.change_employee", self.participant))
        options = self.client.get(reverse("api_v1:project-contract-options", kwargs={"project_id": self.project.pk}))
        self.assertEqual({item["id"] for item in options.data["employees"]}, {self.employee.pk, self.participant.pk})
        self.assertEqual([item["id"] for item in options.data["funds"]], [self.fund.pk])
        created = self.client.post(self.collection_url(), self.payload(), format="json")
        self.assertEqual(created.status_code, 201, created.data)
        contract = Contract.objects.get(pk=created.data["id"])
        changed = self.client.patch(self.detail_url(contract), {"quotity": "0.750"}, format="json")
        self.assertEqual(changed.status_code, 200, changed.data)
        contract.refresh_from_db()
        self.assertEqual(contract.quotity, Decimal("0.750"))
        self.assertEqual(self.client.delete(self.detail_url(contract)).status_code, 204)
        self.assertFalse(Contract.objects.filter(pk=contract.pk).exists())

    def test_project_rejects_foreign_fund_and_nonparticipant(self):
        self.assertEqual(self.client.post(self.collection_url(), self.payload(self.outsider), format="json").status_code, 400)
        self.assertEqual(self.client.post(self.collection_url(), self.payload(fund=self.hidden_fund), format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.detail_url(), {"employee_id": self.outsider.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.detail_url(), {"fund_id": self.hidden_fund.pk}, format="json").status_code, 400)

    def test_project_contract_expenses_use_selected_contract_and_fund(self):
        url = reverse("api_v1:project-contract-expenses", kwargs={"pk": self.project.pk, "contract_id": self.allowed.pk})
        self.assertEqual(self.client.get(url).status_code, 200)
        created = self.client.post(url, {"date": date(2026, 2, 1).isoformat(), "type_id": self.type.pk, "amount": "25.00"}, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(Contract_expense.objects.get(pk=created.data["id"]).contract_id, self.allowed.pk)
        self.assertEqual(Contract_expense.objects.get(pk=created.data["id"]).fund_item_id, self.fund.pk)
        incompatible = self.client.post(url, {"date": "2026-02-02", "type_id": self.type.pk, "amount": "10.00",
                                              "contract_id": self.outside_project.pk}, format="json")
        self.assertEqual(incompatible.status_code, 400, incompatible.data)
        self.assertEqual(self.client.get(reverse("api_v1:project-contract-expenses", kwargs={"pk": self.project.pk, "contract_id": self.outside_employee.pk})).status_code, 404)

    def test_employee_context_does_not_inherit_project_contract_mutations(self):
        self.grant("view_employee", "staff")
        url = reverse("api_v1:employee-contracts", kwargs={"pk": self.participant.pk})
        detail = reverse("api_v1:employee-contract-detail", kwargs={"pk": self.participant.pk, "contract_pk": self.allowed.pk})
        caps = reverse("api_v1:employee-contract-capabilities", kwargs={"employee_id": self.participant.pk})
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertFalse(self.client.get(caps).data["can_add"])
        self.assertFalse(self.client.get(detail).data["capabilities"]["can_change"])
        self.assertEqual(self.client.post(url, self.payload(), format="json").status_code, 403)
        self.assertEqual(self.client.patch(detail, {"quotity": "0.750"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(detail).status_code, 403)

    def test_project_reader_can_view_but_cannot_mutate(self):
        self.participation.status = "p"
        self.participation.save()
        self.grant("view_fund", "fund")
        collection = self.collection_url()
        detail = self.detail_url()
        response = self.client.get(collection)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([item["id"] for item in response.data["items"]], [self.allowed.pk])
        self.assertFalse(any(response.data["capabilities"].values()))
        self.assertFalse(any(self.client.get(detail).data["capabilities"].values()))
        self.assertEqual(self.client.post(collection, self.payload(), format="json").status_code, 403)
        self.assertEqual(self.client.patch(detail, {"quotity": "0.750"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(detail).status_code, 403)
        self.assertEqual(self.client.get(self.collection_url(self.hidden)).status_code, 404)

    def test_employee_global_contract_permissions_are_respected_in_employee_context(self):
        self.grant("view_employee", "staff")
        self.grant("change_employee", "staff")
        self.grant("add_contract", "expense")
        self.grant("change_contract", "expense")
        self.grant("delete_contract", "expense")
        self.grant("change_fund", "fund")
        collection = reverse("api_v1:employee-contracts", kwargs={"pk": self.participant.pk})
        detail = self.detail_url()
        employee_detail = reverse("api_v1:employee-contract-detail", kwargs={"pk": self.participant.pk, "contract_pk": self.allowed.pk})
        caps = reverse("api_v1:employee-contract-capabilities", kwargs={"employee_id": self.participant.pk})
        self.assertTrue(self.client.get(caps).data["can_add"])
        self.assertTrue(all(self.client.get(employee_detail).data["capabilities"].values()))
        created = self.client.post(collection, self.payload(), format="json")
        self.assertEqual(created.status_code, 201, created.data)
        changed = self.client.patch(employee_detail, {"quotity": "0.750"}, format="json")
        self.assertEqual(changed.status_code, 200, changed.data)
        self.assertEqual(self.client.delete(employee_detail).status_code, 204)
        self.assertEqual(self.client.get(detail).status_code, 404)

    def test_employee_end_date_offer_requires_a_dated_latest_contract_and_employee_change(self):
        self.grant("change_employee", "staff")
        self.participant.exit_date = date(2026, 12, 31)
        self.participant.save()
        detail = self.detail_url()
        empty = self.client.patch(detail, {"end_date": None}, format="json")
        self.assertIsNone(empty.data["employee_end_date_sync"])
        equal = self.client.patch(detail, {"end_date": "2026-12-31"}, format="json")
        self.assertIsNone(equal.data["employee_end_date_sync"])
        later = Contract.objects.create(employee=self.participant, fund=self.fund, status="prov", end_date=date(2028, 1, 1))
        blocked = self.client.patch(detail, {"end_date": "2027-06-30"}, format="json")
        self.assertIsNone(blocked.data["employee_end_date_sync"])
        later.delete()
        extend = self.client.patch(detail, {"end_date": "2027-06-30"}, format="json")
        self.assertEqual(extend.data["employee_end_date_sync"], {
            "employee_id": self.participant.pk, "current_end_date": "2026-12-31",
            "proposed_end_date": "2027-06-30", "can_update": True,
        })
        self.participant.exit_date = date(2028, 12, 31)
        self.participant.save()
        shorten = self.client.patch(detail, {"end_date": "2027-07-31"}, format="json")
        self.assertEqual(shorten.data["employee_end_date_sync"]["current_end_date"], "2028-12-31")
        self.assertEqual(shorten.data["employee_end_date_sync"]["proposed_end_date"], "2027-07-31")
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.exit_date, date(2028, 12, 31))

    def test_employee_end_date_sync_requires_employee_permission_and_rechecks_offer(self):
        detail = self.detail_url()
        sync = reverse("api_v1:project-contract-sync-employee-end-date", kwargs={"project_id": self.project.pk, "contract_id": self.allowed.pk})
        saved = self.client.patch(detail, {"end_date": "2027-06-30"}, format="json")
        self.assertEqual(saved.status_code, 200, saved.data)
        self.assertIsNone(saved.data["employee_end_date_sync"])
        self.assertEqual(self.client.post(sync, {}, format="json").status_code, 403)
        self.grant("change_employee", "staff")
        other = Contract.objects.create(employee=self.participant, fund=self.fund, status="prov", end_date=date(2028, 1, 1))
        self.assertEqual(self.client.post(sync, {}, format="json").status_code, 400)
        other.delete()
        confirmed = self.client.post(sync, {}, format="json")
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.exit_date, date(2027, 6, 30))
        self.assertEqual(self.client.post(sync, {}, format="json").status_code, 400)

    def test_employee_context_create_offers_and_syncs_the_same_employee(self):
        self.grant("view_employee", "staff")
        self.grant("change_employee", "staff")
        self.grant("add_contract", "expense")
        self.grant("change_fund", "fund")
        collection = reverse("api_v1:employee-contracts", kwargs={"pk": self.participant.pk})
        created = self.client.post(collection, self.payload(), format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["employee_end_date_sync"]["proposed_end_date"], "2026-12-31")
        sync = reverse("api_v1:employee-contract-sync-employee-end-date", kwargs={"pk": self.participant.pk, "contract_pk": created.data["id"]})
        self.assertEqual(self.client.post(sync, {}, format="json").status_code, 200)
        self.participant.refresh_from_db()
        self.assertEqual(self.participant.exit_date, date(2026, 12, 31))
