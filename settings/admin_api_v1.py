"""Staff-only Settings administration backed by the existing models and services."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from invitations.utils import get_invitation_model
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from notification.models import UserNotification
from notification.tasks import send_pending_notification
from notification.utils import check_overdue_milestones, check_overload_employee, check_stale_milestones
from plugin.models import PluginSetting
from plugin.registry import registry
from staff.models import Employee

from .models import LabsManagerSetting
from .forms import labInviteForm


GENERAL_KEYS = (
    "MAIL_OBJECT_PREFIX", "EMPLOYEE_CAN_EDIT_SUBORDINATE",
    "CO_LEADER_CAN_EDIT_PROJECT", "AUDIT_LOG_RETENTION", "NEW_EMPLOYEE_CASSE",
)
PLUGIN_KEYS = (
    "ENABLE_PLUGINS_SCHEDULE", "ENABLE_PLUGINS_URL",
    "ENABLE_PLUGINS_CALENDAR", "ENABLE_PLUGINS_SUBSCRIPTION",
)


def setting_data(model, key, **context):
    choices = model.get_setting_choices(key, **context)
    definition = model.get_setting_definition(key, **context)
    probe = model(key=key, **context)
    return {
        "key": key,
        "name": str(model.get_setting_name(key, **context)),
        "description": str(model.get_setting_description(key, **context)),
        "units": str(model.get_setting_units(key, **context) or ""),
        "type": "choice" if choices is not None else probe.setting_type(),
        "value": model.get_setting(key, create=False, **context),
        "default": model.get_setting_default(key, **context),
        "choices": [{"value": str(value), "label": str(label)} for value, label in choices] if choices is not None else [],
        "can_change": True,
        "hidden": bool(definition.get("hidden", False)),
    }


def save_setting(model, key, value, **context):
    choices = model.get_setting_choices(key, **context)
    kind = "choice" if choices is not None else model(key=key, **context).setting_type()
    if kind == "boolean" and type(value) is not bool:
        raise serializers.ValidationError({"value": "A boolean value is required."})
    if kind == "integer" and type(value) is not int:
        raise serializers.ValidationError({"value": "An integer value is required."})
    if kind in ("choice", "string") and not isinstance(value, str):
        raise serializers.ValidationError({"value": "A string value is required."})
    with transaction.atomic():
        instance = model.get_setting_object(key, create=False, **context) or model(key=key, **context)
        instance.value = str(value)
        try:
            instance.save()
        except DjangoValidationError as error:
            raise serializers.ValidationError(getattr(error, "message_dict", None) or error.messages) from error
    return setting_data(model, key, **context)


class StaffView(APIView):
    permission_classes = (permissions.IsAdminUser,)


class AdminSettings(StaffView):
    def get(self, request, section):
        keys = {"general": GENERAL_KEYS, "plugins": PLUGIN_KEYS}.get(section)
        if keys is None:
            raise Http404
        return Response({"settings": [setting_data(LabsManagerSetting, key) for key in keys]})


class AdminSettingDetail(StaffView):
    def patch(self, request, section, key):
        keys = {"general": GENERAL_KEYS, "plugins": PLUGIN_KEYS}.get(section)
        key = key.upper()
        if keys is None or key not in keys:
            raise Http404
        if not isinstance(request.data, dict) or set(request.data) != {"value"}:
            raise serializers.ValidationError({"value": "Expected one value."})
        return Response(save_setting(LabsManagerSetting, key, request.data["value"]))


def user_data(user):
    employee = getattr(user, "employee", None)
    return {"id": user.pk, "username": user.username, "name": user.get_full_name(),
            "last_login": user.last_login, "is_active": user.is_active, "is_staff": user.is_staff,
            "employee": {"id": employee.pk, "name": employee.user_name} if employee else None}


class AdminUsers(StaffView):
    def get(self, request):
        users = get_user_model().objects.select_related("employee").order_by("username")
        return Response({"results": [user_data(user) for user in users]})


class AdminUserEmployee(StaffView):
    def patch(self, request, pk):
        if not isinstance(request.data, dict) or set(request.data) != {"employee_id"}:
            raise serializers.ValidationError({"employee_id": "Expected an Employee id or null."})
        employee_id = request.data["employee_id"]
        if employee_id is not None and (type(employee_id) is not int or employee_id <= 0):
            raise serializers.ValidationError({"employee_id": "A valid Employee id is required."})
        with transaction.atomic():
            user = get_object_or_404(get_user_model().objects.select_for_update(), pk=pk)
            current = Employee.objects.select_for_update().filter(user=user).first()
            target = get_object_or_404(Employee.objects.select_for_update(), pk=employee_id) if employee_id else None
            if target and target.user_id not in (None, user.pk):
                raise serializers.ValidationError({"employee_id": "This Employee is already linked to another User."})
            if current and current != target:
                current.user = None
                current.save(update_fields=["user"])
            if target and target.user_id != user.pk:
                target.user = user
                try:
                    target.save(update_fields=["user"])
                except IntegrityError as error:
                    raise serializers.ValidationError({"employee_id": "This Employee is already linked."}) from error
        return Response(user_data(get_user_model().objects.select_related("employee").get(pk=pk)))


class AdminEmployeeOptions(StaffView):
    def get(self, request):
        employees = Employee.objects.filter(is_active=True, user__isnull=True).order_by("last_name", "first_name")
        return Response({"results": [{"id": item.pk, "name": item.user_name} for item in employees]})


def invitation_data(invitation):
    return {
        "id": invitation.pk,
        "email": invitation.email,
        "created": invitation.created,
        "sent": invitation.sent,
        "accepted": invitation.accepted,
        "key_expired": invitation.key_expired() if invitation.sent else False,
        "inviter": {"id": invitation.inviter_id, "username": invitation.inviter.username} if invitation.inviter_id else None,
    }


class AdminInvitations(StaffView):
    def get(self, request):
        invitations = get_invitation_model().objects.select_related("inviter").order_by("-created", "-pk")
        return Response({"results": [invitation_data(item) for item in invitations]})

    def post(self, request):
        if not isinstance(request.data, dict) or set(request.data) != {"email"}:
            raise serializers.ValidationError({"email": "An e-mail address is required."})
        form = labInviteForm(data=request.data)
        if not form.is_valid():
            raise serializers.ValidationError(form.errors)
        email = form.cleaned_data["email"]
        with transaction.atomic():
            invitation = form.save(email)
            invitation.inviter = request.user
            invitation.save()
            try:
                invitation.send_invitation(request)
            except Exception as error:
                raise serializers.ValidationError({"email": "The invitation could not be sent."}) from error
        return Response(invitation_data(invitation), status=201)


class AdminRemoveExpiredInvitations(StaffView):
    def post(self, request):
        invitation_model = get_invitation_model()
        with transaction.atomic():
            count = invitation_model.objects.all_expired().count()
            invitation_model.objects.delete_expired_confirmations()
        return Response({"deleted": count})


def pending_data():
    rows = UserNotification.objects.filter(send__isnull=True).select_related("user", "source_content_type").order_by("creation")
    return [{"id": row.pk, "user": row.user.username, "source_type": str(row.source_content_type) if row.source_content_type else "",
             "action": row.get_action_type_display(), "object": str(row.source_object) if row.source_object else "",
             "created": row.creation} for row in rows]


class AdminNotifications(StaffView):
    def get(self, request):
        return Response({"results": pending_data()})


class AdminNotificationAction(StaffView):
    def post(self, request, action):
        if action == "check":
            counts = {"stale": check_stale_milestones(), "overdue": check_overdue_milestones(), "overload": check_overload_employee()}
            return Response({"counts": counts, "results": pending_data()})
        if action == "send":
            sent = send_pending_notification()
            return Response({"sent": sent, "results": pending_data()})
        raise Http404


def plugin_data(key, plugin):
    return {"key": key, "human_name": str(plugin.human_name), "description": str(plugin.description),
            "author": str(plugin.author), "pub_date": plugin.pub_date, "version": plugin.version,
            "website": plugin.website, "license": plugin.license,
            "mixins": list(plugin.get_registered_mixins(with_cls=False))}


def plugin_errors():
    return [{"stage": str(stage), "name": str(name), "message": str(message)}
            for stage, errors in registry.errors.items() for entry in errors for name, message in entry.items()]


class AdminPlugins(StaffView):
    def get(self, request):
        return Response({"results": [plugin_data(key, plugin) for key, plugin in registry.plugins.items()],
                         "errors": plugin_errors()})


class AdminPluginReload(StaffView):
    def post(self, request):
        registry.reload_plugins(full_reload=True, force_reload=True, collect=True)
        return AdminPlugins().get(request)


def plugin_or_404(key):
    plugin = registry.get_plugin(key)
    if plugin is None:
        raise Http404
    return plugin


class AdminPluginDetail(StaffView):
    def get(self, request, key):
        plugin = plugin_or_404(key)
        data = plugin_data(key, plugin)
        sections = {}
        if plugin.mixin_enabled("settings"):
            config = registry.get_plugin_config(key)
            definitions = registry.mixins_settings.get(key, {})
            sections["settings"] = [setting_data(PluginSetting, name, plugin=config) for name, definition in definitions.items() if not definition.get("hidden")]
        if plugin.mixin_enabled("schedule"):
            from django_q.models import Schedule
            names = plugin.get_task_names()
            sections["schedule"] = [{"name": task.name, "function": task.func, "schedule_type": task.schedule_type,
                                      "repeat": task.repeats, "next_run": task.next_run, "success": bool(task.success())}
                                     for task in Schedule.objects.filter(name__in=names)]
        if plugin.mixin_enabled("urls"):
            base = "/" + plugin.base_url.strip("/") + "/"
            sections["urls"] = {"base_url": base, "routes": [
                {"name": str(pattern.name or ""), "url": str(pattern.pattern),
                 "href": base + str(pattern.pattern) if "<" not in str(pattern.pattern) else None}
                for pattern in plugin.urls or [] if hasattr(pattern, "pattern")
            ]}
        data["sections"] = sections
        return Response(data)


class AdminPluginSetting(StaffView):
    def patch(self, request, key, setting_key):
        plugin = plugin_or_404(key)
        if not plugin.mixin_enabled("settings"):
            raise Http404
        config = registry.get_plugin_config(key)
        definition = registry.mixins_settings.get(key, {}).get(setting_key.upper())
        if not config or not definition or definition.get("hidden"):
            raise Http404
        if not isinstance(request.data, dict) or set(request.data) != {"value"}:
            raise serializers.ValidationError({"value": "Expected one value."})
        return Response(save_setting(PluginSetting, setting_key.upper(), request.data["value"], plugin=config))
