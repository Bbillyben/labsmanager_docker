from urllib.parse import urlsplit

from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    REACT_PUBLIC_URL="https://frontend.example/app",
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
)
class EmailConfirmationV1Tests(APITestCase):
    bridge = "/api/v1/auth/email/confirm/bridge/"
    current = "/api/v1/auth/email/confirm/"

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="confirmation-ada", email="ada@example.test", password="Password-123!"
        )
        self.address = EmailAddress.objects.create(user=self.user, email=self.user.email, primary=True, verified=False)
        self.key = EmailConfirmationHMAC.create(self.address).key

    def test_new_message_url_uses_react_base_and_legacy_url_still_resolves(self):
        for base in ("https://frontend.example/app", "https://frontend.example/app/"):
            with self.subTest(base=base), override_settings(REACT_PUBLIC_URL=base):
                url = get_adapter().get_email_confirmation_url(None, EmailConfirmationHMAC.create(self.address))
                self.assertTrue(url.startswith(base.rstrip("/") + "/email/confirm/bridge/"))
                self.assertNotIn("/app/app/", url)
        self.assertTrue(reverse("account_confirm_email", kwargs={"key": self.key}).startswith("/accounts/confirm-email/"))
        with override_settings(REACT_PUBLIC_URL=""):
            request = self.client.get("/api/v1/me/").wsgi_request
            self.assertIn("/accounts/confirm-email/", get_adapter().get_email_confirmation_url(request, EmailConfirmationHMAC.create(self.address)))

    def test_sent_confirmation_email_contains_react_link(self):
        request = self.client.get("/api/v1/me/").wsgi_request
        EmailConfirmationHMAC.create(self.address).send(request)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("https://frontend.example/app/email/confirm/bridge/", mail.outbox[0].body)
        self.assertNotIn("/app/app/", mail.outbox[0].body)

    def test_anonymous_bridge_requires_explicit_post_and_reuses_allauth(self):
        client = APIClient(enforce_csrf_checks=True)
        csrf = client.get("/api/v1/me/").cookies["csrftoken"].value
        self.assertEqual(client.post(self.bridge, {"key": self.key}, format="json").status_code, 403)
        exchanged = client.post(self.bridge, {"key": self.key}, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(exchanged.status_code, 200, exchanged.data)
        self.assertEqual(exchanged.data["state"], "confirmation_required")
        self.address.refresh_from_db()
        self.assertFalse(self.address.verified)
        self.assertEqual(client.get(self.current).data["email"], self.user.email)
        self.assertEqual(client.post(self.current).status_code, 403)
        confirmed = client.post(self.current, HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        self.assertEqual(confirmed.data["state"], "confirmed")
        self.address.refresh_from_db()
        self.assertTrue(self.address.verified)
        self.assertEqual(client.get(self.current).data["state"], "confirmed")
        self.assertEqual(client.post(self.current, HTTP_X_CSRFTOKEN=csrf).data["state"], "already_confirmed")

    def test_invalid_expired_and_already_confirmed_states(self):
        self.assertEqual(self.client.post(self.bridge, {"key": "bad"}, format="json").data["state"], "invalid")
        with override_settings(ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS=0):
            self.assertEqual(self.client.post(self.bridge, {"key": self.key}, format="json").data["state"], "invalid")
        self.client.post(self.bridge, {"key": self.key}, format="json")
        self.address.verified = True
        self.address.save(update_fields=["verified"])
        self.assertEqual(self.client.get(self.current).data["state"], "already_confirmed")

    def test_other_signed_in_user_is_logged_out_without_confirming(self):
        other = get_user_model().objects.create_user(username="other", email="other@example.test", password="Password-123!")
        client = APIClient()
        client.force_login(other)
        response = client.post(self.bridge, {"key": self.key}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(client.get("/api/v1/me/").data["is_authenticated"])
        self.address.refresh_from_db()
        self.assertFalse(self.address.verified)

    def test_matching_signed_in_user_stays_signed_in(self):
        client = APIClient()
        client.force_login(self.user)
        self.assertEqual(client.post(self.bridge, {"key": self.key}, format="json").status_code, 200)
        self.assertEqual(client.post(self.current).data["state"], "confirmed")
        self.assertTrue(client.get("/api/v1/me/").data["is_authenticated"])

    def test_existing_django_link_still_confirms(self):
        url = reverse("account_confirm_email", kwargs={"key": self.key})
        self.assertEqual(urlsplit(url).path, url)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.address.refresh_from_db()
        self.assertFalse(self.address.verified)
        self.assertIn(self.client.post(url).status_code, (200, 302))
        self.address.refresh_from_db()
        self.assertTrue(self.address.verified)
