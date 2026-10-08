from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework.test import APITestCase

from expense.models import Expense, Expense_point
from fund.models import Cost_Type, Fund, Fund_Institution, Fund_Item
from project.models import Institution, Participant, Project
from settings.models import LMProjectSetting
from staff.models import Employee


class ProjectFundingV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="funding-leader", password="test")
        self.employee = Employee.objects.create(first_name="A", last_name="Leader", user=self.user)
        self.project = Project.objects.create(name="Atlas funding", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        self.hidden = Project.objects.create(name="Hidden funding")
        self.participation = Participant.objects.create(project=self.project, employee=self.employee, status="l")
        self.funder = Fund_Institution.objects.create(short_name="ANR", name="Agence")
        self.institution = Institution.objects.create(short_name="ULF", name="Université")
        self.type = Cost_Type.objects.create(short_name="HR", name="Human resources")
        self.other_type = Cost_Type.objects.create(short_name="EQ", name="Equipment")
        self.fund = Fund.objects.create(project=self.project, funder=self.funder, institution=self.institution,
                                        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), ref="A-1")
        self.hidden_fund = Fund.objects.create(project=self.hidden, funder=self.funder, institution=self.institution,
                                               start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        self.item = Fund_Item.objects.create(fund=self.fund, type=self.type, amount=Decimal("100.00"))
        self.point = Expense_point.objects.create(fund=self.fund, type=self.type, amount=Decimal("-30.00"),
                                                   entry_date=date(2026, 2, 1), value_date=date(2026, 2, 1))
        self.client.force_login(self.user)

    def grant(self, codename, app):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def collection(self, project=None):
        return reverse("api_v1:project-funding", kwargs={"pk": (project or self.project).pk})

    def fund_url(self, fund=None, project=None):
        return reverse("api_v1:project-funding-fund", kwargs={"pk": (project or self.project).pk, "fund_id": (fund or self.fund).pk})

    def child_url(self, kind, child=None, fund=None):
        kwargs = {"pk": self.project.pk, "fund_id": (fund or self.fund).pk}
        if child:
            kwargs["item_id"] = child.pk
        return reverse(f"api_v1:project-funding-{kind if child else kind + 's'}", kwargs=kwargs)

    def test_scoped_overview_and_detail_use_signed_cached_values(self):
        response = self.client.get(self.collection())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["funds"]), 1)
        self.assertEqual(data["overview"]["rows"][0]["cells"][str(self.fund.pk)],
                         {"amount": "100.00", "expense": "-30.00", "available": "70.00"})
        self.assertEqual(data["overview"]["grand_total"]["available"], "70.00")
        detail = self.client.get(self.fund_url()).json()
        self.assertEqual(detail["total"], {"amount": "100.00", "expense": "-30.00", "available": "70.00"})
        self.assertEqual(detail["expense_points"]["items"][0]["amount"], "-30.00")
        self.assertEqual(self.client.get(self.collection(self.hidden)).status_code, 404)
        self.assertEqual(self.client.get(self.fund_url(self.hidden_fund)).status_code, 404)

    def test_fund_create_change_and_project_end_confirmation(self):
        url = self.collection()
        payload = {"funder_id": self.funder.pk, "institution_id": self.institution.pk, "ref": "B-2"}
        created = self.client.post(url, payload, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        new = Fund.objects.get(pk=created.data["id"])
        self.assertEqual(new.start_date, self.project.start_date)
        self.assertEqual(new.end_date, self.project.end_date)
        edit = self.fund_url(new)
        self.assertEqual(self.client.patch(edit, {"end_date": "2027-02-01"}, format="json").status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.end_date, date(2026, 12, 31))
        self.assertEqual(self.client.patch(edit, {"end_date": "2027-03-01", "update_project_end": True}, format="json").status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.end_date, date(2027, 3, 1))
        self.assertEqual(self.client.patch(edit, {"institution_id": self.institution.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(edit).status_code, 403)
        self.grant("delete_fund", "fund")
        self.assertEqual(self.client.delete(edit).status_code, 204)

    def test_fund_patch_accepts_open_start_with_bounded_end(self):
        response = self.client.patch(self.fund_url(), {"start_date": None}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.fund.refresh_from_db()
        self.assertIsNone(self.fund.start_date)
        self.assertEqual(self.fund.end_date, date(2026, 12, 31))

    def test_items_recalculate_and_enforce_uniqueness(self):
        url = self.child_url("item")
        response = self.client.post(url, {"type_id": self.other_type.pk, "amount": "50.00"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        item = Fund_Item.objects.get(pk=response.data["id"])
        self.fund.refresh_from_db()
        self.assertEqual(self.fund.amount, Decimal("150.00"))
        self.assertEqual(self.client.post(url, {"type_id": self.other_type.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.child_url("item", item), {"amount": "75.00"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(self.child_url("item", item)).status_code, 403)
        self.grant("delete_fund_item", "fund")
        self.assertEqual(self.client.delete(self.child_url("item", item)).status_code, 204)
        self.fund.refresh_from_db()
        self.assertEqual(self.fund.amount, Decimal("100.00"))
        self.assertEqual(self.client.delete(self.child_url("item", self.item)).status_code, 400)
        self.assertTrue(Fund_Item.objects.filter(pk=self.item.pk).exists())

    def test_expense_point_modes_and_delete_recalculation(self):
        url = self.child_url("expense-point")
        detail = self.child_url("expense-point", self.point)
        self.assertEqual(self.client.get(self.fund_url()).json()["expense_points"]["capabilities"]["expense_mode"], "s")
        self.assertEqual(self.client.patch(detail, {"amount": "40.00"}, format="json").status_code, 200)
        self.point.refresh_from_db()
        self.assertEqual(self.point.amount, Decimal("-40.00"))
        self.assertEqual(self.client.post(url, {"type_id": self.type.pk, "amount": "10.00", "entry_date": "2026-02-01", "value_date": "2026-02-01"}, format="json").status_code, 400)
        self.grant("delete_expense_point", "expense")
        self.assertEqual(self.client.delete(detail).status_code, 204)
        self.fund.refresh_from_db()
        self.item.refresh_from_db()
        self.assertEqual(self.fund.expense, Decimal("0.00"))
        self.assertEqual(self.item.expense, Decimal("0.00"))
        LMProjectSetting.set_setting("EXPENSE_CALCULATION", "e", change_user=None, project=self.project)
        capabilities = self.client.get(self.fund_url()).json()["expense_points"]["capabilities"]
        self.assertFalse(capabilities["can_add"] or capabilities["can_change"] or capabilities["can_delete"])
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 403)
        LMProjectSetting.set_setting("EXPENSE_CALCULATION", "h", change_user=None, project=self.project)
        self.assertTrue(self.client.get(self.fund_url()).json()["expense_points"]["capabilities"]["can_add"])

    def test_readonly_capabilities_and_mutation_denial(self):
        self.participation.status = "p"
        self.participation.save()
        self.grant("view_fund", "fund")
        data = self.client.get(self.collection()).json()
        self.assertFalse(data["capabilities"]["can_add"])
        detail = self.client.get(self.fund_url()).json()
        self.assertFalse(detail["fund"]["capabilities"]["can_change"])
        self.assertFalse(detail["items"]["capabilities"]["can_add"])
        self.assertFalse(detail["expense_points"]["capabilities"]["can_add"])
        self.assertEqual(self.client.post(self.collection(), {}, format="json").status_code, 403)
        self.assertEqual(self.client.patch(self.fund_url(), {"ref": "no"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.child_url("expense-point", self.point)).status_code, 403)

    def test_populated_fund_delete_and_cross_project_writes(self):
        self.grant("delete_fund", "fund")
        LMProjectSetting.set_setting("EXPENSE_CALCULATION", "h", change_user=None, project=self.project)
        Expense.objects.create(fund_item=self.fund, type=self.type, amount=Decimal("10.00"), date=date(2026, 3, 1))
        self.assertEqual(self.client.patch(self.fund_url(self.hidden_fund), {"ref": "leak"}, format="json").status_code, 404)
        self.assertEqual(self.client.post(self.child_url("item", fund=self.hidden_fund),
                                          {"type_id": self.other_type.pk, "amount": "50"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(self.fund_url()).status_code, 204)
        self.assertFalse(Fund.objects.filter(pk=self.fund.pk).exists())
        self.assertFalse(Fund_Item.objects.filter(pk=self.item.pk).exists())
        self.assertFalse(Expense_point.objects.filter(pk=self.point.pk).exists())
        self.assertFalse(Expense.objects.filter(fund_item_id=self.fund.pk).exists())

    def test_hybrid_create_and_expense_mode_rejects_global_override(self):
        LMProjectSetting.set_setting("EXPENSE_CALCULATION", "h", change_user=None, project=self.project)
        payload = {"type_id": self.other_type.pk, "amount": "25.00", "entry_date": "2026-03-01", "value_date": "2026-03-01"}
        created = self.client.post(self.child_url("expense-point"), payload, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        point = Expense_point.objects.get(pk=created.data["id"])
        self.assertEqual(point.amount, Decimal("-25.00"))
        self.fund.refresh_from_db()
        self.assertEqual(self.fund.expense, Decimal("-55.00"))
        self.grant("delete_expense_point", "expense")
        LMProjectSetting.set_setting("EXPENSE_CALCULATION", "e", change_user=None, project=self.project)
        caps = self.client.get(self.fund_url()).json()["expense_points"]["capabilities"]
        self.assertEqual(caps, {"expense_mode": "e", "can_add": False, "can_change": False, "can_delete": False})
        self.assertEqual(self.client.patch(self.child_url("expense-point", point), {"amount": "40"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.child_url("expense-point", point)).status_code, 403)

    def test_global_view_fund_can_open_empty_visible_project(self):
        self.participation.status = "p"
        self.participation.save()
        self.grant("view_fund", "fund")
        empty = Project.objects.create(name="Empty funding")
        Participant.objects.create(project=empty, employee=self.employee, status="p")
        response = self.client.get(self.collection(empty))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["funds"], [])

    def test_project_change_alone_does_not_expose_fund_domain(self):
        self.participation.status = "p"
        self.participation.save()
        self.grant("change_project", "project")
        overview = self.client.get(reverse("api_v1:project-detail", kwargs={"pk": self.project.pk})).json()
        self.assertFalse(overview["funding_visible"])
        self.assertEqual(self.client.get(self.collection()).status_code, 403)
