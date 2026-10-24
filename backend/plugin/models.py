"""  Credit : Inventree https://github.com/inventree/InvenTree 
### Largely copyed from Inventree : https://github.com/inventree/InvenTree/blob/master/src/backend/InvenTree/plugin/models.py
"""

import inspect
import warnings

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


from settings.models import BaseLabsManagerSetting
from plugin import registry
from .plugin import LabManagerPlugin
# Create your models here.


class PluginConfig(models.Model):
    """A PluginConfig object holds settings for plugins.

    Attributes:
        key: slug of the plugin (this must be unique across all installed plugins!)
        name: PluginName of the plugin - serves for a manual double check  if the right plugin is used
        active: Should the plugin be loaded?
    """

    @staticmethod
    def get_api_url():
        """Return the API URL associated with the PluginConfig model."""
        return reverse('api-plugin-list')

    class Meta:
        """Meta for PluginConfig."""

        verbose_name = _('Plugin Configuration')
        verbose_name_plural = _('Plugin Configurations')

    key = models.CharField(
        unique=True,
        db_index=True,
        max_length=255,
        verbose_name=_('Key'),
        help_text=_('Key of plugin'),
    )

    name = models.CharField(
        null=True,
        blank=True,
        max_length=255,
        verbose_name=_('Name'),
        help_text=_('PluginName of the plugin'),
    )

    active = models.BooleanField(
        default=False, verbose_name=_('Active'), help_text=_('Is the plugin active')
    )

    def __str__(self) -> str:
        """Nice name for printing."""
        name = f'{self.name} - {self.key}'
        if not self.active:
            name += '(not active)'
        return name

    # extra attributes from the registry
    def mixins(self):
        """Returns all registered mixins."""
        try:
            if inspect.isclass(self.plugin):
                return self.plugin.get_registered_mixins(
                    self, with_base=True, with_cls=False
                )
            return self.plugin.get_registered_mixins(with_base=True, with_cls=False)
        except (AttributeError, ValueError):  # pragma: no cover
            return {}

    # functions

    def __init__(self, *args, **kwargs):
        """Override to set original state of the plugin-config instance."""
        super().__init__(*args, **kwargs)
        self.__org_active = self.active

        # Append settings from registry
        plugin = registry.plugins_full.get(self.key, None)

        def get_plugin_meta(name):
            """Return a meta-value associated with this plugin."""
            # Ignore if the plugin config is not defined
            if not plugin:
                return None

            # Ignore if the plugin is not active
            if not self.active:
                return None

            result = getattr(plugin, name, None)

            if result is not None:
                result = str(result)

            return result

        self.meta = {
            key: get_plugin_meta(key)
            for key in [
                'slug',
                'human_name',
                'description',
                'author',
                'pub_date',
                'version',
                'website',
                'license',
                'package_path',
                'settings_url',
            ]
        }

        # Save plugin
        self.plugin: LabManagerPlugin = plugin

    def __getstate__(self):
        """Customize pickling behavior."""
        state = super().__getstate__()
        state.pop(
            'plugin', None
        )  # plugin cannot be pickled in some circumstances when used with drf views, remove it (#5408)
        return state

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        """Extend save method to reload plugins if the 'active' status changes."""
        reload = kwargs.pop('no_reload', False)  # check if no_reload flag is set

        if self.active and not self.__org_active and not self.is_builtin():
            from plugin.dependencies import activation_ready
            from django.core.exceptions import ValidationError
            if not activation_ready(self.key):
                raise ValidationError({'active': 'Plugin dependencies are unavailable or require an application restart.'})

        super().save(force_insert, force_update, *args, **kwargs)

        if self.is_builtin():
            # Force active if builtin
            self.active = True

        if not reload and self.active != self.__org_active:
            if settings.PLUGIN_TESTING:
                warnings.warn('A reload was triggered', stacklevel=2)
            registry.reload_plugins()

    @admin.display(boolean=True, description=_('Installed'))
    def is_installed(self) -> bool:
        """Simple check to determine if this plugin is installed.

        A plugin might not be installed if it has been removed from the system,
        but the PluginConfig associated with it still exists.
        """
        return self.plugin is not None

    @admin.display(boolean=True, description=_('Sample plugin'))
    def is_sample(self) -> bool:
        """Is this plugin a sample app?"""
        if not self.plugin:
            return False

        return self.plugin.check_is_sample()

    @admin.display(boolean=True, description=_('Builtin Plugin'))
    def is_builtin(self) -> bool:
        """Return True if this is a 'builtin' plugin."""
        if not self.plugin:
            return False

        return self.plugin.check_is_builtin()

    @admin.display(boolean=True, description=_('Package Plugin'))
    def is_package(self) -> bool:
        """Return True if this is a 'package' plugin."""
        if not self.plugin:
            return False

        return getattr(self.plugin, 'is_package', False)

    def activate(self, active: bool) -> None:
        """Set the 'active' status of this plugin instance."""
        # from InvenTree.tasks import check_for_migrations, offload_task

        if self.active == active:
            return

        self.active = active
        self.save()

        # if active:
        #     offload_task(check_for_migrations)
        #     offload_task(plugin.staticfiles.copy_plugin_static_files, self.key)

class PluginSetting(BaseLabsManagerSetting):
    """This model represents settings for individual plugins."""

    typ = 'plugin'
    extra_unique_fields = ['plugin']

    class Meta:
        """Meta for PluginSetting."""

        unique_together = [('plugin', 'key')]

    plugin = models.ForeignKey(
        PluginConfig,
        related_name='settings',
        null=False,
        verbose_name=_('Plugin'),
        on_delete=models.CASCADE,
    )

    @classmethod
    def get_setting_definition(cls, key, **kwargs):
        """In the BaseLabsManagerSetting class, we have a class attribute named 'SETTINGS', which is a dict object that fully defines all the setting parameters.

        Here, unlike the BaseInvenTreeSetting, we do not know the definitions of all settings
        'ahead of time' (as they are defined externally in the plugins).

        Settings can be provided by the caller, as kwargs['settings'].

        If not provided, we'll look at the plugin registry to see what settings are available,
        (if the plugin is specified!)
        """
        if 'settings' not in kwargs:
            plugin = kwargs.pop('plugin', None)

            if plugin:
                mixin_settings = getattr(registry, 'mixins_settings', None)
                if mixin_settings:
                    kwargs['settings'] = mixin_settings.get(plugin.key, {})

        return super().get_setting_definition(key, **kwargs)


class UserPluginSetting(BaseLabsManagerSetting):
    """A plugin setting owned by one authenticated user."""

    typ = 'user_plugin'
    extra_unique_fields = ['plugin', 'user']

    plugin = models.ForeignKey(PluginConfig, related_name='user_settings', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='plugin_settings', on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['plugin', 'user', 'key'], name='unique_user_plugin_setting')]

    @classmethod
    def get_setting_definition(cls, key, **kwargs):
        if 'settings' not in kwargs:
            plugin = kwargs.get('plugin')
            if plugin:
                kwargs['settings'] = getattr(registry, 'mixins_user_settings', {}).get(plugin.key, {})
        return super().get_setting_definition(key, **kwargs)


class PluginAccessToken(models.Model):
    """Hashed secret for one plugin, optionally owned by one user."""

    class Kind(models.TextChoices):
        PLUGIN = 'plugin', 'Plugin'
        USER = 'user', 'User'

    plugin = models.ForeignKey(PluginConfig, related_name='access_tokens', on_delete=models.CASCADE)
    kind = models.CharField(max_length=6, choices=Kind.choices)
    user = models.ForeignKey(User, related_name='plugin_access_tokens', null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    public_id = models.CharField(max_length=64, unique=True, editable=False)
    secret_hash = models.CharField(max_length=255, editable=False)
    scopes = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Plugin token'
        verbose_name_plural = 'Plugin tokens'
        constraints = [models.CheckConstraint(
            check=(models.Q(kind='plugin', user__isnull=True) | models.Q(kind='user', user__isnull=False)),
            name='plugin_token_kind_owner',
        )]

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        if (self.kind == self.Kind.PLUGIN) != (self.user_id is None):
            raise ValidationError({'user': 'Token kind and owner are inconsistent.'})
        if not isinstance(self.scopes, list) or any(not isinstance(scope, str) for scope in self.scopes) or len(set(self.scopes)) != len(self.scopes):
            raise ValidationError({'scopes': 'Scopes must be a list of distinct names.'})
        if self.pk:
            original = type(self).objects.filter(pk=self.pk).values('plugin_id', 'kind', 'user_id', 'public_id', 'secret_hash', 'scopes', 'revoked_at').first()
            if original:
                immutable = ('plugin_id', 'kind', 'user_id', 'public_id', 'secret_hash', 'scopes')
                if any(getattr(self, field) != original[field] for field in immutable):
                    raise ValidationError('Token identity, secret and scopes cannot be changed.')
                if original['revoked_at'] is not None and self.revoked_at != original['revoked_at']:
                    raise ValidationError('Token revocation cannot be undone.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
