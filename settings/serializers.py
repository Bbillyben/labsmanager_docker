from rest_framework import serializers
from .models import LMUserSetting, LabsManagerSetting
from labsmanager.serializers_base import LabsManagerModelSerializer 

class SettingsSerializer(LabsManagerModelSerializer):
    """Base serializer for a settings object."""

    key = serializers.CharField(read_only=True)

    name = serializers.CharField(read_only=True)

    description = serializers.CharField(read_only=True)

    type = serializers.CharField(source='setting_type', read_only=True)

    choices = serializers.SerializerMethodField()

    model_name = serializers.CharField(read_only=True)

    api_url = serializers.CharField(read_only=True)
    typ = serializers.CharField(read_only=True)

    def get_choices(self, obj):
        """Returns the choices available for a given item."""
        results = []

        choices = obj.choices()

        if choices:
            for choice in choices:
                results.append({
                    'value': choice[0],
                    'display_name': choice[1],
                })

        return results

    def get_value(self, obj):
        """Make sure protected values are not returned."""
        # never return protected values
        if obj.protected:
            result = '***'
        else:
            result = obj.value

        return result
    
class UserSettingsSerializer(SettingsSerializer):
    """Serializer for the labsmanagerUserSetting model."""

    user = serializers.PrimaryKeyRelatedField(read_only=True)
    type = serializers.CharField(source='setting_type', read_only=True)
    
    class Meta:
        """Meta options for UserSettingsSerializer."""

        model = LMUserSetting
        fields = [
            'pk',
            'key',
            'value',
            'name',
            'description',
            'user',
            'type',
            'choices',
            'model_name',
            'api_url',
        ]

class ProjectSettingsSerializer(SettingsSerializer):
    """Serializer for the labsmanagerUserSetting model."""

    project = serializers.PrimaryKeyRelatedField(read_only=True)
    type = serializers.CharField(source='setting_type', read_only=True)
    
    class Meta:
        """Meta options for UserSettingsSerializer."""

        model = LMUserSetting
        fields = [
            'pk',
            'key',
            'value',
            'name',
            'description',
            'project',
            'type',
            'choices',
            'model_name',
            'api_url',
        ]

class GlobalSettingsSerializer(SettingsSerializer):
    """Serializer for the LabsManagerSetting model."""
    
    class Meta:
        """Meta options for GlobalSettingsSerializer."""

        model = LabsManagerSetting
        fields = [
            'pk',
            'key',
            'value',
            'name',
            'description',
            'type',
            'choices',
            'model_name',
            'api_url',
        ]
class GenericReferencedSettingSerializer(SettingsSerializer):
    """Serializer for a GenericReferencedSetting model.

    Args:
        MODEL: model class for the serializer
        EXTRA_FIELDS: fields that need to be appended to the serializer
            field must also be defined in the custom class
    """

    MODEL = None
    EXTRA_FIELDS = None

    def __init__(self, *args, **kwargs):
        """Init overrides the Meta class to make it dynamic."""

        class CustomMeta:
            """Scaffold for custom Meta class."""

            fields = [
                'pk',
                'key',
                'value',
                'name',
                'description',
                'type',
                'choices',
                'model_name',
                'api_url',
                'typ',
                # 'required',
            ]

        # set Meta class
        self.Meta = CustomMeta
        self.Meta.model = self.MODEL
        # extend the fields
        self.Meta.fields.extend(self.EXTRA_FIELDS)

        # resume operations
        super().__init__(*args, **kwargs)