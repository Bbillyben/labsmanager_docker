from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase
from allauth.account.utils import user_pk_to_url_str
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlsplit


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    REACT_PUBLIC_URL="http://frontend.example:5173/app",
    ACCOUNT_RATE_LIMITS={"reset_password": "30/m/key", "reset_password_from_key": "30/m/ip"},
    CSRF_COOKIE_SECURE=False, SESSION_COOKIE_SECURE=False,
)
class PasswordResetV1Tests(APITestCase):
    def setUp(self):
        cache.clear()
        mail.outbox.clear()
        self.user = get_user_model().objects.create_user(
            username="reset-ada", email="reset@example.test", password="Old-password-123!"
        )

    def test_non_enumerating_request_and_react_token_flow(self):
        client = APIClient(enforce_csrf_checks=True)
        csrf = client.get("/api/v1/me/").cookies["csrftoken"].value
        url = "/api/v1/auth/password/reset/"
        unknown = client.post(url, {"email": "missing@example.test"}, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(unknown.status_code, 200)
        mail.outbox.clear()
        known = client.post(url, {"email": self.user.email}, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(known.status_code, 200)
        self.assertEqual(unknown.data, known.data)
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn("/app/password/reset/bridge/", body)
        self.assertNotIn("/accounts/password/reset/key/", body)
        bridge_url = next(word for word in body.split() if "/bridge/" in word)
        self.assertTrue(bridge_url.startswith("http://frontend.example:5173/app/password/reset/bridge/"))
        self.assertNotIn("backend.test", bridge_url)
        key = urlsplit(bridge_url).path.rstrip("/").split("/")[-1]
        bridge = client.get(f"/api/v1/auth/password/reset/bridge/{key}/")
        self.assertEqual(bridge.status_code, 200)
        self.assertEqual(bridge.data["valid"], True)
        self.assertNotIn("Location", bridge)
        uid = bridge.data["uid"]
        confirm_url = f"/api/v1/auth/password/reset/{uid}/"
        self.assertEqual(client.get(confirm_url).status_code, 200)
        self.assertTrue(client.get(confirm_url).data["password_hints"])
        wrong = client.post(confirm_url, {"password1": "weak", "password2": "weak"}, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(wrong.status_code, 400)
        self.assertIn("password1", wrong.data)
        valid = client.post(confirm_url, {"password1": "New-secure-password-456!", "password2": "New-secure-password-456!"}, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(valid.status_code, 200, valid.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-secure-password-456!"))
        self.assertEqual(client.get(confirm_url).status_code, 400)

    def test_email_link_uses_public_react_base_with_or_without_trailing_slash(self):
        for base in ("http://frontend.test:5173/app", "https://example.org/app", "https://example.org/app/"):
            with self.subTest(base=base), override_settings(REACT_PUBLIC_URL=base, ALLOWED_HOSTS=["backend.test"]):
                mail.outbox.clear()
                response = self.client.post(
                    "/api/v1/auth/password/reset/", {"email": self.user.email},
                    format="json", HTTP_HOST="backend.test:7000",
                )
                self.assertEqual(response.status_code, 200)
                link = next(word for word in mail.outbox[-1].body.split() if "/bridge/" in word)
                self.assertTrue(link.startswith(f"{base.rstrip('/')}/password/reset/bridge/"))
                self.assertNotIn("/app/app/", link)
                self.assertNotIn("backend.test", link)
                self.assertTrue(urlsplit(link).path.rstrip("/").split("/")[-1])

    @override_settings(REACT_PUBLIC_URL="")
    def test_missing_public_url_fails_for_known_and_unknown_addresses(self):
        sent_before = len(mail.outbox)
        known = self.client.post("/api/v1/auth/password/reset/", {"email": self.user.email}, format="json")
        unknown = self.client.post("/api/v1/auth/password/reset/", {"email": "missing@example.test"}, format="json")
        self.assertEqual(known.status_code, 503)
        self.assertEqual(known.data, unknown.data)
        self.assertFalse(any(self.user.email in message.to for message in mail.outbox[sent_before:]))

    def test_invalid_link_and_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(client.post("/api/v1/auth/password/reset/", {"email": self.user.email}, format="json").status_code, 403)
        bridge = client.get("/api/v1/auth/password/reset/bridge/not-valid/")
        self.assertEqual(bridge.status_code, 400)
        self.assertEqual(bridge.data, {"valid": False})
        self.assertNotIn("Location", bridge)
        self.assertEqual(client.get("/api/v1/auth/password/reset/invalid/").status_code, 400)

    @override_settings(PASSWORD_RESET_TIMEOUT=1)
    def test_expired_link_is_rejected(self):
        with patch.object(default_token_generator, "_now", return_value=timezone.now().replace(tzinfo=None) - timedelta(minutes=2)):
            token = default_token_generator.make_token(self.user)
        key = f"{user_pk_to_url_str(self.user)}-{token}"
        response = self.client.get(f"/api/v1/auth/password/reset/bridge/{key}/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {"valid": False})
