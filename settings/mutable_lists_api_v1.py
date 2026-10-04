"""Small, explicit registry for the mutable lists in legacy Settings."""

from dataclasses import dataclass

from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError, RestrictedError
from django.http import Http404
from django.forms.models import model_to_dict
from django.utils.translation import gettext_lazy as _
from mptt.exceptions import InvalidMove
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from expense.forms import ContractTypeModelForm
from expense.models import Contract_type
from fund.forms import CostTypeModelForm
from fund.models import Cost_Type
from infos.forms import ContactInfoTypeForm, ContactTypeForm, OrganizationInfosTypeForm
from infos.models import ContactInfoType, ContactType, OrganizationInfosType
from leave.forms import LeaveTypeModelForm
from leave.models import Leave_Type
from project.forms import GenericInfoTypeProjectForm
from project.models import GenericInfoTypeProject
from staff.forms import EmployeeTypeModelForm, GenericInfoTypeForm
from staff.models import Employee_Type, GenericInfoType


GROUPS = {
    "fund": _("Fund"), "contract": _("Contract"), "leaves": _("Leaves"),
    "project": _("Project"), "staff": _("Staff"), "organization": _("Organization"),
}


@dataclass(frozen=True)
class MutableList:
    group: str
    model: type
    form: type
    columns: tuple[str, ...]
    ordering: tuple[str, ...] = ("name",)
    allow_delete: bool = False  # No active legacy Settings panel offers Delete.
    tree_column: str | None = None

    def allowed(self, user, action):
        if action == "view":
            return user.is_authenticated  # Legacy Settings lists were readable after login.
        if action == "delete" and not self.allow_delete:
            return False
        return user.has_perm(f"{self.model._meta.app_label}.{action}_{self.model._meta.model_name}")


MUTABLE_LISTS = {
    "cost-types": MutableList("fund", Cost_Type, CostTypeModelForm, ("name", "short_name", "in_focus", "is_hr"), ("tree_id", "lft"), tree_column="name"),
    "contract-types": MutableList("contract", Contract_type, ContractTypeModelForm, ("name",)),
    "leave-types": MutableList("leaves", Leave_Type, LeaveTypeModelForm, ("name", "short_name", "color"), ("tree_id", "lft"), tree_column="name"),
    "project-info-types": MutableList("project", GenericInfoTypeProject, GenericInfoTypeProjectForm, ("name", "icon")),
    "employee-types": MutableList("staff", Employee_Type, EmployeeTypeModelForm, ("name", "shortname")),
    "employee-info-types": MutableList("staff", GenericInfoType, GenericInfoTypeForm, ("name", "icon")),
    "organization-info-types": MutableList("organization", OrganizationInfosType, OrganizationInfosTypeForm, ("name", "icon", "type")),
    "contact-info-types": MutableList("organization", ContactInfoType, ContactInfoTypeForm, ("name", "icon", "type")),
    "contact-types": MutableList("organization", ContactType, ContactTypeForm, ("name",)),
}


def get_list(key, user):
    config = MUTABLE_LISTS.get(key)
    if config is None or not config.allowed(user, "view"):
        raise Http404
    return config


def capabilities(config, user, instance=None):
    form = config.form(instance=instance)
    return {
        "can_view": config.allowed(user, "view"),
        "can_add": config.allowed(user, "add"),
        "can_change": config.allowed(user, "change") and any(not field.disabled for field in form.fields.values()),
        "can_delete": config.allowed(user, "delete"),
    }


def field_data(name, field):
    if isinstance(field, forms.ModelChoiceField):
        kind = "relation"
        choices = [{"value": obj.pk, "label": str(obj)} for obj in field.queryset]
    elif isinstance(field, forms.BooleanField):
        kind, choices = "boolean", []
    elif isinstance(field, forms.TypedChoiceField) or isinstance(field, forms.ChoiceField):
        kind = "choice"
        choices = [{"value": value, "label": str(label)} for value, label in field.choices]
    elif getattr(field.widget, "input_type", None) == "color":
        kind, choices = "color", []
    else:
        kind, choices = "text", []
    return {"key": name, "label": str(field.label or name), "type": kind,
            "required": field.required, "readonly": field.disabled, "choices": choices,
            "default": field.initial if isinstance(field.initial, (str, int, bool)) else None}


def row_data(config, user, obj):
    fields = {}
    for name in config.form.base_fields:
        value = getattr(obj, name)
        fields[name] = value.pk if hasattr(value, "pk") else value
    row = {"id": obj.pk, "values": fields, "capabilities": capabilities(config, user, obj),
           "editable_fields": [name for name, field in config.form(instance=obj).fields.items() if not field.disabled]}
    if config.tree_column:
        row["tree_level"] = obj.level
    return row


def list_metadata(key, config, user):
    form = config.form()
    metadata = {"key": key, "group": config.group, "label": str(config.model._meta.verbose_name_plural),
                "columns": list(config.columns), "fields": [field_data(name, field) for name, field in form.fields.items()],
                "capabilities": capabilities(config, user)}
    if config.tree_column:
        metadata["renderers"] = {config.tree_column: "tree"}
    return metadata


def require_action(config, user, action, instance=None):
    if not capabilities(config, user, instance)[f"can_{action}"]:
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied()


def save_form(config, request, instance=None):
    initial = model_to_dict(instance, fields=config.form.base_fields) if instance else {}
    probe = config.form(instance=instance)
    editable = {name for name, field in probe.fields.items() if not field.disabled}
    if not isinstance(request.data, dict) or set(request.data) - editable:
        raise serializers.ValidationError({"detail": _("Unknown or read-only field.")})
    data = {**initial, **request.data}
    # The legacy SanitizeDataFormMixin indexes cleaned_data even for invalid fields.
    # Validate field inputs first so the existing ModelForm can safely run its clean().
    for name, field in probe.fields.items():
        if field.disabled:
            continue
        try:
            field.clean(data.get(name))
        except DjangoValidationError as error:
            raise serializers.ValidationError({name: error.messages}) from error
    form = config.form(data=data, instance=instance, request=request)
    if not form.is_valid():
        raise serializers.ValidationError(dict(form.errors))
    try:
        with transaction.atomic():
            obj = form.save(commit=False)
            obj.full_clean()
            obj.save()
            form.save_m2m()
    except DjangoValidationError as error:
        raise serializers.ValidationError(getattr(error, "message_dict", None) or error.messages) from error
    except InvalidMove as error:
        raise serializers.ValidationError({"parent": str(error)}) from error
    return obj


class MutableListsRegistryV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        groups = []
        for key, label in GROUPS.items():
            lists = [list_metadata(list_key, config, request.user) for list_key, config in MUTABLE_LISTS.items()
                     if config.group == key and config.allowed(request.user, "view")]
            if lists:
                groups.append({"key": key, "label": str(label), "lists": lists})
        return Response({"groups": groups})


class MutableListCollectionV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, list_key):
        config = get_list(list_key, request.user)
        rows = config.model.objects.order_by(*config.ordering)
        return Response({"list": list_metadata(list_key, config, request.user),
                         "rows": [row_data(config, request.user, obj) for obj in rows]})

    def post(self, request, list_key):
        config = get_list(list_key, request.user)
        require_action(config, request.user, "add")
        obj = save_form(config, request)
        return Response(row_data(config, request.user, obj), status=status.HTTP_201_CREATED)


class MutableListDetailV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def _object(self, list_key, item_id, user):
        config = get_list(list_key, user)
        try:
            return config, config.model.objects.get(pk=item_id)
        except config.model.DoesNotExist as error:
            raise Http404 from error

    def patch(self, request, list_key, item_id):
        config, obj = self._object(list_key, item_id, request.user)
        require_action(config, request.user, "change", obj)
        return Response(row_data(config, request.user, save_form(config, request, obj)))

    def delete(self, request, list_key, item_id):
        config, obj = self._object(list_key, item_id, request.user)
        require_action(config, request.user, "delete", obj)
        try:
            obj.delete()
        except (ProtectedError, RestrictedError):
            raise serializers.ValidationError({"detail": _("This item is currently used and cannot be deleted.")})
        return Response(status=status.HTTP_204_NO_CONTENT)
