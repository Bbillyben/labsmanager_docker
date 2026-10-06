"""Focused checks for deployment configuration and first-migration URL loading."""

from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from labsmanager.config import get_setting
from plugin.urls import get_plugin_urls


class TypedConfigurationTests(SimpleTestCase):
    @patch("labsmanager.config.load_config_data", return_value={"session_cookie_age": 1800})
    @patch.dict("os.environ", {"LAB_SESSION_COOKIE_AGE": "7200"})
    def test_integer_environment_value_is_cast(self, _config):
        self.assertEqual(get_setting("LAB_SESSION_COOKIE_AGE", "session_cookie_age", 6400, int), 7200)

    @patch("labsmanager.config.load_config_data", return_value={"email": {"port": 25}})
    @patch.dict("os.environ", {"LAB_EMAIL_PORT": ""})
    def test_blank_typed_environment_value_uses_config(self, _config):
        self.assertEqual(get_setting("LAB_EMAIL_PORT", "email.port", 25, int), 25)

    @patch.dict("os.environ", {"LAB_SESSION_COOKIE_AGE": "invalid"})
    def test_invalid_integer_fails_instead_of_leaking_string(self):
        with self.assertRaises(ImproperlyConfigured):
            get_setting("LAB_SESSION_COOKIE_AGE", "session_cookie_age", 6400, int)


class PluginUrlBootstrapTests(SimpleTestCase):
    @override_settings(PLUGIN_TESTING_SETUP=False)
    @patch("plugin.urls.get_global_setting")
    @patch("plugin.urls.canAppAccessDatabase", return_value=False)
    def test_migration_checks_do_not_query_settings_table(self, _ready, setting):
        self.assertIsNotNone(get_plugin_urls())
        setting.assert_not_called()

    @override_settings(PLUGIN_TESTING_SETUP=False)
    @patch("plugin.urls.get_global_setting", return_value=False)
    @patch("plugin.urls.canAppAccessDatabase", return_value=True)
    def test_runtime_still_uses_plugin_url_setting(self, _ready, setting):
        get_plugin_urls()
        setting.assert_called_once_with("ENABLE_PLUGINS_URL", False)
