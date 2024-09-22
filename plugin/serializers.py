
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
            # 'is_sample',
            # 'is_installed',
            # 'is_package',
        ]

        read_only_fields = ['key', 'is_builtin',
                            # 'is_sample', 'is_installed'
                            ]

    meta = serializers.DictField(read_only=True)
    mixins = serializers.DictField(read_only=True)  
    
from settings.serializers import GenericReferencedSettingSerializer
class PluginSettingSerializer(GenericReferencedSettingSerializer):
    """Serializer for the PluginSetting model."""

    MODEL = PluginSetting
    EXTRA_FIELDS = ['plugin']

    plugin = serializers.CharField(source='plugin.key', read_only=True)