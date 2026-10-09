"""Staff-owned invitation assignments; django-invitations remains the invite authority."""

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from invitations.utils import get_invitation_model
from rest_framework.exceptions import APIException

from .models import Employee, InvitationProvisioning


def eligible_employee(email, employee_id, *, lock=False):
    if employee_id is None:
        return None
    queryset = Employee.objects
    if lock:
        queryset = queryset.select_for_update()
    employee = queryset.filter(pk=employee_id, is_active=True).first()
    if employee is None or employee.user_id is not None:
        raise ValidationError({"employee_id": _("Select an active Employee without a User.")})
    if employee.email and employee.email.casefold() != email.casefold():
        raise ValidationError({"employee_id": _("The Employee email differs from the invitation email.")})
    return employee


def assignable_groups(actor, group_ids):
    if not group_ids:
        return []
    if not actor.is_superuser:
        raise ValidationError({"group_ids": _("Only a superuser can assign groups through an invitation.")})
    if len(group_ids) != len(set(group_ids)):
        raise ValidationError({"group_ids": _("Duplicate groups are not allowed.")})
    groups = list(Group.objects.filter(pk__in=group_ids).order_by("pk"))
    if len(groups) != len(group_ids):
        raise ValidationError({"group_ids": _("Select existing groups.")})
    return groups


def save_provisioning(invitation, employee, groups):
    if employee is None and not groups:
        InvitationProvisioning.objects.filter(invitation=invitation).delete()
        return
    provisioning, _ = InvitationProvisioning.objects.update_or_create(
        invitation=invitation, defaults={"employee": employee},
    )
    provisioning.groups.set(groups)


class ProvisioningConflict(APIException):
    """A selected Employee was linked after the invitation was prepared."""

    status_code = 409
    default_code = "employee_already_linked"


def apply_provisioning_for_signup(user):
    """Called after django-invitations' signup receiver accepted the invitation."""
    invitation = get_invitation_model().objects.filter(email__iexact=user.email, accepted=True).first()
    if invitation is None:
        return
    provisioning = InvitationProvisioning.objects.filter(invitation=invitation).first()
    if provisioning is None:
        return
    if provisioning.employee_id:
        employee = Employee.objects.select_for_update().get(pk=provisioning.employee_id)
        if employee.user_id is not None:
            raise ProvisioningConflict(_("The selected Employee is already linked to a User."))
        employee.user = user
        employee.save(update_fields=["user"])
    groups = list(provisioning.groups.all())
    if groups:
        user.groups.add(*groups)


def validate_pending_employee(invitation):
    provisioning = InvitationProvisioning.objects.filter(invitation=invitation).first()
    if provisioning and provisioning.employee_id:
        eligible_employee(invitation.email, provisioning.employee_id, lock=True)


from allauth.account.views import SignupView


class AtomicInvitationSignupView(SignupView):
    """Keep the legacy allauth form while making invited signup atomic."""

    @transaction.atomic
    def form_valid(self, form):
        email = self.request.session.get("account_verified_email")
        if email:
            invitation = get_invitation_model().objects.select_for_update().filter(email__iexact=email).first()
            if invitation is None or invitation.accepted or not invitation.sent or invitation.key_expired():
                form.add_error(None, _("This invitation is no longer valid."))
                return self.form_invalid(form)
            try:
                validate_pending_employee(invitation)
            except ValidationError as error:
                form.add_error(None, error.messages[0])
                return self.form_invalid(form)
        try:
            return super().form_valid(form)
        except ProvisioningConflict as error:
            form.add_error(None, str(error.detail))
            response = self.form_invalid(form)
            transaction.set_rollback(True)
            return response
