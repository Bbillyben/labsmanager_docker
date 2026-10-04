from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from common.models import favorite, subscription
from common.preferences import list_user_favorites
from fund.models import Cost_Type, Fund, Fund_Institution, Fund_Item
from project.models import Institution, Participant, Project
from project.views import get_project_fund_overviewReport_bytType
from staff.models import Employee, Team


class ObjectPreferenceV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="preference-reader")
        self.employee = Employee.objects.create(first_name="Ada", last_name="Reader", user=self.user)
        self.other = Employee.objects.create(first_name="Hidden", last_name="Person")
        self.project = Project.objects.create(name="Alpha")
        self.hidden_project = Project.objects.create(name="Secret")
        Participant.objects.create(project=self.project, employee=self.employee, status="p")
        self.team = Team.objects.create(name="Readers", leader=self.employee)
        self.hidden_team = Team.objects.create(name="Hidden Team", leader=self.other)
        self.institution = Institution.objects.create(short_name="UNI", name="University")
        self.funder = Fund_Institution.objects.create(short_name="ANR", name="Agency")
        self.client.force_login(self.user)

    def url(self, kind, obj):
        return f"/api/v1/preferences/{kind}/{obj.pk}/"

    def test_status_and_idempotent_set_for_both_models(self):
        url = self.url("project", self.project)
        self.assertEqual(self.client.get(url).data, {"favorite": False, "subscription": False})
        for _ in range(2):
            response = self.client.put(url, {"favorite": True, "subscription": True}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data, {"favorite": True, "subscription": True})
        self.assertEqual(favorite.objects.filter(user=self.user).count(), 1)
        self.assertEqual(subscription.objects.filter(user=self.user).count(), 1)
        self.assertEqual(self.client.put(url, {"favorite": False, "subscription": False}, format="json").data, {"favorite": False, "subscription": False})
        self.assertFalse(favorite.objects.filter(user=self.user).exists())
        self.assertFalse(subscription.objects.filter(user=self.user).exists())
        self.assertEqual(self.client.put(url, {"favorite": "true"}, format="json").status_code, 400)
        self.assertEqual(self.client.get("/api/v1/preferences/unknown/1/").status_code, 404)

    def test_unique_constraints_and_legacy_toggle_share_relations(self):
        url = self.url("employee", self.employee)
        self.assertEqual(self.client.put(url, {"favorite": True}, format="json").status_code, 200)
        content_type = ContentType.objects.get_for_model(self.employee)
        with self.assertRaises(IntegrityError), transaction.atomic():
            favorite.objects.create(user=self.user, content_type=content_type, object_id=self.employee.pk)
        legacy = {"type": "staff.employee", "pk": str(self.employee.pk)}
        self.assertEqual(self.client.post("/common/fav-toggle/", legacy).status_code, 200)
        self.assertFalse(favorite.objects.filter(user=self.user).exists())
        self.assertEqual(self.client.post("/common/sub-toggle/", legacy).status_code, 200)
        self.assertTrue(self.client.get(url).data["subscription"])
        with self.assertRaises(IntegrityError), transaction.atomic():
            subscription.objects.create(user=self.user, content_type=content_type, object_id=self.employee.pk)

    def test_hidden_objects_are_rejected_and_old_relations_retained(self):
        self.assertEqual(self.client.get(self.url("project", self.hidden_project)).status_code, 404)
        self.assertEqual(self.client.put(self.url("team", self.hidden_team), {"favorite": True}, format="json").status_code, 404)
        self.assertEqual(self.client.get(self.url("institution", self.institution)).status_code, 404)
        favorite.objects.create(user=self.user, content_type=ContentType.objects.get_for_model(Project), object_id=self.hidden_project.pk)
        favorite.objects.create(user=self.user, content_type=ContentType.objects.get_for_model(Team), object_id=self.hidden_team.pk)
        response = self.client.get("/api/v1/favorites/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])
        self.assertEqual(favorite.objects.filter(user=self.user).count(), 2)
        self.assertNotIn("Secret", self.client.get("/api/favorite/current_user/").content.decode())
        self.assertEqual(len(self.client.get("/api/favorite/").data), 0)

    def test_favorite_disappears_when_project_visibility_is_lost(self):
        url = self.url("project", self.project)
        self.assertEqual(self.client.put(url, {"favorite": True}, format="json").status_code, 200)
        self.assertEqual(len(self.client.get("/api/v1/favorites/").data), 1)
        Participant.objects.filter(project=self.project, employee=self.employee).delete()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/favorites/").data, [])
        self.assertEqual(favorite.objects.filter(user=self.user).count(), 1)

    def test_subscription_navigation_reuses_object_visibility(self):
        subscription.objects.create(user=self.user, content_type=ContentType.objects.get_for_model(Project), object_id=self.project.pk)
        subscription.objects.create(user=self.user, content_type=ContentType.objects.get_for_model(Project), object_id=self.hidden_project.pk)
        response = self.client.get("/api/v1/subscriptions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([(row["type"], row["id"]) for row in response.data], [("project", self.project.pk)])

    def test_navigation_groups_sorts_and_links_react_and_legacy(self):
        self.user.user_permissions.add(Permission.objects.get(codename="display_infos", content_type__app_label="common"))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)
        second = Project.objects.create(name="Beta")
        Participant.objects.create(project=second, employee=self.employee, status="p")
        for obj in (second, self.project, self.employee, self.team, self.institution, self.funder):
            favorite.objects.create(user=self.user, content_type=ContentType.objects.get_for_model(obj), object_id=obj.pk)
        data = self.client.get("/api/v1/favorites/").data
        self.assertEqual([(item["group"], item["label"]) for item in data], [
            ("projects", "Alpha"), ("projects", "Beta"), ("employees", str(self.employee)),
            ("teams", "Readers"), ("institutions", "ANR"), ("institutions", "UNI"),
        ])
        self.assertEqual([item["url"] for item in data[:4]], [
            f"/projects/{self.project.pk}", f"/projects/{second.pk}",
            f"/employees/{self.employee.pk}", f"/teams/{self.team.pk}",
        ])
        self.assertFalse(data[-1]["legacy"])
        self.assertEqual(data[-2]["url"], f"/organizations/funders/{self.funder.pk}")
        self.assertEqual(data[-1]["url"], f"/organizations/institutions/{self.institution.pk}")
        legacy_rows = list_user_favorites(self.user)
        self.assertIn(f"/fund/fund_institution/{self.funder.pk}", legacy_rows[-2]["legacy_url"])
        self.assertIn(f"/project/institution/{self.institution.pk}", legacy_rows[-1]["legacy_url"])
        self.assertContains(self.client.get("/common/nav/"), "Alpha")

    def test_mail_financial_overview_uses_supplied_fund_scope(self):
        kind = Cost_Type.objects.create(short_name="EQ", name="Equipment")
        first = Fund.objects.create(project=self.project, funder=self.funder, institution=self.institution,
                                    start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        second = Fund.objects.create(project=self.project, funder=self.funder, institution=self.institution,
                                     start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        Fund_Item.objects.create(fund=first, type=kind, amount=Decimal("100.00"))
        Fund_Item.objects.create(fund=second, type=kind, amount=Decimal("900.00"))
        all_rows = list(get_project_fund_overviewReport_bytType(self.project.pk))
        visible_rows = list(get_project_fund_overviewReport_bytType(
            self.project.pk, Fund.objects.filter(pk=first.pk)
        ))
        self.assertEqual(all_rows[0]["total_amount"], Decimal("1000.00"))
        self.assertEqual(visible_rows[0]["total_amount"], Decimal("100.00"))
