"""Institution and funder API scopes, mutations and related data."""

from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework.test import APITestCase

from expense.models import Contract
from fund.models import Fund, Fund_Institution
from infos.models import Contact, ContactInfo, ContactInfoType, ContactType, GenericNote, OrganizationInfos, OrganizationInfosType
from project.models import Institution, Participant, Project
from staff.models import Employee
from common.preferences import list_user_favorites
from common.models import favorite


class OrganizationV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="organization-reader")
        self.employee = Employee.objects.create(first_name="Ada", last_name="Reader", user=self.user)
        self.other = Employee.objects.create(first_name="Sam", last_name="Worker")
        self.institution = Institution.objects.create(short_name="UNI", name="University")
        self.funder = Fund_Institution.objects.create(short_name="AG", name="Agency")
        self.hidden_org = Institution.objects.create(short_name="SEC", name="Secret University")
        self.visible_project = Project.objects.create(name="Visible Project", status=True)
        self.hidden_project = Project.objects.create(name="Hidden Project", status=True)
        Participant.objects.create(project=self.visible_project, employee=self.employee, status="l")
        Participant.objects.create(project=self.visible_project, employee=self.other, status="p")
        self.fund = Fund.objects.create(project=self.visible_project, institution=self.institution, funder=self.funder,
                                        amount=Decimal("100.00"), expense=Decimal("-30.00"),
                                        amount_f=Decimal("80.00"), expense_f=Decimal("-20.00"))
        Fund.objects.create(project=self.hidden_project, institution=self.institution, funder=self.funder,
                            amount=Decimal("900.00"), expense=Decimal("-100.00"), amount_f=Decimal("800.00"), expense_f=Decimal("-50.00"))
        self.contract = Contract.objects.create(fund=self.fund, employee=self.other, is_active=True,
                                                start_date=timezone.localdate() - timedelta(days=10),
                                                end_date=timezone.localdate() + timedelta(days=10))
        self.client.force_login(self.user)

    def grant(self, app, codename):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def path(self, kind="institutions", pk=None):
        return f"/api/v1/organizations/{kind}/" + (f"{pk}/" if pk else "")

    def test_read_search_pagination_and_scoped_summaries(self):
        self.assertEqual(self.client.get(self.path()).status_code, 404)
        self.grant("common", "display_infos")
        GenericNote.objects.create(content_type=ContentType.objects.get_for_model(Contract), object_id=self.contract.pk,
                                   name="Visible note", note="<p>Text</p>", visibility="object", creator=self.user)
        self.assertFalse(self.client.get(self.path()).data["capabilities"]["can_add"])
        self.assertEqual(self.client.post(self.path(), {"short_name": "NEW", "name": "New"}).status_code, 403)
        page = self.client.get(self.path(), {"search": "university", "ordering": "-short_name", "limit": 1})
        self.assertEqual(page.data["count"], 2)
        self.assertIsNotNone(page.data["next"])
        self.assertIsNotNone(self.client.get(self.path(), {"search": "university", "ordering": "-short_name", "limit": 1, "offset": 1}).data["previous"])
        for kind, org in (("institutions", self.institution), ("funders", self.funder)):
            self.assertIn(org.pk, [x["id"] for x in self.client.get(self.path(kind), {"search": org.name.lower()}).data["results"]])
            self.assertIn(org.pk, [x["id"] for x in self.client.get(self.path(kind), {"search": org.short_name.lower()}).data["results"]])
            summary = self.client.get(self.path(kind, org.pk) + "summary/").data
            self.assertEqual(summary["projects"]["total"], 1)
            self.assertEqual(Decimal(summary["projects"]["total_amount"]), Decimal("100.00"))
            self.assertEqual(Decimal(summary["projects"]["available_amount"]), Decimal("70.00"))
            self.assertEqual(Decimal(summary["projects"]["available_amount_focus"]), Decimal("60.00"))
            self.assertEqual(summary["contracts"]["total"], 1)
            self.assertEqual(summary["contracts"]["current"], 1)
            self.assertEqual(summary["contracts"]["active"], 1)
            project_rows = self.client.get(self.path(kind, org.pk) + "projects/").data
            self.assertEqual([x["id"] for x in project_rows], [self.visible_project.pk])
            canonical = next(x for x in self.client.get("/api/v1/projects/").data["results"] if x["id"] == self.visible_project.pk)
            for field in ("name", "start_date", "end_date", "status", "institutions", "participants", "funds", "capabilities"):
                self.assertEqual(project_rows[0][field], canonical[field])
            self.assertEqual([x["id"] for x in self.client.get(self.path(kind, org.pk) + "contracts/").data], [self.contract.pk])
            contract_row = self.client.get(self.path(kind, org.pk) + "contracts/").data[0]
            hub_row = next(x for x in self.client.get("/api/v1/contracts/").data["results"] if x["id"] == self.contract.pk)
            for field in ("employee", "contract_type", "fund", "status", "is_active", "start_date", "end_date", "quotity", "total_amount", "notes", "capabilities", "admin_url"):
                self.assertEqual(contract_row[field], hub_row[field])
            self.assertEqual(contract_row["notes"]["visible_count"], 1)
        self.assertEqual(self.client.get(self.path(pk=999999)).status_code, 404)

    def test_project_rows_keep_organization_scope_when_another_project_is_visible(self):
        self.grant("common", "display_infos")
        other_institution = Institution.objects.create(short_name="OTHER", name="Other institution")
        other_funder = Fund_Institution.objects.create(short_name="OTHER", name="Other funder")
        other_project = Project.objects.create(name="Another visible project", status=True)
        Participant.objects.create(project=other_project, employee=self.employee, status="l")
        other_fund = Fund.objects.create(project=other_project, institution=other_institution, funder=other_funder)
        Contract.objects.create(fund=other_fund, employee=self.other)
        for kind, org in (("institutions", self.institution), ("funders", self.funder)):
            rows = self.client.get(self.path(kind, org.pk) + "projects/").data
            self.assertEqual([row["id"] for row in rows], [self.visible_project.pk])
            contracts = self.client.get(self.path(kind, org.pk) + "contracts/").data
            self.assertEqual([row["id"] for row in contracts], [self.contract.pk])

    def test_organization_capabilities_and_crud(self):
        self.grant("project", "add_institution")
        self.assertEqual(self.client.post(self.path(), {"short_name": "NEW", "name": "New"}).status_code, 404)
        self.grant("common", "display_infos")
        created = self.client.post(self.path(), {"short_name": "NEW", "name": "New"}, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        pk = created.data["id"]
        self.assertFalse(created.data["capabilities"]["can_change"])
        self.grant("project", "change_institution")
        self.assertTrue(self.client.get(self.path(pk=pk)).data["capabilities"]["can_change"])
        self.assertEqual(self.client.patch(self.path(pk=pk), {"name": "Newer"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(self.path(pk=pk)).status_code, 403)
        self.grant("project", "delete_institution")
        self.assertEqual(self.client.delete(self.path(pk=pk)).status_code, 204)
        self.assertEqual(self.client.get(self.path(pk=pk)).status_code, 404)

    def test_info_contact_and_contact_info_scoped_crud(self):
        self.grant("common", "display_infos")
        base = self.path(pk=self.institution.pk)
        org_type = OrganizationInfosType.objects.create(name="Phone", icon="Phone", type="tel")
        contact_type = ContactType.objects.create(name="Manager")
        contact_info_type = ContactInfoType.objects.create(name="Email", icon="Mail", type="mail")
        options = self.client.get(base + "options/")
        self.assertEqual(options.status_code, 200)
        self.assertEqual(options.data["organization_info_types"][0]["icon"], "Phone")
        self.assertEqual(options.data["contact_info_types"][0]["type"], "mail")
        self.assertIn(options.data["map_provider"], ("gmap", "opensm"))
        self.assertEqual(self.client.post(base + "infos/", {"info_id": org_type.pk, "value": "123"}).status_code, 403)
        self.grant("infos", "add_organizationinfos")
        self.grant("infos", "add_contact")
        self.grant("infos", "add_contactinfo")
        info = self.client.post(base + "infos/", {"info_id": org_type.pk, "value": "123"}, format="json")
        self.assertEqual(info.status_code, 201, info.data)
        self.assertEqual(info.data["info"]["icon"], "Phone")
        self.assertEqual(info.data["info"]["type"], "tel")
        self.assertEqual(self.client.get(self.path(pk=self.hidden_org.pk) + "infos/").data["items"], [])
        self.assertEqual(self.client.patch(self.path(pk=self.hidden_org.pk) + f"infos/{info.data['id']}/", {"value": "999"}).status_code, 404)
        contact = self.client.post(base + "contacts/", {"type_id": contact_type.pk, "first_name": "Kim", "last_name": "Smith"}, format="json")
        self.assertEqual(contact.status_code, 201, contact.data)
        contact_path = base + f"contacts/{contact.data['id']}/"
        email = self.client.post(contact_path + "infos/", {"info_id": contact_info_type.pk, "value": "a@example.com"}, format="json")
        self.assertEqual(email.status_code, 201, email.data)
        self.assertEqual(email.data["info"]["type"], "mail")
        self.assertEqual(self.client.get(contact_path + "infos/").data["items"][0]["id"], email.data["id"])
        self.assertEqual(self.client.get(contact_path + f"infos/{email.data['id']}/").data["value"], "a@example.com")
        self.assertEqual(self.client.get(self.path("funders", self.funder.pk) + f"contacts/{contact.data['id']}/").status_code, 404)
        self.grant("infos", "change_contactinfo")
        self.assertEqual(self.client.patch(contact_path + f"infos/{email.data['id']}/", {"value": "b@example.com"}, format="json").status_code, 200)
        self.grant("infos", "delete_contactinfo")
        self.assertEqual(self.client.delete(contact_path + f"infos/{email.data['id']}/").status_code, 204)
        self.assertFalse(ContactInfo.objects.filter(pk=email.data["id"]).exists())
        self.assertEqual(OrganizationInfos.objects.get(pk=info.data["id"]).content_type, ContentType.objects.get_for_model(Institution))
        self.assertEqual(Contact.objects.get(pk=contact.data["id"]).object_id, self.institution.pk)

    def test_funder_notes_favorites_and_referenced_delete(self):
        self.grant("common", "display_infos")
        favorite.objects.create(user=self.user, content_type=ContentType.objects.get_for_model(self.funder), object_id=self.funder.pk)
        self.assertEqual(list_user_favorites(self.user)[0]["url"], f"/organizations/funders/{self.funder.pk}")
        self.assertEqual(self.client.get(f"/api/v1/notes/funder/{self.funder.pk}/").status_code, 200)
        self.grant("fund", "delete_fund_institution")
        self.assertFalse(self.client.get(self.path("funders", self.funder.pk)).data["capabilities"]["can_delete"])
        self.assertEqual(self.client.delete(self.path("funders", self.funder.pk)).status_code, 400)
        self.assertTrue(Fund.objects.filter(pk=self.fund.pk).exists())
