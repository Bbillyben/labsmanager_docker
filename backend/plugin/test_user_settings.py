from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from plugin.base.SettingMixin import SettingsMixin
from plugin.models import PluginConfig, PluginSetting, UserPluginSetting
from plugin.registry import registry


DEFINITIONS = {'COLOUR': {'name': 'Colour', 'description': 'Personal colour', 'default': 'blue',
                          'choices': [('blue', 'Blue'), ('red', 'Red')]}}


class UserPluginSettingTests(TestCase):
    def setUp(self):
        self.plugin = PluginConfig.objects.create(key='personal-test', name='Personal Test')
        self.other_plugin = PluginConfig.objects.create(key='other-personal-test')
        PluginConfig.objects.filter(pk__in=[self.plugin.pk, self.other_plugin.pk]).update(active=True)
        self.plugin.active = True
        self.other_plugin.active = True
        self.alice = User.objects.create_user('alice')
        self.bob = User.objects.create_user('bob')
        class ExampleSettings(SettingsMixin):
            USER_SETTINGS = DEFINITIONS

            def add_mixin(self, *args):
                pass

            def plugin_config(inner_self):
                return self.plugin

        self.mixin = ExampleSettings()
        self.registry_patch = patch.object(registry, 'mixins_user_settings', {
            self.plugin.key: DEFINITIONS, self.other_plugin.key: DEFINITIONS,
        }, create=True)
        self.registry_patch.start()
        self.addCleanup(self.registry_patch.stop)

    def test_defaults_writes_validation_and_isolation(self):
        self.assertEqual(self.mixin.get_user_setting('COLOUR', self.alice), 'blue')
        self.assertFalse(UserPluginSetting.objects.exists())
        self.assertEqual(self.mixin.set_user_setting('COLOUR', 'red', self.alice), 'red')
        self.assertEqual(self.mixin.get_user_setting('COLOUR', self.bob), 'blue')
        self.assertEqual(UserPluginSetting.get_setting('COLOUR', plugin=self.other_plugin, user=self.alice, create=False), 'blue')
        with self.assertRaises(ValidationError):
            self.mixin.set_user_setting('COLOUR', 'green', self.alice)
        self.assertEqual(self.mixin.reset_user_setting('COLOUR', self.alice), 'blue')
        self.assertFalse(UserPluginSetting.objects.exists())

    def test_uniqueness_and_global_setting_remains_separate(self):
        UserPluginSetting.objects.create(plugin=self.plugin, user=self.alice, key='COLOUR', value='red')
        with self.assertRaises(ValidationError):
            UserPluginSetting.objects.create(plugin=self.plugin, user=self.alice, key='colour', value='blue')
        UserPluginSetting.objects.create(plugin=self.plugin, user=self.bob, key='COLOUR', value='blue')
        UserPluginSetting.objects.create(plugin=self.other_plugin, user=self.alice, key='COLOUR', value='blue')
        with patch.object(registry, 'mixins_settings', {self.plugin.key: DEFINITIONS}, create=True):
            PluginSetting.objects.create(plugin=self.plugin, key='COLOUR', value='blue')
            self.assertEqual(PluginSetting.get_setting('COLOUR', plugin=self.plugin, create=False), 'blue')
        self.assertEqual(UserPluginSetting.objects.count(), 3)

    def test_registry_definitions_follow_activation(self):
        self.assertTrue(self.mixin.has_settings)
        fake_registry = SimpleNamespace()
        plugin = SimpleNamespace(settings={}, user_settings=DEFINITIONS,
                                 mixin_enabled=lambda name: name == 'settings')
        SettingsMixin._activate_mixin(fake_registry, [('personal-test', plugin)])
        self.assertEqual(fake_registry.mixins_user_settings['personal-test'], DEFINITIONS)
        SettingsMixin._deactivate_mixin(fake_registry)
        self.assertEqual(fake_registry.mixins_user_settings, {})

    def test_api_is_current_user_only_and_survives_deactivation(self):
        plugin = SimpleNamespace(mixin_enabled=lambda name: name == 'settings')
        with patch.object(registry, 'get_plugin', return_value=plugin), patch.object(registry, 'get_plugin_config', return_value=self.plugin):
            url = '/api/v1/plugins/personal-test/user-settings/'
            self.assertIn(self.client.get(url).status_code, (401, 403))
            self.client.force_login(self.alice)
            self.assertEqual(self.client.get(url).json()['settings'][0]['value'], 'blue')
            self.assertFalse(UserPluginSetting.objects.exists())
            detail = url + 'COLOUR/'
            self.assertEqual(self.client.patch(detail, data='{"value":"red","user_id":2}', content_type='application/json').status_code, 400)
            self.assertEqual(self.client.patch(detail, data='{"value":"red"}', content_type='application/json').status_code, 200)
            self.client.force_login(self.bob)
            self.assertEqual(self.client.get(url).json()['settings'][0]['value'], 'blue')
            self.plugin.active = False
            self.plugin.save(no_reload=True)
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(UserPluginSetting.objects.get(plugin=self.plugin, user=self.alice).value, 'red')
            self.plugin.active = True
            self.plugin.save(no_reload=True)
            self.client.force_login(self.alice)
            self.assertEqual(self.client.get(url).json()['settings'][0]['value'], 'red')
