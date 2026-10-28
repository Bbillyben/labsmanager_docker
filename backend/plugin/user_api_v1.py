"""Current-user settings for active plugins."""

from django.http import Http404
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from plugin.models import UserPluginSetting
from plugin.registry import registry
from plugin.ui_contributions import declared_contributions, is_visible
from settings.admin_api_v1 import save_setting, setting_data


def personal_settings(key):
    plugin = registry.get_plugin(key)
    if plugin is None or not plugin.mixin_enabled('settings'):
        raise Http404
    config = registry.get_plugin_config(key)
    if config is None or not config.active:
        raise Http404
    return config, getattr(registry, 'mixins_user_settings', {}).get(key, {})


class UserPlugins(APIView):
    """Discover active plugins with personal settings or tokens."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        registry.check_reload()
        action_plugins = {plugin.slug for plugin, item in declared_contributions()
                          if item['slot'] == 'user.plugin.settings.actions'}
        panel_plugins = {plugin.slug for plugin, item in declared_contributions()
                         if item['slot'] == 'user.plugin.settings.panels'
                         and is_visible(plugin, item, request, {'plugin': plugin, 'plugin_key': plugin.slug})}
        results = []
        for key, plugin in registry.plugins.items():
            settings_available = plugin.mixin_enabled('settings') and bool(
                getattr(registry, 'mixins_user_settings', {}).get(key, {}))
            tokens_available = plugin.mixin_enabled('token') and getattr(plugin, 'TOKEN_CONFIG', {}).get('user') is True
            actions_available = key in action_plugins
            panels_available = key in panel_plugins
            if settings_available or tokens_available or actions_available or panels_available:
                results.append({'key': key, 'human_name': str(plugin.human_name),
                                'description': str(plugin.description), 'user_settings': settings_available,
                                'user_tokens': tokens_available, 'ui_actions': actions_available,
                                'ui_panels': panels_available})
        return Response({'results': sorted(results, key=lambda item: item['human_name'].casefold())})


class UserPluginSettings(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, key):
        config, definitions = personal_settings(key)
        return Response({'settings': [
            setting_data(UserPluginSetting, name, plugin=config, user=request.user)
            for name, definition in definitions.items() if not definition.get('hidden')
        ]})


class UserPluginSettingDetail(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _setting(self, request, key, setting_key):
        config, definitions = personal_settings(key)
        setting_key = setting_key.upper()
        definition = definitions.get(setting_key)
        if definition is None or definition.get('hidden'):
            raise Http404
        return config, setting_key

    def patch(self, request, key, setting_key):
        config, setting_key = self._setting(request, key, setting_key)
        if not isinstance(request.data, dict) or set(request.data) != {'value'}:
            raise serializers.ValidationError({'value': 'Expected one value.'})
        return Response(save_setting(UserPluginSetting, setting_key, request.data['value'], plugin=config, user=request.user))

    def delete(self, request, key, setting_key):
        config, setting_key = self._setting(request, key, setting_key)
        UserPluginSetting.objects.filter(plugin=config, user=request.user, key=setting_key).delete()
        return Response(setting_data(UserPluginSetting, setting_key, plugin=config, user=request.user))
