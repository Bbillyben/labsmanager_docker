"""Current user's account controls using the same django-allauth forms and flows as legacy."""

from allauth.account import app_settings
from allauth.account.forms import AddEmailForm, ChangePasswordForm, SetPasswordForm
from allauth.account.internal import flows
from allauth.account.models import EmailAddress
from allauth.account.utils import send_email_confirmation, sync_user_email_addresses
from allauth.decorators import rate_limit
from allauth.utils import get_form_class
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView


def form_errors(form):
    return {key: [str(error) for error in values] for key, values in form.errors.items()}


def email_data(user):
    rows = EmailAddress.objects.filter(user=user).order_by("email")
    return {
        "can_add": EmailAddress.objects.can_add_email(user),
        "emails": [{
            "id": row.pk, "email": row.email, "verified": row.verified, "primary": row.primary,
            "can_delete": not row.primary and flows.manage_email.can_delete_email(row),
            "can_make_primary": not row.primary and flows.manage_email.can_mark_as_primary(row),
            "can_resend": not row.verified,
        } for row in rows],
    }


class UserAccountV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        sync_user_email_addresses(request.user)
        user = request.user
        return Response({
            "username": user.get_username(), "first_name": user.first_name,
            "last_name": user.last_name, "last_login": user.last_login,
            "employee": ({"id": user.employee.pk, "name": str(user.employee)}
                         if hasattr(user, "employee") else None),
            "has_usable_password": user.has_usable_password(),
            **email_data(user),
        })


@method_decorator(rate_limit(action="change_password"), name="dispatch")
@method_decorator(sensitive_post_parameters("oldpassword", "password1", "password2"), name="dispatch")
class UserPasswordV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        has_password = request.user.has_usable_password()
        key = "change_password" if has_password else "set_password"
        base = ChangePasswordForm if has_password else SetPasswordForm
        form_class = get_form_class(app_settings.FORMS, key, base)
        form = form_class(user=request.user, data=request.data)
        if not form.is_valid():
            raise serializers.ValidationError(form_errors(form))
        form.save()
        logged_out = (flows.password_change.finalize_password_change(request._request, request.user)
                      if has_password else flows.password_change.finalize_password_set(request._request, request.user))
        return Response({"saved": True, "logged_out": logged_out})


class UserEmailsV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        sync_user_email_addresses(request.user)
        return Response(email_data(request.user))

    def post(self, request):
        form_class = get_form_class(app_settings.FORMS, "add_email", AddEmailForm)
        form = form_class(user=request.user, data=request.data)
        if not form.is_valid():
            raise serializers.ValidationError(form_errors(form))
        flows.manage_email.add_email(request._request, form)
        return Response(email_data(request.user), status=201)


class UserEmailDetailV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_email(self, request, email_id):
        try:
            return EmailAddress.objects.get(pk=email_id, user=request.user)
        except EmailAddress.DoesNotExist as error:
            raise Http404 from error

    def patch(self, request, email_id):
        row = self.get_email(request, email_id)
        action = request.data.get("action")
        if action == "primary":
            if row.primary or not flows.manage_email.can_mark_as_primary(row):
                raise serializers.ValidationError({"action": "This address cannot become primary."})
            flows.manage_email.mark_as_primary(request._request, row)
        elif action == "resend":
            if row.verified:
                raise serializers.ValidationError({"action": "This address is already verified."})
            send_email_confirmation(request._request, request.user, email=row.email)
        else:
            raise serializers.ValidationError({"action": "Unknown email action."})
        return Response(email_data(request.user))

    def delete(self, request, email_id):
        row = self.get_email(request, email_id)
        if row.primary:
            raise serializers.ValidationError({"email": "A primary email address cannot be removed."})
        if not flows.manage_email.can_delete_email(row):
            raise serializers.ValidationError({"email": "This address cannot be removed."})
        flows.manage_email.delete_email(request._request, row)
        return Response(email_data(request.user))
