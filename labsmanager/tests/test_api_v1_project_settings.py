from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework.test import APITestCase

from project.models import Participant, Project
from settings.models import LMProjectSetting
from staff.models import Employee


class ProjectSettingsV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="settings-leader", password="test")
        self.employee = Employee.objects.create(first_name="A", last_name="Leader", user=self.user)
        self.project = Project.objects.create(name="Atlas settings", status=True)
        self.other = Project.objects.create(name="Other settings", status=True)
        Participant.objects.create(project=self.project, employee=self.employee, status="l")
        self.client.force_login(self.user)

    def url(self, project=None):
        return reverse("api_v1:project-settings", kwargs={"pk": (project or self.project).pk})

    def item_url(self, key, project=None):
        return reverse("api_v1:project-setting-detail", kwargs={"pk": (project or self.project).pk, "key": key})

    def grant(self, app, codename):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    def test_metadata_and_defaults_without_creating_rows(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        settings = response.json()["settings"]
        self.assertEqual([item["key"] for item in settings], list(LMProjectSetting.SETTINGS))
        self.assertEqual(settings[0]["type"], "choice")
        self.assertEqual(settings[0]["value"], "s")
        self.assertEqual(settings[0]["default"], "s")
        self.assertEqual([choice["value"] for choice in settings[0]["choices"]], ["s", "e", "h"])
        self.assertEqual([item["value"] for item in settings[1:]], [True, True])
        self.assertEqual([item["type"] for item in settings[1:]], ["boolean", "boolean"])
        self.assertFalse(LMProjectSetting.objects.filter(project=self.project).exists())
        detail = self.client.get(reverse("api_v1:project-detail", kwargs={"pk": self.project.pk})).json()
        self.assertTrue(detail["capabilities"]["can_change_settings"])

    def test_metadata_uses_django_translations_for_names_and_choices(self):
        french = self.client.get(self.url(), HTTP_ACCEPT_LANGUAGE="fr").json()["settings"]
        english = self.client.get(self.url(), HTTP_ACCEPT_LANGUAGE="en").json()["settings"]
        self.assertEqual(french[0]["name"], "Mode de calcul des dépenses")
        self.assertEqual(french[0]["choices"][1]["label"], "Dépenses individuelles")
        self.assertEqual(english[0]["name"], "Expense calculation mode")
        self.assertEqual(english[0]["choices"][1]["label"], "Individual expenses")

    def test_object_change_or_global_settings_permission_and_hidden_project(self):
        reader = get_user_model().objects.create_user(username="settings-reader", password="test")
        reader.user_permissions.add(Permission.objects.get(content_type__app_label="project", codename="view_project"))
        self.client.force_login(reader)
        self.assertFalse(self.client.get(reverse("api_v1:project-detail", kwargs={"pk": self.project.pk})).json()["capabilities"]["can_change_settings"])
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        self.assertEqual(self.client.patch(self.item_url("LEADER_EDIT_FUND"), {"value": False}, format="json").status_code, 403)
        reader.user_permissions.add(Permission.objects.get(content_type__app_label="settings", codename="change_lmprojectsetting"))
        reader = get_user_model().objects.get(pk=reader.pk)
        self.client.force_login(reader)
        self.assertTrue(self.client.get(reverse("api_v1:project-detail", kwargs={"pk": self.project.pk})).json()["capabilities"]["can_change_settings"])
        self.assertEqual(self.client.get(self.url()).status_code, 200)
        self.assertEqual(self.client.patch(self.item_url("LEADER_EDIT_FUND"), {"value": False}, format="json").status_code, 200)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url(self.other)).status_code, 404)
        self.assertEqual(self.client.patch(self.item_url("LEADER_EDIT_FUND", self.other), {"value": False}, format="json").status_code, 404)

    def test_first_mutation_creates_setting_via_save_and_isolates_project(self):
        original = LMProjectSetting.save
        with patch.object(LMProjectSetting, "save", autospec=True, side_effect=original) as save:
            response = self.client.patch(self.item_url("LEADER_EDIT_FUND"), {"value": False}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.json()["value"])
        self.assertEqual(save.call_count, 1)
        setting = LMProjectSetting.objects.get(project=self.project, key="LEADER_EDIT_FUND")
        self.assertFalse(setting.to_native_value())
        self.assertTrue(LMProjectSetting.get_setting("LEADER_EDIT_FUND", project=self.other, create=False))
        self.assertFalse(LMProjectSetting.objects.filter(project=self.other).exists())
        self.assertEqual(self.client.patch(self.item_url("LEADER_EDIT_FUND"), {"value": True}, format="json").json()["value"], True)

    def test_choice_values_and_invalid_inputs(self):
        url = self.item_url("EXPENSE_CALCULATION")
        for value in ("s", "e", "h"):
            with self.subTest(value=value):
                response = self.client.patch(url, {"value": value}, format="json")
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.json()["value"], value)
        self.assertEqual(self.client.patch(url, {"value": "unknown"}, format="json").status_code, 400)
        self.assertEqual(self.client.get(self.url()).json()["settings"][0]["value"], "h")
        self.assertEqual(self.client.patch(self.item_url("LEADER_EDIT_FUND"), {"value": "garbage"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.item_url("LEADER_EDIT_FUND"), {"value": 0}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.item_url("UNKNOWN"), {"value": True}, format="json").status_code, 404)
