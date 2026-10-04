from dataclasses import replace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models.deletion import ProtectedError
from rest_framework.test import APITestCase

from expense.models import Contract_type
from fund.models import Cost_Type
from infos.models import OrganizationInfosType
from leave.models import Leave_Type
from settings.mutable_lists_api_v1 import MUTABLE_LISTS
from staff.models import Employee_Type


class MutableListsV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="list-user")
        self.client.force_login(self.user)

    def grant(self, model, *actions):
        for action in actions:
            permission = Permission.objects.get(content_type__app_label=model._meta.app_label,
                                                codename=f"{action}_{model._meta.model_name}")
            self.user.user_permissions.add(permission)
        self.user = get_user_model().objects.get(pk=self.user.pk)

    def test_registry_contains_only_nine_active_legacy_lists(self):
        response = self.client.get("/api/v1/settings/lists/")
        self.assertEqual(response.status_code, 200, response.data)
        groups = response.data["groups"]
        self.assertEqual([group["key"] for group in groups], ["fund", "contract", "leaves", "project", "staff", "organization"])
        self.assertEqual(sum(len(group["lists"]) for group in groups), 9)
        self.assertNotIn("fund-institutions", MUTABLE_LISTS)
        self.assertNotIn("institutions", MUTABLE_LISTS)
        cost = groups[0]["lists"][0]
        self.assertEqual(cost["columns"], ["name", "short_name", "in_focus", "is_hr"])
        self.assertEqual(next(field for field in cost["fields"] if field["key"] == "parent")["type"], "relation")
        leave = groups[2]["lists"][0]
        self.assertEqual(next(field for field in leave["fields"] if field["key"] == "color")["type"], "color")
        org = next(item for item in groups[-1]["lists"] if item["key"] == "organization-info-types")
        self.assertEqual(next(field for field in org["fields"] if field["key"] == "type")["type"], "choice")
        self.assertFalse(cost["capabilities"]["can_add"])
        self.assertFalse(cost["capabilities"]["can_delete"])

    def test_authentication_and_unknown_list(self):
        self.client.logout()
        self.assertNotEqual(self.client.get("/api/v1/settings/lists/").status_code, 200)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/v1/settings/lists/unknown/").status_code, 404)

    def test_read_create_update_and_denied_delete(self):
        url = "/api/v1/settings/lists/employee-types/"
        self.assertEqual(self.client.post(url, {"name": "Research", "shortname": "R"}, format="json").status_code, 403)
        self.grant(Employee_Type, "add", "change", "delete")
        created = self.client.post(url, {"name": "Research", "shortname": "R"}, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        pk = created.data["id"]
        listing = self.client.get(url)
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual([row["id"] for row in listing.data["rows"]], [pk])
        self.assertTrue(listing.data["rows"][0]["capabilities"]["can_change"])
        changed = self.client.patch(f"{url}{pk}/", {"shortname": "RS"}, format="json")
        self.assertEqual(changed.status_code, 200, changed.data)
        self.assertEqual(changed.data["values"]["shortname"], "RS")
        self.assertEqual(self.client.delete(f"{url}{pk}/").status_code, 403)
        self.assertTrue(Employee_Type.objects.filter(pk=pk).exists())

    def test_validation_and_readonly_form_fields(self):
        self.grant(Contract_type, "add", "change")
        url = "/api/v1/settings/lists/contract-types/"
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 400)
        created = self.client.post(url, {"name": "Fixed"}, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        pk = created.data["id"]
        self.assertEqual(self.client.patch(f"{url}{pk}/", {"name": "Other"}, format="json").status_code, 403)
        self.assertFalse(self.client.get(url).data["rows"][0]["capabilities"]["can_change"])
        self.assertEqual(Contract_type.objects.get(pk=pk).name, "Fixed")

    def test_choice_and_tree_order(self):
        self.grant(OrganizationInfosType, "add")
        url = "/api/v1/settings/lists/organization-info-types/"
        self.assertEqual(self.client.post(url, {"name": "Phone", "type": "invalid"}, format="json").status_code, 400)
        created = self.client.post(url, {"name": "Phone", "type": "tel"}, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["values"]["type"], "tel")
        self.grant(Leave_Type, "add")
        leaves = "/api/v1/settings/lists/leave-types/"
        parent = self.client.post(leaves, {"name": "Leave", "short_name": "L", "color": "#ffffff"}, format="json")
        self.assertEqual(parent.status_code, 201, parent.data)
        child = self.client.post(leaves, {"parent": parent.data["id"], "name": "Child", "short_name": "C", "color": "#ffffff"}, format="json")
        self.assertEqual(child.status_code, 201, child.data)
        self.assertEqual([row["id"] for row in self.client.get(leaves).data["rows"]], [parent.data["id"], child.data["id"]])

    def test_tree_renderer_uses_materialized_levels_and_mptt_order(self):
        for key, model, extra in (
            ("cost-types", Cost_Type, {}),
            ("leave-types", Leave_Type, {"color": "#ffffff"}),
        ):
            parent = model.objects.create(name="Parent", short_name="A", **extra)
            child = model.objects.create(parent=parent, name="Child", short_name="A1", **extra)
            grandchild = model.objects.create(parent=child, name="Grandchild", short_name="A11", **extra)
            other = model.objects.create(name="Other", short_name="B", **extra)
            with patch.object(model, "get_ancestors", side_effect=AssertionError("No ancestor query")):
                response = self.client.get(f"/api/v1/settings/lists/{key}/")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["list"]["renderers"], {"name": "tree"})
            rows = response.data["rows"]
            self.assertEqual([row["id"] for row in rows], [parent.pk, child.pk, grandchild.pk, other.pk])
            self.assertEqual([row["tree_level"] for row in rows], [0, 1, 2, 0])
            self.assertEqual([row["values"]["name"] for row in rows], ["Parent", "Child", "Grandchild", "Other"])
            for row in rows:
                self.assertNotIn("tree_id", row)
                self.assertNotIn("lft", row)
                self.assertNotIn("rght", row)

        ordinary = self.client.get("/api/v1/settings/lists/employee-types/").data
        self.assertNotIn("renderers", ordinary["list"])
        self.assertTrue(all("tree_level" not in row for row in ordinary["rows"]))

    def test_protected_delete_is_a_validation_error_if_enabled_later(self):
        self.grant(Employee_Type, "delete")
        item = Employee_Type.objects.create(name="Referenced", shortname="Ref")
        config = replace(MUTABLE_LISTS["employee-types"], allow_delete=True)
        with patch.dict(MUTABLE_LISTS, {"employee-types": config}), patch.object(Employee_Type, "delete", side_effect=ProtectedError("used", [])):
            response = self.client.delete(f"/api/v1/settings/lists/employee-types/{item.pk}/")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertTrue(Employee_Type.objects.filter(pk=item.pk).exists())
