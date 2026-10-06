"""URL lookup for plugin app."""

from django.conf import settings
from django.urls import include, re_path

from settings.accessor import get_global_setting
from labsmanager.ready import canAppAccessDatabase

PLUGIN_BASE = 'plugin'  # Constant for links


def get_plugin_urls():
    """Returns a urlpattern that can be integrated into the global urls."""
    from plugin.registry import registry

    urls = []

    # URL checks run before the settings tables exist during a first migrate.
    # No plugin URLs can be active before that bootstrap has completed.
    if settings.PLUGIN_TESTING_SETUP or (
        canAppAccessDatabase(allow_test=True, allow_shell=True)
        and get_global_setting('ENABLE_PLUGINS_URL', False)
    ):
        for plugin in registry.plugins.values():
            if plugin.mixin_enabled('urls'):
                urls.extend(plugin.urlpatterns)
    pg_path = re_path(f'^{PLUGIN_BASE}/', include((urls, 'plugin')))
    return pg_path


