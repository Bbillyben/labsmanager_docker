from allauth.account.forms import LoginForm
from allauth.account.forms import ResetPasswordForm, ResetPasswordKeyForm, UserTokenForm
from allauth.account import app_settings
from allauth.account.internal import flows
from allauth.utils import get_form_class
from allauth.core import ratelimit
from allauth.core.exceptions import ImmediateHttpResponse
from django.contrib.auth import logout
from django.conf import settings
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib import admin
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from staff.models import Employee
from settings.models import LMUserSetting

RESET_SESSION_UID = "react_password_reset_uid"
RESET_SESSION_KEY = "react_password_reset_key"


def _reset_token_form(uid, key):
    """Use the configured allauth token form for both bridge and confirmation."""
    form_class = get_form_class(app_settings.FORMS, "user_token", UserTokenForm)
    return form_class(data={"uidb36": uid, "key": key})


def _reset_user(request, uid):
    """Resolve a session-bound reset token without exposing the user to React."""
    key = request.session.get(RESET_SESSION_KEY, "")
    if request.session.get(RESET_SESSION_UID) != uid or not key:
        return None
    form = _reset_token_form(uid, key)
    return form.reset_user if form.is_valid() else None


CAPABILITY_PERMISSIONS = {
    "view_employee_list": ("common.employee_list", "staff.view_employee"),
    "view_team_list": ("common.team_list", "staff.view_team"),
    "view_contract_list": ("common.contract_list", "expense.view_contract"),
    "view_project_list": ("common.project_list", "project.view_project"),
    "view_organizations": ("common.display_infos",),
    "view_calendar": ("common.display_calendar", "leave.view_leave"),
    "view_dashboard": ("common.display_dashboard",),
    "use_fund_finder": ("fund.view_fund",),
    "import_data": ("common.import",),
}


def get_user_capabilities(user):
    """Compute the frontend capabilities backed by existing Django permissions.

    Capabilities are presentation hints for the SPA, not authorization
    decisions. Every protected endpoint must continue to enforce its own
    permissions and object visibility.

    Args:
        user: Authenticated Django user whose permissions are evaluated.

    Returns:
        dict[str, bool]: Functional capability names mapped to permission
        results.
    """
    from data_consistency.permissions import can_manage_consistency
    return {
        capability: any(user.has_perm(permission) for permission in permissions)
        for capability, permissions in CAPABILITY_PERMISSIONS.items()
    } | {"manage_data_consistency": can_manage_consistency(user)}


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CurrentUserView(APIView):
    """Expose the minimal session state required to bootstrap the SPA.

    Anonymous callers receive only an authentication-state flag so the
    frontend can redirect to login. Authenticated callers receive their
    identity and UI capabilities. The view deliberately allows anonymous
    access and ensures Django emits the CSRF cookie needed by later
    session-authenticated unsafe requests.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Return the current anonymous or authenticated session contract.

        Args:
            request: DRF request carrying the Django session user.

        Returns:
            Response: Minimal anonymous state or authenticated user bootstrap
            data.
        """
        user = request.user

        if not user.is_authenticated:
            return Response({"is_authenticated": False})

        employee = (
            Employee.objects.filter(user=user)
            .values("id", "first_name", "last_name")
            .first()
        )

        return Response(
            {
                "id": user.pk,
                "username": user.get_username(),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "is_authenticated": True,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "employee": employee,
                "capabilities": get_user_capabilities(user),
                "can_access_admin": admin.site.has_permission(request),
                "admin_url": reverse("admin:index") if admin.site.has_permission(request) else None,
                "theme": LMUserSetting.get_setting("LAB_THEME", user=user, create=False),
            }
        )


def _authentication_error(code, message, status_code):
    """Build the stable, non-enumerating authentication error contract.

    Args:
        code: Stable machine-readable error identifier.
        message: Generic user-facing message.
        status_code: HTTP status returned by the API.

    Returns:
        Response: Anonymous authentication state and error details.
    """
    return Response(
        {"is_authenticated": False, "error": {"code": code, "message": message}},
        status=status_code,
    )


@method_decorator(csrf_protect, name="dispatch")
@method_decorator(sensitive_post_parameters("password"), name="dispatch")
class LoginV1View(APIView):
    """Create a Django session through the existing django-allauth policy.

    The configured Allauth form preserves username/email authentication,
    backends, session expiry and failed-login rate limiting. CSRF is required
    for anonymous callers and failures never disclose account state.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        """Validate credentials and establish the session cookie.

        Args:
            request: DRF request containing ``login`` and ``password``.

        Returns:
            Response: Authenticated state, a generic credential error, or a
            rate-limit error.
        """
        django_request = request._request
        if django_request.user.is_authenticated:
            return Response({"is_authenticated": True})
        if not ratelimit.consume(django_request, action="login"):
            return _authentication_error(
                "too_many_attempts",
                "Trop de tentatives de connexion. Réessayez plus tard.",
                429,
            )
        form = LoginForm(data=request.data, request=django_request)
        if not form.is_valid():
            error_codes = {
                error.code
                for errors in form.errors.as_data().values()
                for error in errors
            }
            if "too_many_login_attempts" in error_codes:
                return _authentication_error(
                    "too_many_attempts",
                    "Trop de tentatives de connexion. Réessayez plus tard.",
                    429,
                )
            return _authentication_error(
                "invalid_credentials",
                "Identifiant ou mot de passe incorrect.",
                400,
            )
        try:
            form.login(django_request)
        except ImmediateHttpResponse:
            return _authentication_error(
                "invalid_credentials",
                "Identifiant ou mot de passe incorrect.",
                400,
            )
        if not django_request.user.is_authenticated:
            return _authentication_error(
                "invalid_credentials",
                "Identifiant ou mot de passe incorrect.",
                400,
            )
        return Response({"is_authenticated": True})


@method_decorator(csrf_protect, name="dispatch")
class LogoutV1View(APIView):
    """End the current Django session through a CSRF-protected POST.

    Logout is idempotent for anonymous callers and keeps Django authoritative
    for session and cookie lifecycle.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Clear the current session and return the anonymous state.

        Args:
            request: DRF request carrying the optional Django session.

        Returns:
            Response: Minimal anonymous authentication state.
        """
        logout(request._request)
        return Response({"is_authenticated": False})


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetRequestV1View(APIView):
    """Request an allauth email without disclosing account existence."""
    permission_classes = [AllowAny]

    def post(self, request):
        if not settings.REACT_PUBLIC_URL.strip():
            return Response({"detail": "React public URL is not configured."}, status=503)
        email = request.data.get("email") if isinstance(request.data, dict) else None
        if not isinstance(email, str):
            return Response({"email": ["A valid email address is required."]}, status=400)
        try:
            validate_email(email)
        except ValidationError:
            return Response({"email": ["A valid email address is required."]}, status=400)
        form_class = get_form_class(app_settings.FORMS, "reset_password", ResetPasswordForm)
        form = form_class(data=request.data)
        if not form.is_valid():
            # Do not disclose whether the address belongs to an account.
            return Response({"sent": True})
        if not ratelimit.consume(request._request, action="reset_password", key=form.cleaned_data["email"].lower()):
            return Response({"detail": "Too many requests."}, status=429)
        request._request.react_password_reset = True
        form.save(request._request)
        return Response({"sent": True})


class PasswordResetBridgeV1View(APIView):
    """Exchange an emailed token for session-bound reset state."""
    permission_classes = [AllowAny]

    def get(self, request, key):
        if not ratelimit.consume(request._request, action="reset_password_from_key"):
            return Response({"detail": "Too many requests."}, status=429)
        uid, separator, token = key.partition("-")
        user = None
        if separator:
            form = _reset_token_form(uid, token)
            if form.is_valid():
                user = form.reset_user
        if user:
            if request.user.is_authenticated and request.user.pk != user.pk:
                logout(request._request)
            request.session[RESET_SESSION_UID] = uid
            request.session[RESET_SESSION_KEY] = token
            return Response({"valid": True, "uid": uid}, headers={"Cache-Control": "no-store"})
        else:
            request.session.pop(RESET_SESSION_UID, None)
            request.session.pop(RESET_SESSION_KEY, None)
            return Response({"valid": False}, status=400, headers={"Cache-Control": "no-store"})


class PasswordResetConfirmV1View(APIView):
    """Expose validator hints and save through the configured allauth reset form."""
    permission_classes = [AllowAny]

    def get(self, request, uid):
        if not ratelimit.consume(request._request, action="reset_password_from_key"):
            return Response({"detail": "Too many requests."}, status=429)
        if not _reset_user(request, uid):
            return Response({"valid": False}, status=400)
        return Response({"valid": True, "password_hints": password_validation.password_validators_help_texts()})

    def post(self, request, uid):
        user = _reset_user(request, uid)
        if user is None:
            return Response({"valid": False}, status=400)
        if not ratelimit.consume(request._request, action="reset_password_from_key"):
            return Response({"detail": "Too many requests."}, status=429)
        form_class = get_form_class(app_settings.FORMS, "reset_password_from_key", ResetPasswordKeyForm)
        form = form_class(data=request.data, user=user, temp_key=request.session[RESET_SESSION_KEY])
        if not form.is_valid():
            return Response(form.errors, status=400)
        form.save()
        flows.password_reset.finalize_password_reset(request._request, user)
        request.session.pop(RESET_SESSION_UID, None)
        request.session.pop(RESET_SESSION_KEY, None)
        return Response({"saved": True})
