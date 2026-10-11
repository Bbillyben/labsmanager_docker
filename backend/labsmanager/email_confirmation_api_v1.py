"""React presentation of allauth's email-confirmation workflow."""

from allauth.account.models import EmailAddress, get_emailconfirmation_model
from allauth.account.views import ConfirmEmailView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


SESSION_KEY = "react_email_confirmation_key"
SESSION_ADDRESS = "react_email_confirmation_address"
SESSION_RESULT = "react_email_confirmation_result"
NO_STORE = {"Cache-Control": "no-store"}


def _clear(request):
    for name in (SESSION_KEY, SESSION_ADDRESS, SESSION_RESULT):
        request.session.pop(name, None)


def _confirmation(request):
    key = request.session.get(SESSION_KEY)
    address_id = request.session.get(SESSION_ADDRESS)
    if not isinstance(key, str) or not isinstance(address_id, int):
        return None
    confirmation = get_emailconfirmation_model().from_key(key)
    if confirmation is None or confirmation.email_address.pk != address_id:
        return None
    return confirmation


@method_decorator(csrf_protect, name="dispatch")
class EmailConfirmationBridgeV1View(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        key = request.data.get("key") if isinstance(request.data, dict) else None
        if not isinstance(key, str) or not key:
            _clear(request)
            return Response({"state": "invalid"}, status=400, headers=NO_STORE)
        confirmation = get_emailconfirmation_model().from_key(key)
        if confirmation is None:
            _clear(request)
            return Response({"state": "invalid"}, status=400, headers=NO_STORE)

        # Match allauth's GET behavior when another user is currently signed in.
        view = ConfirmEmailView()
        view.setup(request._request, key=key)
        view.logout_other_user(confirmation)
        request.session[SESSION_KEY] = key
        request.session[SESSION_ADDRESS] = confirmation.email_address.pk
        request.session.pop(SESSION_RESULT, None)
        return Response({"state": "confirmation_required"}, headers=NO_STORE)


@method_decorator(csrf_protect, name="dispatch")
class EmailConfirmationV1View(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        if request.session.get(SESSION_RESULT) == "confirmed":
            return Response({"state": "confirmed"}, headers=NO_STORE)
        confirmation = _confirmation(request)
        if confirmation is not None:
            return Response({"state": "confirmation_required", "email": confirmation.email_address.email}, headers=NO_STORE)
        address_id = request.session.get(SESSION_ADDRESS)
        if isinstance(address_id, int) and EmailAddress.objects.filter(pk=address_id, verified=True).exists():
            _clear(request)
            return Response({"state": "already_confirmed"}, headers=NO_STORE)
        _clear(request)
        return Response({"state": "invalid"}, status=400, headers=NO_STORE)

    def post(self, request):
        if request.session.get(SESSION_RESULT) == "confirmed":
            return Response({"state": "already_confirmed"}, headers=NO_STORE)
        confirmation = _confirmation(request)
        if confirmation is None:
            address_id = request.session.get(SESSION_ADDRESS)
            if isinstance(address_id, int) and EmailAddress.objects.filter(pk=address_id, verified=True).exists():
                _clear(request)
                return Response({"state": "already_confirmed"}, headers=NO_STORE)
            _clear(request)
            return Response({"state": "invalid"}, status=400, headers=NO_STORE)

        key = request.session[SESSION_KEY]
        address = confirmation.email_address
        # The allauth view owns confirmation, signals, primary-address rules,
        # optional login and the signed-in user mismatch behavior.
        ConfirmEmailView.as_view()(request._request, key=key)
        address.refresh_from_db()
        if not address.verified:
            _clear(request)
            return Response({"state": "invalid"}, status=400, headers=NO_STORE)
        _clear(request)
        request.session[SESSION_RESULT] = "confirmed"
        return Response({"state": "confirmed"}, headers=NO_STORE)
