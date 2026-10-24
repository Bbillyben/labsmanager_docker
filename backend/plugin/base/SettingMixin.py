"""Plugin mixin class for SettingsMixin."""

import logging
from typing import TYPE_CHECKING

from django.db.utils import OperationalError, ProgrammingError

logger = logging.getLogger('labsmanager')

# import only for typechecking, otherwise this throws a model is unready error
if TYPE_CHECKING:
    from settings.models import SettingsKeyType
else:
    class SettingsKeyType:
        """Dummy class, so that python throws no error."""


class SettingsMixin:
    """Mixin that enables global settings for the plugin."""

    SETTINGS: dict[str, SettingsKeyType] = {}
    USER_SETTINGS: dict[str, SettingsKeyType] = {}

    class MixinMeta:
        """Meta for mixin."""

        MIXIN_NAME = 'Settings'

    def __init__(self, *args, **kwargs):
        """Register mixin."""
        super().__init__(*args, **kwargs)
        self.add_mixin('settings', 'has_settings', __class__)
        self.settings = getattr(self, 'SETTINGS', {})
        self.user_settings = getattr(self, 'USER_SETTINGS', {})


    @classmethod
    def _activate_mixin(cls, registry, plugins, *args, **kwargs):
        """Activate plugin settings.

        Add all defined settings form the plugins to a unified dict in the registry.
        This dict is referenced by the PluginSettings for settings definitions.
        """
        logger.debug('Activating plugin settings')

        registry.mixins_settings = {}
        registry.mixins_user_settings = {}

        for slug, plugin in plugins:
            if plugin.mixin_enabled('settings'):
                plugin_setting = plugin.settings
                registry.mixins_settings[slug] = plugin_setting
                registry.mixins_user_settings[slug] = plugin.user_settings

    @classmethod
    def _deactivate_mixin(cls, registry, **kwargs):
        """Deactivate all plugin settings."""
        logger.debug('Deactivating plugin settings')
        # clear settings cache
        registry.mixins_settings = {}
        registry.mixins_user_settings = {}

    @property
    def has_settings(self):
        """Does this plugin use custom global settings."""
        return bool(self.settings or self.user_settings)

    def get_user_setting(self, key, user):
        """Read a personal setting without creating a row for its default."""
        from plugin.models import UserPluginSetting

        if user is None or not user.is_authenticated:
            raise ValueError('An authenticated user is required')
        if key.upper() not in self.user_settings:
            raise KeyError(key)
        return UserPluginSetting.get_setting(key, plugin=self.plugin_config(), user=user, create=False)

    def get_user_settings(self, user):
        """Return the user's declared settings with effective values."""
        return {key: self.get_user_setting(key, user) for key in self.user_settings}

    def set_user_setting(self, key, value, user):
        """Validate and save a personal setting for an explicit user."""
        from plugin.models import UserPluginSetting

        if user is None or not user.is_authenticated:
            raise ValueError('An authenticated user is required')
        key = key.upper()
        if key not in self.user_settings:
            raise KeyError(key)
        plugin = self.plugin_config()
        setting = UserPluginSetting.get_setting_object(key, plugin=plugin, user=user, create=False)
        if setting is None:
            setting = UserPluginSetting(key=key, plugin=plugin, user=user)
        setting.value = str(value)
        setting.save()
        return self.get_user_setting(key, user)

    def reset_user_setting(self, key, user):
        """Remove a personal override and return its declared default."""
        from plugin.models import UserPluginSetting

        if user is None or not user.is_authenticated:
            raise ValueError('An authenticated user is required')
        key = key.upper()
        if key not in self.user_settings:
            raise KeyError(key)
        UserPluginSetting.objects.filter(plugin=self.plugin_config(), user=user, key=key).delete()
        return self.get_user_setting(key, user)

    def get_setting(self, key, cache=False, backup_value=None):
        """Return the 'value' of the setting associated with this plugin.

        Arguments:
            key: The 'name' of the setting value to be retrieved
            cache: Whether to use RAM cached value (default = False)
            backup_value: A backup value to return if the setting is not found
        """
        from plugin.models import PluginSetting

        return PluginSetting.get_setting(
            key, plugin=self.plugin_config(), cache=cache, backup_value=backup_value
        )

    def set_setting(self, key, value, user=None):
        """Set plugin setting value by key."""
        from plugin.models import PluginSetting
        from plugin.registry import registry

        try:
            plugin = registry.get_plugin_config(self.plugin_slug(), self.plugin_name())
        except (OperationalError, ProgrammingError):  # pragma: no cover
            plugin = None

        if not plugin:  # pragma: no cover
            # Cannot find associated plugin model, return
            logger.error("Plugin configuration not found for plugin '%s'", self.slug)
            return

        PluginSetting.set_setting(key, value, user, plugin=plugin)

    def check_settings(self):
        """Check if all required settings for this machine are defined.

        Warning: This method cannot be used in the __init__ function of the plugin

        Returns:
            is_valid: Are all required settings defined
            missing_settings: List of all settings that are missing (empty if is_valid is 'True')
        """
        from plugin.models import PluginSetting

        return PluginSetting.check_all_settings(
            settings_definition=self.settings, plugin=self.plugin_config()
        )
