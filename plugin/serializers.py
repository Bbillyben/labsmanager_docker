
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from plugin.models import PluginConfig, PluginSetting

class PluginConfigSerializer(serializers.ModelSerializer):
    """Serializer for a PluginConfig."""

    class Meta:
        """Meta for serializer."""

        model = PluginConfig
        fields = [
            'pk',
            'key',
            'name',
            # 'package_name',
            'active',
            'meta',
            'mixins',
            'is_builtin',
            'is_sample',
            # 'is_installed',
            # 'is_package',
        ]

        read_only_fields = ['key', 'is_builtin',
                            'is_sample', 
                            # 'is_installed'
                            ]

    meta = serializers.DictField(read_only=True)
    mixins = serializers.DictField(read_only=True)  
    
from settings.serializers import GenericReferencedSettingSerializer
class PluginSettingSerializer(GenericReferencedSettingSerializer):
    """Serializer for the PluginSetting model."""

    MODEL = PluginSetting
    EXTRA_FIELDS = ['plugin']

    plugin = serializers.CharField(source='plugin.key', read_only=True)

class PluginReloadSerializer(serializers.Serializer):
    """Serializer for remotely forcing plugin registry reload."""

    class Meta:
        """Meta for serializer."""

        fields = ['full_reload', 'force_reload', 'collect_plugins']

    full_reload = serializers.BooleanField(
        required=False,
        default=False,
        label=_('Full reload'),
        help_text=_('Perform a full reload of the plugin registry'),
    )

    force_reload = serializers.BooleanField(
        required=False,
        default=False,
        label=_('Force reload'),
        help_text=_(
            'Force a reload of the plugin registry, even if it is already loaded'
        ),
    )

    collect_plugins = serializers.BooleanField(
        required=False,
        default=False,
        label=_('Collect plugins'),
        help_text=_('Collect plugins and add them to the registry'),
    )

    def save(self):
        """Reload the plugin registry."""
        from plugin.registry import registry

        registry.reload_plugins(
            full_reload=self.validated_data.get('full_reload', False),
            force_reload=self.validated_data.get('force_reload', False),
            collect=self.validated_data.get('collect_plugins', False),
        )

class PluginActivateSerializer(serializers.Serializer):
    """Serializer for activating or deactivating a plugin."""

    model = PluginConfig

    class Meta:
        """Metaclass for serializer."""

        fields = ['active']

    active = serializers.BooleanField(
        required=False,
        default=True,
        label=_('Activate Plugin'),
        help_text=_('Activate this plugin'),
    )

    def update(self, instance, validated_data):
        """Apply the new 'active' value to the plugin instance."""
        instance.activate(validated_data.get('active', True))
        return instance