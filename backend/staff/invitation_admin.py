"""LabsManager fields on the existing django-invitations Admin workflow."""

from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from invitations.admin import InvitationAdmin as BaseInvitationAdmin
from invitations.forms import InvitationAdminAddForm, InvitationAdminChangeForm
from invitations.utils import get_invitation_model

from .invitation_provisioning import eligible_employee, save_provisioning
from .models import Employee, InvitationProvisioning


class ProvisioningFields:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.was_accepted = bool(self.instance.pk and self.instance.accepted)
        provisioning = InvitationProvisioning.objects.filter(invitation=self.instance).first() if self.instance.pk else None
        selected_id = provisioning.employee_id if provisioning else None
        self.fields["employee"].queryset = Employee.objects.filter(is_active=True).filter(
            Q(user__isnull=True) | Q(pk=selected_id)
        ).order_by("last_name", "first_name")
        if selected_id:
            self.fields["employee"].initial = selected_id
        if self.request.user.is_superuser:
            self.fields["groups"].queryset = Group.objects.order_by("name")
            if provisioning:
                self.fields["groups"].initial = provisioning.groups.values_list("pk", flat=True)
        else:
            self.fields.pop("groups")
        if self.was_accepted:
            self.fields["employee"].disabled = True
            if "groups" in self.fields:
                self.fields["groups"].disabled = True

    def clean(self):
        data = super().clean()
        if self.was_accepted:
            return data
        employee = data.get("employee")
        if employee:
            try:
                eligible_employee(data.get("email") or self.instance.email, employee.pk)
            except ValidationError as error:
                self.add_error("employee", error.messages[0])
        return data


class LabsInvitationAddForm(ProvisioningFields, InvitationAdminAddForm):
    employee = forms.ModelChoiceField(queryset=Employee.objects.none(), required=False, label=_("Employee"))
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.none(), required=False, label=_("Groups"))

    def save(self, commit=True):
        # Package form sends before Admin saves related fields. Defer sending
        # until the provisioning has been saved in save_related().
        self.instance = get_invitation_model().create(
            self.cleaned_data["email"], inviter=self.cleaned_data.get("inviter") or self.request.user,
        )
        self.save_m2m = lambda: None
        return self.instance


class LabsInvitationChangeForm(ProvisioningFields, InvitationAdminChangeForm):
    employee = forms.ModelChoiceField(queryset=Employee.objects.none(), required=False, label=_("Employee"))
    groups = forms.ModelMultipleChoiceField(queryset=Group.objects.none(), required=False, label=_("Groups"))


class LabsInvitationAdmin(BaseInvitationAdmin):
    def get_form(self, request, obj=None, **kwargs):
        kwargs["form"] = LabsInvitationChangeForm if obj else LabsInvitationAddForm
        form = admin.ModelAdmin.get_form(self, request, obj, **kwargs)
        form.request = request
        return form

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        invitation = form.instance
        if form.was_accepted or invitation.accepted:
            return
        employee = form.cleaned_data.get("employee")
        if employee:
            employee = eligible_employee(invitation.email, employee.pk, lock=True)
        previous = InvitationProvisioning.objects.filter(invitation=invitation).first()
        groups = form.cleaned_data.get("groups") if request.user.is_superuser else previous.groups.all() if previous else []
        save_provisioning(invitation, employee, groups)
        if not change:
            invitation.send_invitation(request)
