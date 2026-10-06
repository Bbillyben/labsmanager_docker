"""The Contract Hub shares visibility, filtering and export scope."""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import Q
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APITestCase

from expense.models import Contract, Contract_expense, Contract_type
from fund.models import Fund, Fund_Institution
from infos.models import GenericNote
from project.models import Institution, Participant, Project
from staff.models import Employee, Employee_Superior


class ContractHubV1Tests(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.user = get_user_model().objects.create_user(username="contract-hub-reader")
        self.reader = Employee.objects.create(first_name="Reader", last_name="Leader", user=self.user)
        self.employee = Employee.objects.create(first_name="Alice", last_name="Alpha")
        self.other = Employee.objects.create(first_name="Bob", last_name="Zulu")
        self.hidden_employee = Employee.objects.create(first_name="Hector", last_name="Hidden")
        self.project = Project.objects.create(name="Atlas")
        self.hidden_project = Project.objects.create(name="Secret")
        Participant.objects.create(project=self.project, employee=self.reader, status="l")
        Participant.objects.create(project=self.project, employee=self.employee, status="p")
        Participant.objects.create(project=self.project, employee=self.other, status="p")
        self.funder = Fund_Institution.objects.create(name="Agency", short_name="AG")
        self.hidden_funder = Fund_Institution.objects.create(name="Secret agency", short_name="SECRET")
        self.institution = Institution.objects.create(name="University", short_name="UNI")
        self.hidden_institution = Institution.objects.create(name="Secret university", short_name="HIDDEN")
        self.fund = Fund.objects.create(project=self.project, funder=self.funder, institution=self.institution, ref="VISIBLE-1")
        hidden_fund = Fund.objects.create(project=self.hidden_project, funder=self.hidden_funder, institution=self.hidden_institution, ref="SECRET-1")
        self.type = Contract_type.objects.create(name="Fixed term")
        self.other_type = Contract_type.objects.create(name="Permanent")
        self.current = Contract.objects.create(employee=self.employee, fund=self.fund, contract_type=self.type,
            status="prov", is_active=False, start_date=self.today - timedelta(days=10), end_date=self.today + timedelta(days=10))
        self.future = Contract.objects.create(employee=self.other, fund=self.fund, contract_type=self.other_type,
            status="effe", is_active=True, start_date=self.today + timedelta(days=20), end_date=self.today + timedelta(days=40))
        self.hidden = Contract.objects.create(employee=self.hidden_employee, fund=hidden_fund, contract_type=self.type,
            status="prov", is_active=True, start_date=self.today, end_date=self.today + timedelta(days=1))
        self.client.force_login(self.user)

    def grant(self, app, code):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=code))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def ids(self, **params):
        response = self.client.get("/api/v1/contracts/", params)
        self.assertEqual(response.status_code, 200, response.data)
        return [item["id"] for item in response.data["results"]]

    def test_visibility_temporal_flags_and_cumulative_filters(self):
        self.assertEqual(set(self.ids()), {self.current.pk, self.future.pk})
        self.assertEqual(self.ids(active="true"), [self.future.pk])
        self.assertEqual(self.ids(active="false"), [self.current.pk])
        self.assertEqual(self.ids(ongoing="true"), [self.current.pk])
        self.assertEqual(self.ids(ongoing="false"), [self.future.pk])
        self.assertEqual(self.ids(active="true", ongoing="true"), [])
        self.assertEqual(self.ids(employee=self.current.employee_id, type=self.type.pk, cont_status="prov",
                                  project=self.project.pk, funder=self.funder.pk, institution=self.institution.pk), [self.current.pk])
        self.assertEqual(self.ids(type=self.type.pk, project=self.hidden_project.pk), [])
        with patch.object(Contract, "staleFilter", return_value=Q(pk=self.future.pk)) as stale:
            self.assertEqual(self.ids(stale="true"), [self.future.pk])
            self.assertEqual(self.ids(stale="false"), [self.current.pk])
            self.assertEqual(stale.call_count, 2)

    def test_ordering_pagination_options_and_detail_permissions(self):
        self.assertEqual(self.ids(ordering="-employee__last_name", limit=1), [self.future.pk])
        self.assertEqual(self.ids(ordering="-employee__last_name", limit=1, offset=1), [self.current.pk])
        options = self.client.get("/api/v1/contracts/filter-options/")
        self.assertEqual(options.status_code, 200, options.data)
        self.assertEqual({entry["id"] for entry in options.data["funders"]}, {self.funder.pk})
        self.assertEqual({entry["id"] for entry in options.data["institutions"]}, {self.institution.pk})
        self.assertEqual({entry["id"] for entry in options.data["contract_types"]}, {self.type.pk, self.other_type.pk})
        self.assertEqual({entry["value"] for entry in options.data["statuses"]}, {"effe", "prov"})
        detail = f"/api/v1/contracts/{self.current.pk}/"
        response = self.client.get(detail)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["capabilities"]["can_change"])
        self.assertFalse(response.data["capabilities"]["can_delete"])
        self.assertEqual(self.client.patch(detail, {"quotity": "0.750"}, format="json").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/contracts/", {}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(detail).status_code, 405)
        self.assertEqual(self.client.get(f"/api/v1/contracts/{self.hidden.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/api/v1/contracts/{self.hidden.pk}/expenses/").status_code, 404)
        self.reader.user = None
        self.reader.save()
        self.employee.user = self.user
        self.employee.save()
        Participant.objects.filter(project=self.project, employee=self.employee).update(status="l")
        self.assertFalse(self.client.get(detail).data["capabilities"]["can_change"])
        self.grant("common", "self_edit")
        self.assertTrue(self.client.get(detail).data["capabilities"]["can_change"])
        changed = self.client.patch(detail, {"quotity": "0.750"}, format="json")
        self.assertEqual(changed.status_code, 200, changed.data)
        self.current.refresh_from_db()
        self.assertEqual(self.current.quotity, Decimal("0.750"))

    def test_export_uses_filtered_unpaginated_queryset_and_annotated_total(self):
        from fund.models import Cost_Type
        from expense.resources import ContractResource
        cost_type = Cost_Type.objects.create(name="HR", short_name="HR", is_hr=True)
        Contract_expense.objects.create(contract=self.current, fund_item=self.fund, type=cost_type,
                                        date=self.today, amount=Decimal("25.00"))
        response = self.client.get("/api/v1/contracts/", {"ordering": "-employee__last_name", "limit": 1})
        self.assertEqual(response.data["results"][0]["total_amount"], "0.00")
        def unannotated_total(_contract):
            raise AssertionError("Hub export must use the annotated total")

        with patch.object(Contract, "total_amount", property(unannotated_total)):
            export = self.client.get("/api/v1/contracts/export/", {"format": "csv", "ordering": "-employee__last_name", "limit": 1, "offset": 1})
        self.assertEqual(export.status_code, 200, getattr(export, "data", None))
        content = export.content.decode()
        self.assertIn("Alice", content)
        self.assertIn("Bob", content)
        self.assertIn("25.00", content)
        self.assertNotIn("Secret", content)
        self.assertNotIn("Hector", content)
        filtered = self.client.get("/api/v1/contracts/export/", {"format": "csv", "active": "false", "limit": 1, "offset": 1})
        self.assertIn("Alice", filtered.content.decode())
        self.assertNotIn("Bob", filtered.content.decode())
        self.assertTrue(self.client.get("/api/v1/contracts/export/", {"format": "xlsx"})["Content-Type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
        self.assertEqual(self.client.get("/api/v1/contracts/export/", {"format": "pdf"}).status_code, 400)
        self.assertIn("25.00", ContractResource().export(queryset=Contract.objects.filter(pk=self.current.pk)).csv)

    def test_expenses_reuse_contract_context_and_remain_permission_checked(self):
        from fund.models import Cost_Type
        cost_type = Cost_Type.objects.create(name="HR", short_name="HR", is_hr=True)
        url = f"/api/v1/contracts/{self.current.pk}/expenses/"
        self.assertEqual(self.client.get(url).status_code, 200)
        reader = get_user_model().objects.create_user(username="contract-hub-view-only")
        reader.user_permissions.add(Permission.objects.get(content_type__app_label="expense", codename="view_contract"))
        self.client.force_login(reader)
        denied = self.client.post(url, {"date": self.today.isoformat(), "type_id": cost_type.pk, "amount": "10.00"}, format="json")
        self.assertEqual(denied.status_code, 403, denied.data)
        self.client.force_login(self.user)
        self.grant("expense", "add_contract_expense")
        created = self.client.post(url, {"date": self.today.isoformat(), "type_id": cost_type.pk, "amount": "10.00"}, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(Contract_expense.objects.get(pk=created.data["id"]).contract_id, self.current.pk)
        self.assertEqual(self.client.get(url).data["count"], 1)

    def test_employee_contract_scope_is_included_for_subordinate_and_self(self):
        subordinate = Employee.objects.create(first_name="Sam", last_name="Subordinate")
        Employee_Superior.objects.create(employee=subordinate, superior=self.reader)
        subordinate_contract = Contract.objects.create(employee=subordinate, fund=self.hidden.fund, status="prov")
        self_contract = Contract.objects.create(employee=self.reader, fund=self.hidden.fund, status="prov")

        for employee, contract in ((subordinate, subordinate_contract), (self.reader, self_contract)):
            context = self.client.get(f"/api/v1/employees/{employee.pk}/contracts/")
            self.assertEqual(context.status_code, 200, context.data)
            self.assertIn(contract.pk, {item["id"] for item in context.data})
            self.assertIn(contract.pk, self.ids())
            detail = self.client.get(f"/api/v1/contracts/{contract.pk}/")
            self.assertEqual(detail.status_code, 200, detail.data)
            self.assertFalse(detail.data["capabilities"]["can_change"])

        self.assertNotIn(self.hidden.pk, self.ids())
        export = self.client.get("/api/v1/contracts/export/", {"format": "csv"})
        self.assertIn("SUBORDINATE", export.content.decode())
        self.assertNotIn("Hector", export.content.decode())

    def test_project_contract_scope_is_included_for_leader_coleader_and_reader(self):
        participant = Employee.objects.create(first_name="Nina", last_name="Participant")
        outsider = Employee.objects.create(first_name="Ona", last_name="Outsider")
        Participant.objects.create(project=self.project, employee=participant, status="p")
        included = Contract.objects.create(employee=participant, fund=self.fund, status="prov")
        excluded = Contract.objects.create(employee=outsider, fund=self.fund, status="prov")
        collection = f"/api/v1/projects/{self.project.pk}/contracts/"

        for role in ("l", "cl"):
            relation = Participant.objects.get(project=self.project, employee=self.reader)
            relation.status = role
            relation.save(update_fields=["status"])
            context = self.client.get(collection)
            self.assertEqual(context.status_code, 200, context.data)
            context_ids = {item["id"] for item in context.data["items"]}
            self.assertIn(included.pk, context_ids)
            self.assertNotIn(excluded.pk, context_ids)
            self.assertTrue(context_ids <= set(self.ids()))
            self.assertNotIn(excluded.pk, self.ids())

        relation.status = "p"
        relation.save(update_fields=["status"])
        self.grant("fund", "view_fund")
        context = self.client.get(collection)
        self.assertEqual(context.status_code, 200, context.data)
        context_ids = {item["id"] for item in context.data["items"]}
        self.assertIn(included.pk, context_ids)
        self.assertTrue(context_ids <= set(self.ids()))
        self.assertFalse(self.client.get(f"/api/v1/contracts/{included.pk}/").data["capabilities"]["can_change"])
        self.assertIn("Nina", self.client.get("/api/v1/contracts/export/", {"format": "csv"}).content.decode())
        self.assertNotIn("Ona", self.client.get("/api/v1/contracts/export/", {"format": "csv"}).content.decode())

    def test_global_view_and_superuser_visibility_remain_available(self):
        self.grant("staff", "view_employee")
        context = self.client.get(f"/api/v1/employees/{self.hidden_employee.pk}/contracts/")
        self.assertIn(self.hidden.pk, {item["id"] for item in context.data})
        self.assertIn(self.hidden.pk, self.ids())
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save(update_fields=["is_superuser", "is_staff"])
        self.client.force_login(self.user)
        self.assertEqual(set(self.ids()), {self.current.pk, self.future.pk, self.hidden.pk})

    def test_list_batches_only_visible_contract_note_counts(self):
        content_type = ContentType.objects.get_for_model(Contract)
        other_author = get_user_model().objects.create_user(username="other-contract-note-author")
        for name, visibility, creator in (
            ("Public", "object", self.user),
            ("Own private", "creator", self.user),
            ("Other private", "creator", other_author),
        ):
            GenericNote.objects.create(content_type=content_type, object_id=self.current.pk,
                                       name=name, note="<p>Text</p>", visibility=visibility, creator=creator)
        GenericNote.objects.create(content_type=content_type, object_id=self.hidden.pk,
                                   name="Hidden", note="<p>Text</p>", visibility="object", creator=self.user)

        with CaptureQueriesContext(connection) as captured:
            response = self.client.get("/api/v1/contracts/")
        self.assertEqual(response.status_code, 200, response.data)
        notes = {item["id"]: item["notes"] for item in response.data["results"]}
        self.assertEqual(notes, {
            self.current.pk: {"visible_count": 2, "can_add": False},
            self.future.pk: {"visible_count": 0, "can_add": False},
        })
        self.assertEqual(len([query for query in captured if '"infos_genericnote"' in query["sql"]]), 1)
        self.grant("infos", "change_genericnote")
        admin_rows = {item["id"]: item for item in self.client.get("/api/v1/contracts/").data["results"]}
        self.assertEqual(admin_rows[self.current.pk]["notes"], {"visible_count": 3, "can_add": True})
        self.assertFalse(admin_rows[self.current.pk]["capabilities"]["can_change"])

    def test_zero_notes_exposes_add_only_with_existing_contract_permission(self):
        own_contract = Contract.objects.create(employee=self.reader, fund=self.fund, status="prov")
        before = {item["id"]: item for item in self.client.get("/api/v1/contracts/").data["results"]}
        self.assertFalse(before[own_contract.pk]["notes"]["can_add"])
        self.grant("common", "self_edit")
        rows = {item["id"]: item for item in self.client.get("/api/v1/contracts/").data["results"]}
        self.assertEqual(rows[own_contract.pk]["notes"], {"visible_count": 0, "can_add": True})
        self.assertTrue(rows[own_contract.pk]["capabilities"]["can_change"])
        self.assertEqual(rows[self.current.pk]["notes"], {"visible_count": 0, "can_add": False})
