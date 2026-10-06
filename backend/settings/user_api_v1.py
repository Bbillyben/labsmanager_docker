"""Typed, current-user-only Settings API backed by LMUserSetting."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import Http404
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LMUserSetting


USER_SETTING_GROUPS = {
    "interface": (
        "REDIRECT_LOGGING", "SHOW_PAST_ORG", "MAP_PROVIDER", "LAB_THEME",
    ),
    "notifications": (
        "NOTIFCATION_STATUS", "NOTIFCATION_REPORT_LANGUAGE",
        "NOTIFICATION_ENDPOINTS_MILESTONES", "NOTIFICATION_ENDPOINTS_MILESTONES_STALE",
        "NOTIFICATION_ENDPOINTS_MILESTONES_REPEAT",
        "NOTIFICATION_ENDPOINTS_MILESTONES_REPORT_REPEAT",
        "NOTIFICATION_ENDPOINTS_MILESTONES_REPORT_HORIZON",
        "NOTIFICATION_PROJECT_PARTICIPANT", "NOTIFICATION_STAFF_EMPLOYEE",
        "NOTIFCATION_FREQ", "NOTIFCATION_EMP_INCOMMING", "NOTIFCATION_INC_LEAVE",
        "NOTIFCATION_SUB_MILESTONES", "NOTIFCATION_LEAVE_FORMAT",
        "NOTIFCATION_LEAVE_REPORT_NONE", "NOTIFCATION_LEAVE_TIMEFRAME",
    ),
    "stale": (
        "DASHBOARD_CONTRACT_STALE_TO_MONTH", "DASHBOARD_PROJECT_STALE_TO_MONTH",
    ),
}


def user_setting_data(user, key):
    """Expose the effective value and the model's own metadata without creating a row."""
    choices = LMUserSetting.get_setting_choices(key, user=user)
    probe = LMUserSetting(key=key, user=user)
    return {
        "key": key,
        "name": str(LMUserSetting.get_setting_name(key, user=user)),
        "description": str(LMUserSetting.get_setting_description(key, user=user)),
        "type": "choice" if choices is not None else probe.setting_type(),
        "value": LMUserSetting.get_setting(key, user=user, create=False),
        "default": LMUserSetting.get_setting_default(key, user=user),
        "choices": [{"value": str(value), "label": str(label)} for value, label in choices] if choices is not None else [],
        "can_change": True,
    }


class UserSettingsV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, section):
        if section not in USER_SETTING_GROUPS:
            raise Http404
        return Response({"settings": [user_setting_data(request.user, key) for key in USER_SETTING_GROUPS[section]]})


class UserSettingDetailV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def patch(self, request, section, key):
        key = key.upper()
        if section not in USER_SETTING_GROUPS or key not in USER_SETTING_GROUPS[section]:
            raise Http404
        if not isinstance(request.data, dict) or set(request.data) != {"value"}:
            raise serializers.ValidationError({"value": "Expected one value."})
        value = request.data["value"]
        choices = LMUserSetting.get_setting_choices(key, user=request.user)
        probe = LMUserSetting(key=key, user=request.user)
        kind = "choice" if choices is not None else probe.setting_type()
        if kind == "boolean" and type(value) is not bool:
            raise serializers.ValidationError({"value": "A boolean value is required."})
        if kind == "integer" and (type(value) is not int):
            raise serializers.ValidationError({"value": "An integer value is required."})
        if kind in ("choice", "string") and not isinstance(value, str):
            raise serializers.ValidationError({"value": "A string value is required."})
        with transaction.atomic():
            setting = LMUserSetting.get_setting_object(key, user=request.user, create=False)
            if setting is None:
                setting = LMUserSetting(key=key, user=request.user)
            setting.value = str(value)
            try:
                setting.save()
            except DjangoValidationError as error:
                raise serializers.ValidationError(getattr(error, "message_dict", None) or error.messages) from error
        return Response(user_setting_data(request.user, key))
