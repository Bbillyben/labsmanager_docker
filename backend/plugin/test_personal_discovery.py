from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase

from plugin.registry import registry


def example(name, *, settings=False, user_token=False, plugin_token=False):
    mixins = {'settings': settings, 'token': user_token or plugin_token}
    return SimpleNamespace(human_name=name, description=f'{name} description',
                           mixin_enabled=lambda key: mixins.get(key, False),
                           TOKEN_CONFIG={'user': user_token, 'plugin': plugin_token})


class PluginDiscoveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('reader')
        self.staff = User.objects.create_user('staff', is_staff=True)

    def test_personal_discovery_uses_active_capabilities_only(self):
        plugins = {'preferences': example('Preferences', settings=True),
                   'tokens': example('Tokens', user_token=True),
                   'technical': example('Technical', plugin_token=True),
                   'ordinary': example('Ordinary')}
        url = '/api/v1/plugins/mine/'
        self.assertIn(self.client.get(url).status_code, (401, 403))
        self.client.force_login(self.user)
        with patch.object(registry, 'check_reload'), patch.object(registry, 'plugins', plugins), patch.object(
            registry, 'mixins_user_settings', {'preferences': {'COLOUR': {'default': 'blue'}}}, create=True
        ):
            results = self.client.get(url).json()['results']
            self.assertEqual([row['key'] for row in results], ['preferences', 'tokens'])
            self.assertTrue(all('origin' not in row for row in results))
            del plugins['preferences']
            self.assertEqual([row['key'] for row in self.client.get(url).json()['results']], ['tokens'])

    def test_admin_detail_advertises_only_enabled_technical_tokens(self):
        self.client.force_login(self.staff)
        url = '/api/v1/settings/admin/plugins/technical/'
        plugin = example('Technical', plugin_token=True)
        with patch.object(registry, 'get_plugin', return_value=plugin), patch.object(registry, 'get_plugin_config', return_value=None), patch(
            'settings.admin_api_v1.discovered_plugin_data', return_value={'key': 'technical'}
        ):
            self.assertTrue(self.client.get(url).json()['sections']['tokens'])
            plugin.TOKEN_CONFIG['plugin'] = False
            self.assertNotIn('tokens', self.client.get(url).json()['sections'])
