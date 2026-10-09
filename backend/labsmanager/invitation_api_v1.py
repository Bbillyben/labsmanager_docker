"""React presentation of the existing django-invitations/allauth signup flow."""

from allauth.account import app_settings as account_settings
from allauth.account.adapter import get_adapter
from allauth.account.forms import SignupForm
from allauth.account.utils import complete_signup, filter_users_by_email
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.utils import get_form_class
from django.db import transaction
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from invitations.adapters import get_invitations_adapter
from invitations.utils import get_invitation_model
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from staff.invitation_provisioning import ProvisioningConflict, validate_pending_employee

from .react_urls import react_public_url


INVITATION_SESSION_KEY = "react_invitation_key"


def _clear_invitation_session(request):
    request.session.pop(INVITATION_SESSION_KEY, None)
    request.session.pop("account_verified_email", None)


def _invitation_state(invitation):
    if invitation is None:
        return "invalid"
    if invitation.accepted:
        return "accepted"
    if not invitation.sent or invitation.key_expired():
        return "expired"
    if filter_users_by_email(invitation.email):
        return "account_exists"
    return "valid"


def _state_response(state):
    return Response({"state": state}, status=400 if state == "invalid" else 409,
                    headers={"Cache-Control": "no-store"})


def _signup_contract(invitation):
    form_class = get_form_class(account_settings.FORMS, "signup", SignupForm)
    form = form_class()
    return {
        "state": "valid",
        "email": invitation.email,
        "fields": {
            "username": "username" in form.fields,
            "password2": "password2" in form.fields,
        },
        "password_hints": password_validation.password_validators_help_texts(),
    }


@method_decorator(csrf_protect, name="dispatch")
@method_decorator(never_cache, name="dispatch")
@method_decorator(sensitive_post_parameters("token"), name="dispatch")
class InvitationBridgeV1View(APIView):
    """Exchange the emailed secret once for server-side session state."""

    permission_classes = [AllowAny]

    def post(self, request):
        if request.user.is_authenticated:
            return _state_response("authenticated")
        token = request.data.get("token") if isinstance(request.data, dict) else None
        if not isinstance(token, str) or len(token) != 64:
            return _state_response("invalid")
        invitation = get_invitation_model().objects.filter(key=token.lower()).first()
        state = _invitation_state(invitation)
        if state != "valid":
            _clear_invitation_session(request)
            return _state_response(state)
        request.session[INVITATION_SESSION_KEY] = invitation.key
        get_invitations_adapter().stash_verified_email(request._request, invitation.email)
        return Response(_signup_contract(invitation), headers={"Cache-Control": "no-store"})


@method_decorator(csrf_protect, name="dispatch")
@method_decorator(never_cache, name="dispatch")
@method_decorator(sensitive_post_parameters("password1", "password2"), name="dispatch")
class InvitationSignupV1View(APIView):
    """Validate and finalize signup through the configured allauth form."""

    permission_classes = [AllowAny]

    def _current(self, request, *, lock=False):
        key = request.session.get(INVITATION_SESSION_KEY)
        queryset = get_invitation_model().objects
        if lock:
            queryset = queryset.select_for_update()
        invitation = queryset.filter(key=key).first() if key else None
        state = _invitation_state(invitation)
        if state != "valid":
            _clear_invitation_session(request)
        return invitation, state

    def get(self, request):
        if request.user.is_authenticated:
            return _state_response("authenticated")
        invitation, state = self._current(request)
        if state != "valid":
            return _state_response(state)
        return Response(_signup_contract(invitation), headers={"Cache-Control": "no-store"})

    @transaction.atomic
    def post(self, request):
        if request.user.is_authenticated:
            return _state_response("authenticated")
        invitation, state = self._current(request, lock=True)
        if state != "valid":
            return _state_response(state)
        if request.session.get("account_verified_email", "").lower() != invitation.email.lower():
            _clear_invitation_session(request)
            return _state_response("invalid")
        try:
            validate_pending_employee(invitation)
        except DjangoValidationError as error:
            raise ProvisioningConflict(error.messages[0]) from error
        if not isinstance(request.data, dict) or ("email" in request.data and request.data["email"].lower() != invitation.email.lower()):
            return Response({"email": ["Invitation email cannot be changed."]}, status=400)
        adapter = get_adapter(request._request)
        if not adapter.is_open_for_signup(request._request):
            return _state_response("invalid")
        form_class = get_form_class(account_settings.FORMS, "signup", SignupForm)
        payload = {field: request.data.get(field, "") for field in ("username", "password1", "password2")}
        payload["email"] = invitation.email
        payload["email2"] = invitation.email
        form = form_class(data=payload)
        if not form.is_valid():
            return Response(form.errors, status=400, headers={"Cache-Control": "no-store"})
        user, response = form.try_save(request._request)
        if user is None:
            return _state_response("account_exists")
        try:
            response = response or complete_signup(
                request._request, user, email_verification=None,
                success_url=react_public_url(""),
            )
        except ImmediateHttpResponse as error:
            response = error.response
        _clear_invitation_session(request)
        return Response({
            "state": "complete",
            "authenticated": request._request.user.is_authenticated,
            "redirect_url": response.get("Location") if response is not None else None,
        }, headers={"Cache-Control": "no-store"})
