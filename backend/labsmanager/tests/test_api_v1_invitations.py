"""Focused React invitation bridge and allauth signup checks."""

from datetime import timedelta
from urllib.parse import urlsplit

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import RequestFactory, override_settings
from django.utils import timezone
from invitations.models import Invitation
from rest_framework.test import APIClient, APITestCase


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    REACT_PUBLIC_URL="http://frontend.example:5173/app",
    ALLOWED_HOSTS=["backend.test", "testserver"],
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
)
class InvitationReactV1Tests(APITestCase):
    bridge_url = "/api/v1/auth/invitations/bridge/"
    current_url = "/api/v1/auth/invitations/current/"

    def create_invitation(self, email="invited@example.test", **fields):
        invitation = Invitation.create(email)
        invitation.sent = fields.get("sent", timezone.now())
        invitation.accepted = fields.get("accepted", False)
        invitation.save()
        return invitation

    def bridge(self, invitation, client=None):
        return (client or self.client).post(self.bridge_url, {"token": invitation.key}, format="json")

    def test_mail_uses_react_link_without_changing_legacy_route(self):
        invitation = Invitation.create("mail@example.test")
        invitation.send_invitation(RequestFactory().get("/", HTTP_HOST="backend.test"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f"http://frontend.example:5173/app/invitations/accept/{invitation.key}/", mail.outbox[0].body)
        self.assertNotIn("backend.test/invitations/", mail.outbox[0].body)
        self.assertEqual(urlsplit(f"http://frontend.example:5173/app/invitations/accept/{invitation.key}/").path.split("/")[-2], invitation.key)
        self.assertEqual(self.client.get(f"/invitations/accept-invite/{invitation.key}/").status_code, 302)
        self.assertEqual(self.client.get(f"/invitations/accept/{invitation.key}/").status_code, 302)

    def test_bridge_validates_without_consumption_and_removes_token_from_api_contract(self):
        invitation = self.create_invitation()
        response = self.bridge(invitation)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["email"], invitation.email)
        self.assertNotIn(invitation.key, str(response.data))
        self.assertTrue(response.data["fields"]["username"])
        self.assertEqual(self.client.get(self.current_url).status_code, 200)
        self.assertEqual(self.client.get(self.current_url).status_code, 200)
        invitation.refresh_from_db()
        self.assertFalse(invitation.accepted)

    def test_invalid_expired_accepted_and_registered_email_are_rejected(self):
        self.assertEqual(self.client.post(self.bridge_url, {"token": "x" * 64}, format="json").data["state"], "invalid")
        expired = self.create_invitation("expired@example.test", sent=timezone.now() - timedelta(days=4))
        self.assertEqual(self.bridge(expired).data["state"], "expired")
        accepted = self.create_invitation("accepted@example.test", accepted=True)
        self.assertEqual(self.bridge(accepted).data["state"], "accepted")
        existing = self.create_invitation("existing@example.test")
        get_user_model().objects.create_user(username="already-here", email=existing.email)
        self.assertEqual(self.bridge(existing).data["state"], "account_exists")

    def test_signup_uses_allauth_and_accepts_once(self):
        invitation = self.create_invitation()
        self.assertEqual(self.bridge(invitation).status_code, 200)
        result = self.client.post(self.current_url, {
            "username": "invited-person", "password1": "Invited-password-123!", "password2": "Invited-password-123!",
        }, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data["state"], "complete")
        self.assertTrue(result.data["authenticated"])
        invitation.refresh_from_db()
        self.assertTrue(invitation.accepted)
        user = get_user_model().objects.get(username="invited-person")
        self.assertEqual(user.email, invitation.email)
        self.assertTrue(EmailAddress.objects.get(user=user, email=invitation.email).verified)
        self.assertEqual(self.client.post(self.current_url, {"username": "again"}, format="json").status_code, 409)
        self.assertEqual(self.bridge(invitation, APIClient()).data["state"], "accepted")

    def test_signup_validation_and_mismatched_email_leave_invitation_open(self):
        invitation = self.create_invitation()
        self.bridge(invitation)
        mismatch = self.client.post(self.current_url, {"email": "other@example.test"}, format="json")
        self.assertEqual(mismatch.status_code, 400)
        invalid = self.client.post(self.current_url, {"username": "invited-person", "password1": "short", "password2": "different"}, format="json")
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("password1", invalid.data)
        invitation.refresh_from_db()
        self.assertFalse(invitation.accepted)

    def test_signup_requires_the_email_verified_for_this_invitation_in_session(self):
        invitation = self.create_invitation()
        self.bridge(invitation)
        session = self.client.session
        session["account_verified_email"] = "other@example.test"
        session.save()
        result = self.client.post(self.current_url, {
            "username": "invited-person", "password1": "Invited-password-123!", "password2": "Invited-password-123!",
        }, format="json")
        self.assertEqual(result.data["state"], "invalid")
        self.assertFalse(get_user_model().objects.filter(username="invited-person").exists())

    def test_csrf_and_authenticated_user_are_rejected(self):
        invitation = self.create_invitation()
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(self.bridge(invitation, client).status_code, 403)
        csrf = client.get("/api/v1/me/").cookies["csrftoken"].value
        self.assertEqual(client.post(self.bridge_url, {"token": invitation.key}, format="json", HTTP_X_CSRFTOKEN=csrf).status_code, 200)
        self.assertEqual(client.post(self.current_url, {"username": "blocked"}, format="json").status_code, 403)
        user = get_user_model().objects.create_user(username="logged-in", email="other@example.test")
        self.client.force_authenticate(user)
        self.assertEqual(self.bridge(invitation).data["state"], "authenticated")
        self.assertEqual(self.client.get(self.current_url).data["state"], "authenticated")
