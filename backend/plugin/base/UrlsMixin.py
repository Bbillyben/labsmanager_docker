import logging
from django.conf import settings
from django.urls import re_path, path
from settings.accessor import get_global_setting
from plugin.urls import PLUGIN_BASE

logger = logging.getLogger('labsmanager')


class UrlsMixin:
    """Publish plugin URL patterns through the existing URL registry.

    Override ``setup_urls`` and optionally ``setup_api_urls``, or declare
    ``URLS`` and ``API_URLS``. Patterns are prefixed with the plugin slug;
    activation updates Django's URL cache when URL plugins change.
    """

    class MixinMeta:
        """Meta options for this mixin."""

        MIXIN_NAME = 'URLs'

    def __init__(self):
        """Register mixin."""
        super().__init__()
        self.add_mixin('urls', 'has_urls', __class__)
        self.urls = self.setup_urls()

    @classmethod
    def _activate_mixin(
        cls,
        registry,
        plugins,
        force_reload=False,
        full_reload: bool = False,
        *args,
        **kwargs,
    ):
        """Activate UrlsMixin plugins - add custom urls .

        Args:
            registry (PluginRegistry): The registry that should be used
            plugins (dict): List of IntegrationPlugins that should be installed
            force_reload (bool, optional): Only reload base apps. Defaults to False.
            full_reload (bool, optional): Reload everything - including plugin mechanism. Defaults to False.
        """
        if settings.PLUGIN_TESTING or get_global_setting('ENABLE_PLUGINS_URL'):
            logger.info('Registering UrlsMixin Plugin')
            urls_changed = False
            # check whether an activated plugin extends UrlsMixin
            for _key, plugin in plugins:
                if plugin.mixin_enabled('urls'):
                    urls_changed = True
            # if apps were changed or force loading base apps -> reload
            if urls_changed or force_reload or full_reload:
                # update urls - must be last as models must be registered for creating admin routes
                registry._update_urls()

    def setup_urls(self):
        """Setup url endpoints for this plugin."""
        return getattr(self, 'URLS', None)
    
    def setup_api_urls(self):
        """Setup url endpoints for this plugin under api/."""
        return getattr(self, 'API_URLS', None)

    @property
    def base_url(self):
        """Base url for this plugin."""
        return f'{PLUGIN_BASE}/{self.slug}/'

    @property
    def internal_name(self):
        """Internal url pattern name."""
        return f'plugin:{self.slug}:'

    @property
    def urlpatterns(self):
        """Return patterns prefixed by the plugin's slug under ``/plugin/``."""
        if not self.urls:
            return []

        prefixed_urls =self.format_urls(self.urls)
        return prefixed_urls
    
    
    def format_urls(self, urls):
        """Prefix path and regex patterns without changing their callbacks."""
        prefixed_urls = []
        for pattern in urls:
            # Preserve the pattern type while adding the plugin slug prefix.
            regex = getattr(pattern.pattern, '_regex', None)
            if regex is not None:
                # re_path
                new_pattern = re_path(
                    f'^{self.slug}/{regex.lstrip("^")}',
                    pattern.callback,
                    name=pattern.name
                )
            else:
                # path
                new_pattern = path(
                    f'{self.slug}/{pattern.pattern}',
                    pattern.callback,
                    name=pattern.name
                )
            prefixed_urls.append(new_pattern)

        return prefixed_urls

    @property
    def has_urls(self):
        """Does this plugin use custom urls."""
        return bool(self.urls)