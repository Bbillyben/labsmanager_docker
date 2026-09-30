"""Project Settings v1: metadata from the existing declarative Settings core."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from project.models import Project

from .models import LMProjectSetting


def can_change_project_settings(user, project):
    """Apply the historical global Settings or object Project change authority."""
    return bool(
        user.has_perm("settings.change_lmprojectsetting")
        or Project.get_instances_for_user("change", user, Project.objects.filter(pk=project.pk)).exists()
    )


def project_setting_data(project, key):
    """Serialize one core definition and its effective value without creating a row."""
    definition = LMProjectSetting.get_setting_definition(key)
    if not definition:
        raise ValueError("Unknown Project setting")
    choices = LMProjectSetting.get_setting_choices(key, project=project)
    probe = LMProjectSetting(key=key, project=project)
    return {
        "key": key,
        "name": str(LMProjectSetting.get_setting_name(key, project=project)),
        "description": str(LMProjectSetting.get_setting_description(key, project=project)),
        "type": "choice" if choices is not None else probe.setting_type(),
        "value": LMProjectSetting.get_setting(key, project=project, create=False),
        "default": LMProjectSetting.get_setting_default(key, project=project),
        "choices": [{"value": value, "label": str(label)} for value, label in choices] if choices is not None else [],
    }


class ProjectSettingWriteSerializer(serializers.Serializer):
    value = serializers.JSONField()


class ProjectSettingsV1Base(APIView):
    """Resolve a visible Project before exposing or changing its Settings."""
    permission_classes = (permissions.IsAuthenticated,)

    def get_project(self, request, pk):
        visible = Project.get_instances_for_user("view", request.user, Project.objects.all())
        project = get_object_or_404(visible, pk=pk)
        if not can_change_project_settings(request.user, project):
            raise PermissionDenied()
        return project


class ProjectSettingsV1View(ProjectSettingsV1Base):
    """Expose Project Settings metadata and effective values to editors."""
    def get(self, request, pk):
        project = self.get_project(request, pk)
        return Response({"settings": [project_setting_data(project, key) for key in LMProjectSetting.SETTINGS]})


class ProjectSettingDetailV1View(ProjectSettingsV1Base):
    """Persist a single Project Setting through its model validation and hooks."""
    def patch(self, request, pk, key):
        project = self.get_project(request, pk)
        key = key.upper()
        if not LMProjectSetting.get_setting_definition(key):
            raise Http404
        serializer = ProjectSettingWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        value = serializer.validated_data["value"]
        definition = LMProjectSetting.get_setting_definition(key)
        if definition.get("validator") is bool and type(value) is not bool:
            raise serializers.ValidationError({"value": "A boolean value is required."})
        with transaction.atomic():
            setting = LMProjectSetting.get_setting_object(key, project=project, create=False)
            if setting is None:
                setting = LMProjectSetting(key=key, project=project)
            setting.value = str(value)
            try:
                setting.save()
            except DjangoValidationError as error:
                raise serializers.ValidationError(
                    getattr(error, "message_dict", None) or error.messages
                ) from error
        return Response(project_setting_data(project, key))
