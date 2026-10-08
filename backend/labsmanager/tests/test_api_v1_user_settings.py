from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from allauth.account.models import EmailAddress
from settings.models import LMUserSetting
from django.apps import apps
from importlib import import_module


class UserSettingsV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="settings-reader", password="old-secret-123")
        self.other = get_user_model().objects.create_user(username="other-settings")
        self.client.force_login(self.user)

    def test_sections_expose_effective_values_and_metadata_without_creating_rows(self):
        for section in ("interface", "notifications", "stale"):
            response = self.client.get(f"/api/v1/settings/user/{section}/")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertTrue(response.data["settings"])
            for setting in response.data["settings"]:
                self.assertIn("default", setting)
                self.assertIn("choices", setting)
                self.assertTrue(setting["can_change"])
        self.assertEqual(LMUserSetting.objects.filter(user=self.user).count(), 0)
        self.assertEqual(self.client.get("/api/v1/settings/user/unknown/").status_code, 404)

    def test_updates_are_typed_validated_and_scoped_to_current_user(self):
        LMUserSetting.objects.create(user=self.other, key="DASHBOARD_PROJECT_STALE_TO_MONTH", value="9")
        url = "/api/v1/settings/user/stale/DASHBOARD_PROJECT_STALE_TO_MONTH/"
        response = self.client.patch(url, {"value": 6}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["value"], 6)
        self.assertEqual(LMUserSetting.get_setting("DASHBOARD_PROJECT_STALE_TO_MONTH", user=self.other), 9)
        self.assertEqual(self.client.patch(url, {"value": -1}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"value": "7"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"value": 7, "user": self.other.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.patch("/api/v1/settings/user/stale/MAP_PROVIDER/", {"value": "x"}, format="json").status_code, 404)

    def test_dashboard_settings_include_four_stale_fields(self):
        settings = self.client.get("/api/v1/settings/user/stale/").data["settings"]
        self.assertEqual(
            {item["key"] for item in settings},
            {
                "DASHBOARD_CONTRACT_STALE_TO_MONTH",
                "DASHBOARD_PROJECT_STALE_TO_MONTH",
                "DASHBOARD_MILESTONES_STALE_TO_MONTH",
                "DASHBOARD_FUND_STALE_TO_MONTH",
            },
        )
        self.assertTrue(all(item["type"] == "integer" for item in settings))
        for key in ("DASHBOARD_MILESTONES_STALE_TO_MONTH", "DASHBOARD_FUND_STALE_TO_MONTH"):
            response = self.client.patch(f"/api/v1/settings/user/stale/{key}/", {"value": 4}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["value"], 4)

    def test_choice_and_boolean_validation(self):
        interface = self.client.get("/api/v1/settings/user/interface/").data["settings"]
        boolean = next(item for item in interface if item["type"] == "boolean")
        choice = next(item for item in interface if item["type"] == "choice")
        for item, value in ((boolean, True), (choice, choice["choices"][0]["value"])):
            url = f"/api/v1/settings/user/interface/{item['key']}/"
            response = self.client.patch(url, {"value": value}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["value"], value)
        self.assertEqual(self.client.patch(f"/api/v1/settings/user/interface/{boolean['key']}/", {"value": "true"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(f"/api/v1/settings/user/interface/{choice['key']}/", {"value": "invalid"}, format="json").status_code, 400)

    def test_theme_is_a_two_choice_user_setting_and_me_uses_it(self):
        setting = next(row for row in self.client.get("/api/v1/settings/user/interface/").data["settings"] if row["key"] == "LAB_THEME")
        self.assertEqual(setting["value"], "light")
        self.assertEqual([choice["value"] for choice in setting["choices"]], ["light", "dark"])
        url = "/api/v1/settings/user/interface/LAB_THEME/"
        self.assertEqual(self.client.patch(url, {"value": "dark"}, format="json").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/me/").data["theme"], "dark")
        self.assertEqual(self.client.patch(url, {"value": "default"}, format="json").status_code, 400)

    def test_theme_data_migration_deletes_only_theme_preferences(self):
        theme = LMUserSetting.objects.create(user=self.user, key="LAB_THEME", value="dark")
        other = LMUserSetting.objects.create(user=self.user, key="MAP_PROVIDER", value="gmap")
        migration = import_module("settings.migrations.0009_reset_lab_theme")
        migration.reset_lab_theme(apps, None)
        self.assertFalse(LMUserSetting.objects.filter(pk=theme.pk).exists())
        self.assertTrue(LMUserSetting.objects.filter(pk=other.pk).exists())
        self.assertEqual(LMUserSetting.get_setting("LAB_THEME", user=self.user, create=False), "light")

    def test_notification_preference_uses_existing_model_hook(self):
        url = "/api/v1/settings/user/notifications/NOTIFCATION_FREQ/"
        response = self.client.patch(url, {"value": "3 5 1 * *"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["value"], "3 5 1 * *")
        self.assertEqual(LMUserSetting.get_setting("NOTIFCATION_FREQ", user=self.user), "3 5 1 * *")

    def test_account_password_and_email_actions_use_only_current_user(self):
        account = self.client.get("/api/v1/settings/account/")
        self.assertEqual(account.status_code, 200, account.data)
        self.assertEqual(account.data["username"], self.user.username)
        password = self.client.post("/api/v1/settings/account/password/", {
            "oldpassword": "old-secret-123", "password1": "New-secret-456!", "password2": "New-secret-456!",
        }, format="json")
        self.assertEqual(password.status_code, 200, password.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-secret-456!"))

        foreign = EmailAddress.objects.create(user=self.other, email="other@example.test", verified=True)
        self.assertEqual(self.client.patch(f"/api/v1/settings/account/emails/{foreign.pk}/", {"action": "primary"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/v1/settings/account/emails/{foreign.pk}/").status_code, 404)

    def test_email_lifecycle_uses_allauth_rules(self):
        primary = EmailAddress.objects.create(user=self.user, email="first@example.test", verified=True, primary=True)
        self.user.email = primary.email
        self.user.save(update_fields=["email"])
        current = self.client.get("/api/v1/settings/account/")
        primary_data = next(row for row in current.data["emails"] if row["id"] == primary.pk)
        self.assertTrue(primary_data["primary"])
        self.assertTrue(primary_data["verified"])
        self.assertFalse(primary_data["can_delete"])
        blocked = self.client.delete(f"/api/v1/settings/account/emails/{primary.pk}/")
        self.assertEqual(blocked.status_code, 400)
        self.assertIn("primary", str(blocked.data).lower())
        self.assertTrue(EmailAddress.objects.filter(pk=primary.pk).exists())
        created = self.client.post("/api/v1/settings/account/emails/", {"email": "second@example.test"}, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        second = EmailAddress.objects.get(user=self.user, email="second@example.test")
        self.assertFalse(second.verified)
        second_data = next(row for row in created.data["emails"] if row["id"] == second.pk)
        self.assertFalse(second_data["primary"])
        self.assertFalse(second_data["verified"])
        self.assertTrue(second_data["can_resend"])
        self.assertEqual(self.client.patch(f"/api/v1/settings/account/emails/{second.pk}/", {"action": "primary"}, format="json").status_code, 400)
        resent = self.client.patch(f"/api/v1/settings/account/emails/{second.pk}/", {"action": "resend"}, format="json")
        self.assertEqual(resent.status_code, 200, resent.data)
        second.verified = True
        second.save(update_fields=["verified"])
        self.assertEqual(self.client.patch(f"/api/v1/settings/account/emails/{second.pk}/", {"action": "resend"}, format="json").status_code, 400)
        promoted = self.client.patch(f"/api/v1/settings/account/emails/{second.pk}/", {"action": "primary"}, format="json")
        self.assertEqual(promoted.status_code, 200, promoted.data)
        self.assertEqual(EmailAddress.objects.get(pk=second.pk).primary, True)
        self.assertFalse(EmailAddress.objects.get(pk=primary.pk).primary)
        removed = self.client.delete(f"/api/v1/settings/account/emails/{primary.pk}/")
        self.assertEqual(removed.status_code, 200, removed.data)
        self.assertFalse(EmailAddress.objects.filter(pk=primary.pk).exists())

    def test_sole_primary_email_cannot_be_removed(self):
        primary = EmailAddress.objects.create(user=self.user, email="only@example.test", verified=True, primary=True)
        self.user.email = primary.email
        self.user.save(update_fields=["email"])
        response = self.client.get("/api/v1/settings/account/")
        self.assertFalse(response.data["emails"][0]["can_delete"])
        denied = self.client.delete(f"/api/v1/settings/account/emails/{primary.pk}/")
        self.assertEqual(denied.status_code, 400)
        self.assertTrue(EmailAddress.objects.filter(pk=primary.pk).exists())

    def test_anonymous_user_cannot_access_settings_or_account(self):
        self.client.logout()
        for url in ("/api/v1/settings/account/", "/api/v1/settings/account/emails/", "/api/v1/settings/user/stale/"):
            self.assertIn(self.client.get(url).status_code, (401, 403))
