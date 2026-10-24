from unittest.mock import patch
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.utils import timezone
from django_q.models import Schedule
from invitations.models import Invitation
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APIClient, APITestCase

from settings.models import LabsManagerSetting
from staff.models import Employee
from plugin.models import PluginConfig
from plugin.base.ImportMixin import ImportMixin
from plugin.dependencies import Candidate
from plugin.registry import registry


BASE = "/api/v1/settings/admin/"


class AdminSettingsV1Tests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.staff = user_model.objects.create_user(username="staff-settings", is_staff=True)
        self.reader = user_model.objects.create_user(username="reader-settings")
        self.other = user_model.objects.create_user(username="other-settings")
        self.employee = Employee.objects.create(first_name="Alice", last_name="Test")

    def test_staff_guard_and_all_five_general_settings(self):
        self.client.force_login(self.reader)
        for path in ("general/settings/", "users/", "notifications/", "plugins/"):
            self.assertEqual(self.client.get(BASE + path).status_code, 403)
        self.assertEqual(self.client.patch(BASE + "general/settings/NEW_EMPLOYEE_CASSE/", {"value": False}, format="json").status_code, 403)
        self.client.force_login(self.staff)
        response = self.client.get(BASE + "general/settings/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual({row["key"] for row in response.data["settings"]}, {
            "MAIL_OBJECT_PREFIX", "EMPLOYEE_CAN_EDIT_SUBORDINATE", "CO_LEADER_CAN_EDIT_PROJECT",
            "AUDIT_LOG_RETENTION", "NEW_EMPLOYEE_CASSE",
        })
        self.assertEqual(self.client.patch(BASE + "general/settings/AUDIT_LOG_RETENTION/", {"value": -1}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(BASE + "general/settings/AUDIT_LOG_RETENTION/", {"value": 30}, format="json").status_code, 200)
        self.assertEqual(LabsManagerSetting.get_setting("AUDIT_LOG_RETENTION"), 30)
        self.assertEqual(self.client.patch(BASE + "general/settings/MAIL_OBJECT_PREFIX/", {"value": "[Lab]"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(BASE + "general/settings/NEW_EMPLOYEE_CASSE/", {"value": "false"}, format="json").status_code, 400)

    def test_user_link_change_unlink_and_conflict(self):
        self.client.force_login(self.staff)
        url = BASE + f"users/{self.reader.pk}/employee/"
        self.assertEqual(self.client.patch(url, {"employee_id": self.employee.pk}, format="json").status_code, 200)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.user_id, self.reader.pk)
        rows = self.client.get(BASE + "users/").data["results"]
        self.assertEqual(next(row for row in rows if row["id"] == self.reader.pk)["employee"]["id"], self.employee.pk)
        other_url = BASE + f"users/{self.other.pk}/employee/"
        self.assertEqual(self.client.patch(other_url, {"employee_id": self.employee.pk}, format="json").status_code, 400)
        replacement = Employee.objects.create(first_name="Bob", last_name="Test")
        self.assertEqual(self.client.patch(url, {"employee_id": replacement.pk}, format="json").status_code, 200)
        self.employee.refresh_from_db()
        self.assertIsNone(self.employee.user_id)
        self.assertEqual(self.client.patch(url, {"employee_id": None}, format="json").status_code, 200)
        replacement.refresh_from_db()
        self.assertIsNone(replacement.user_id)

    @patch("settings.admin_api_v1.send_pending_notification", return_value=2)
    @patch("settings.admin_api_v1.check_overload_employee", return_value=0)
    @patch("settings.admin_api_v1.check_overdue_milestones", return_value=1)
    @patch("settings.admin_api_v1.check_stale_milestones", return_value=2)
    def test_notification_actions_use_historical_functions(self, stale, overdue, overload, send):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(BASE + "notifications/").data["results"], [])
        self.assertEqual(self.client.post(BASE + "notifications/check/").data["counts"], {"stale": 2, "overdue": 1, "overload": 0})
        self.assertEqual(self.client.post(BASE + "notifications/send/").data["sent"], 2)
        stale.assert_called_once(); overdue.assert_called_once(); overload.assert_called_once(); send.assert_called_once()

    def test_plugins_endpoint_and_reload_are_staff_only(self):
        self.client.force_login(self.reader)
        self.assertEqual(self.client.post(BASE + "plugins/reload/").status_code, 403)
        self.client.force_login(self.staff)
        response = self.client.get(BASE + "plugins/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("results", response.data)
        self.assertIn("errors", response.data)
        with patch.object(registry, "errors", {"load": [{"sample": "failed"}]}):
            self.assertEqual(self.client.get(BASE + "plugins/").data["errors"],
                             [{"stage": "load", "name": "sample", "message": "failed"}])
        with patch("settings.admin_api_v1.registry.reload_plugins") as reload:
            self.assertEqual(self.client.post(BASE + "plugins/reload/").status_code, 200)
            reload.assert_called_once_with(full_reload=True, force_reload=True, collect=True)
        for key in registry.plugins:
            detail = self.client.get(BASE + f"plugins/{key}/")
            self.assertEqual(detail.status_code, 200, detail.data)
            self.assertEqual(set(detail.data["sections"]).intersection({"settings", "schedule", "urls"}),
                             {mixin for mixin in ("settings", "schedule", "urls") if registry.plugins[key].mixin_enabled(mixin)})
            if detail.data["sections"].get("settings"):
                setting = next((item for item in detail.data["sections"]["settings"] if item["type"] == "boolean"), None)
                if setting:
                    url = BASE + f"plugins/{key}/settings/{setting['key']}/"
                    self.assertEqual(self.client.patch(url, {"value": True}, format="json").status_code, 200)
                    self.assertEqual(self.client.patch(url, {"value": "true"}, format="json").status_code, 400)

    def test_plugin_origins_are_included_for_discovered_candidates(self):
        backend = Path(__file__).resolve().parents[2]
        self.client.force_login(self.staff)
        discovered = self.client.get(BASE + 'plugins/')
        self.assertEqual(discovered.status_code, 200, discovered.data)
        origins = {row['key']: row['origin'] for row in discovered.data['results']}
        self.assertEqual(origins['frenchholliday'], 'sample')
        self.assertEqual(origins['icalexport'], 'builtin')
        candidates = {
            'frenchholliday': Candidate('frenchholliday', backend / 'plugin/samples/FrenchHollidayPlugin', 'FrenchHollidayPlugin'),
            'icalexport': Candidate('icalexport', backend / 'plugin/builtin/ICalExport', 'ICalExport'),
            'external': Candidate('external', backend / 'data/plugins/External', 'External'),
        }
        with patch.object(registry, 'plugins_full', {}), patch.object(registry, 'check_reload'), \
                patch('settings.admin_api_v1.discover_candidates', return_value=candidates), \
                patch('settings.admin_api_v1.diagnose', return_value=None):
            response = self.client.get(BASE + 'plugins/')
        self.assertEqual(response.status_code, 200, response.data)
        rows = {row['key']: row for row in response.data['results']}
        self.assertEqual({key: row['origin'] for key, row in rows.items()},
                         {'frenchholliday': 'sample', 'icalexport': 'builtin', 'external': 'external'})
        self.assertEqual({key: row['is_builtin'] for key, row in rows.items()},
                         {'frenchholliday': False, 'icalexport': True, 'external': False})

    def test_plugin_activation_uses_legacy_endpoint_and_persists_state(self):
        config = PluginConfig.objects.create(key="test-admin-plugin", name="Test admin plugin")
        url = "/api/plugin/test-admin-plugin/activate/"
        self.client.force_login(self.reader)
        self.assertEqual(self.client.patch(url, {"active": True}, format="json").status_code, 403)
        config.refresh_from_db()
        self.assertFalse(config.active)
        strict = APIClient(enforce_csrf_checks=True)
        strict.force_login(self.staff)
        self.assertEqual(strict.patch(url, {"active": True}, format="json").status_code, 403)
        config.refresh_from_db()
        self.assertFalse(config.active)
        self.client.force_login(self.staff)
        with patch.object(registry, "reload_plugins") as reload:
            self.assertEqual(self.client.patch(url, {"active": True}, format="json").status_code, 200)
            config.refresh_from_db()
            self.assertTrue(config.active)
            self.assertEqual(self.client.patch(url, {"active": False}, format="json").status_code, 200)
            config.refresh_from_db()
            self.assertFalse(config.active)
            self.assertEqual(reload.call_count, 2)
        self.assertTrue(PluginConfig.objects.filter(pk=config.pk).exists())

    def test_discovered_inactive_plugin_is_listed_without_initialization(self):
        class InactivePlugin(ImportMixin):
            NAME = "Import plugin"
            TITLE = "Import plugin"
            DESCRIPTION = "Inactive import"
            AUTHOR = "Ada"
            VERSION = "1"

            @classmethod
            def check_is_builtin(cls):
                return False

            @classmethod
            def check_is_sample(cls):
                return False

            def __init__(self):
                raise AssertionError("Inactive plugins must not be initialized for the list")

        PluginConfig.objects.create(key="inactive-import", name="Import plugin")
        self.client.force_login(self.staff)
        with patch.object(registry, "plugins_full", {"inactive-import": InactivePlugin}), \
                patch.object(registry, "plugins", {}), patch.object(registry, "check_reload"):
            response = self.client.get(BASE + "plugins/")
        self.assertEqual(response.status_code, 200, response.data)
        plugin = next(row for row in response.data["results"] if row["key"] == "inactive-import")
        self.assertFalse(plugin["active"])
        self.assertFalse(plugin["is_builtin"])
        self.assertEqual(plugin["origin"], "external")
        self.assertIn("importmixin", plugin["mixins"])

    def test_kiosk_and_frenchholiday_details_are_json_serializable(self):
        self.client.force_login(self.staff)
        Schedule.objects.create(name=registry.plugins["frenchholliday"].get_task_names()[0],
                                func="plugin.registry.call_plugin_function")
        kiosk = self.client.get(BASE + "plugins/kiosk/")
        frenchholiday = self.client.get(BASE + "plugins/frenchholliday/")
        self.assertEqual(kiosk.status_code, 200, kiosk.data)
        self.assertEqual(frenchholiday.status_code, 200, frenchholiday.data)
        self.assertIn("settings", kiosk.data["sections"])
        self.assertIn("urls", kiosk.data["sections"])
        self.assertNotIn("schedule", kiosk.data["sections"])
        self.assertIn("settings", frenchholiday.data["sections"])
        self.assertIn("schedule", frenchholiday.data["sections"])
        self.assertTrue(frenchholiday.data["sections"]["schedule"])

        def assert_no_callable(value):
            self.assertFalse(callable(value), value)
            if isinstance(value, dict):
                for nested in value.values():
                    assert_no_callable(nested)
            elif isinstance(value, (list, tuple)):
                for nested in value:
                    assert_no_callable(nested)

        assert_no_callable(frenchholiday.data)
        for task in frenchholiday.data["sections"]["schedule"]:
            self.assertIsInstance(task["function"], str)
            self.assertIsInstance(task["success"], bool)
        JSONRenderer().render(kiosk.data)
        JSONRenderer().render(frenchholiday.data)


class AdminInvitationsV1Tests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.staff = users.objects.create_user(username="invitation-admin", is_staff=True)
        self.reader = users.objects.create_user(username="invitation-reader", email="registered@example.test")

    def test_staff_lists_all_states_with_historical_fields_and_nonstaff_is_denied(self):
        invite = Invitation.create("pending@example.test", inviter=self.staff)
        invite.sent = timezone.now()
        invite.save()
        unsent = Invitation.create("unsent@example.test")
        accepted = Invitation.create("accepted-visible@example.test")
        accepted.sent = timezone.now()
        accepted.accepted = True
        accepted.save()
        expired = Invitation.create("expired-visible@example.test")
        expired.sent = timezone.now() - timedelta(days=4)
        expired.save()
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(BASE + "invitations/").status_code, 403)
        self.assertEqual(self.client.post(BASE + "invitations/", {"email": "new@example.test"}, format="json").status_code, 403)
        self.assertEqual(self.client.post(BASE + "invitations/remove-expired/").status_code, 403)
        self.client.force_login(self.staff)
        response = self.client.get(BASE + "invitations/")
        self.assertEqual(response.status_code, 200, response.data)
        rows = {row["id"]: row for row in response.data["results"]}
        self.assertEqual(set(rows[invite.pk]), {"id", "email", "created", "sent", "accepted", "key_expired", "inviter", "employee", "group_ids"})
        self.assertEqual(rows[invite.pk]["inviter"], {"id": self.staff.pk, "username": self.staff.username})
        self.assertFalse(rows[invite.pk]["accepted"])
        self.assertFalse(rows[invite.pk]["key_expired"])
        self.assertIsNone(rows[unsent.pk]["sent"])
        self.assertIsNone(rows[unsent.pk]["inviter"])
        self.assertTrue(rows[accepted.pk]["accepted"])
        self.assertTrue(rows[expired.pk]["key_expired"])

    @patch("invitations.models.get_invitations_adapter")
    def test_invitation_uses_package_send_and_email_validation(self, adapter):
        self.client.force_login(self.staff)
        url = BASE + "invitations/"
        self.assertEqual(self.client.post(url, {"email": "invalid"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"email": "registered@example.test"}, format="json").status_code, 400)
        response = self.client.post(url, {"email": "new@example.test"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        invite = Invitation.objects.get(email="new@example.test")
        self.assertEqual(invite.inviter_id, self.staff.pk)
        self.assertIsNotNone(invite.sent)
        self.assertEqual(response.data["id"], invite.pk)
        adapter.return_value.send_mail.assert_called_once()
        self.assertEqual(self.client.post(url, {"email": "new@example.test"}, format="json").status_code, 400)

    def test_remove_expired_uses_package_manager_and_keeps_active(self):
        self.client.force_login(self.staff)
        active = Invitation.create("active@example.test")
        active.sent = timezone.now()
        active.save()
        expired = Invitation.create("expired@example.test")
        expired.sent = timezone.now() - timedelta(days=4)
        expired.save()
        accepted = Invitation.create("accepted@example.test")
        accepted.sent = timezone.now()
        accepted.accepted = True
        accepted.save()
        with patch.object(Invitation.objects, "delete_expired_confirmations", wraps=Invitation.objects.delete_expired_confirmations) as delete:
            response = self.client.post(BASE + "invitations/remove-expired/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["deleted"], 2)
        delete.assert_called_once()
        self.assertTrue(Invitation.objects.filter(pk=active.pk).exists())
        self.assertFalse(Invitation.objects.filter(pk=expired.pk).exists())
        self.assertFalse(Invitation.objects.filter(pk=accepted.pk).exists())
