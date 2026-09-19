from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase


@override_settings(
    ACCOUNT_RATE_LIMITS={"login": "30/m/ip", "login_failed": "5/5m/key"},
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
)
class ApiV1AuthenticationTests(APITestCase):
    """Validate the session and CSRF contract of the React authentication API."""

    password = "correct-horse-battery-staple"

    def setUp(self):
        """Create a regular account and isolate Allauth rate-limit counters."""
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username="ada", email="ada@example.test", password=self.password
        )
        self.login_url = reverse("api_v1:login")
        self.logout_url = reverse("api_v1:logout")
        self.me_url = reverse("api_v1:me")

    def tearDown(self):
        """Prevent rate-limit cache entries leaking into other test classes."""
        cache.clear()

    def csrf_client(self):
        """Return a client primed with the CSRF cookie emitted by ``me``."""
        client = APIClient(enforce_csrf_checks=True)
        response = client.get(self.me_url)
        self.assertEqual(response.status_code, 200)
        return client, response.cookies["csrftoken"].value

    def post_login(self, client, token, login, password):
        """Submit credentials with the CSRF header expected by Django."""
        return client.post(
            self.login_url,
            {"login": login, "password": password},
            format="json",
            HTTP_X_CSRFTOKEN=token,
        )

    def test_login_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        response = client.post(
            self.login_url,
            {"login": self.user.username, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_login_by_username_creates_session(self):
        client, token = self.csrf_client()
        response = self.post_login(client, token, self.user.username, self.password)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"is_authenticated": True})
        self.assertEqual(client.get(self.me_url).json()["id"], self.user.pk)
        self.assertIn("sessionid", client.cookies)

    def test_login_by_email_creates_session(self):
        client, token = self.csrf_client()
        response = self.post_login(client, token, self.user.email, self.password)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(client.get(self.me_url).json()["is_authenticated"])

    def test_login_is_idempotent_for_an_authenticated_session(self):
        client, token = self.csrf_client()
        self.assertEqual(
            self.post_login(client, token, self.user.username, self.password).status_code,
            200,
        )
        token = client.cookies["csrftoken"].value

        response = client.post(
            self.login_url, {}, format="json", HTTP_X_CSRFTOKEN=token
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"is_authenticated": True})

    def test_invalid_credentials_do_not_create_session_or_enumerate(self):
        client, token = self.csrf_client()
        expected = {
            "is_authenticated": False,
            "error": {
                "code": "invalid_credentials",
                "message": "Identifiant ou mot de passe incorrect.",
            },
        }
        unknown = self.post_login(client, token, "unknown", "wrong")
        wrong_password = self.post_login(client, token, self.user.username, "wrong")
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(wrong_password.status_code, 400)
        self.assertEqual(unknown.json(), expected)
        self.assertEqual(wrong_password.json(), expected)
        self.assertNotIn("sessionid", client.cookies)

    def test_inactive_account_uses_same_generic_failure(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        client, token = self.csrf_client()
        response = self.post_login(client, token, self.user.username, self.password)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_credentials")
        self.assertFalse(client.get(self.me_url).json()["is_authenticated"])

    def test_failed_login_limit_is_preserved(self):
        client, token = self.csrf_client()
        for _ in range(5):
            response = self.post_login(client, token, self.user.username, "wrong")
            self.assertEqual(response.status_code, 400)

        limited = self.post_login(client, token, self.user.username, "wrong")

        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.json()["error"]["code"], "too_many_attempts")
        self.assertNotIn("sessionid", client.cookies)

    def test_logout_requires_csrf_and_clears_session(self):
        client, token = self.csrf_client()
        self.assertEqual(
            self.post_login(client, token, self.user.username, self.password).status_code,
            200,
        )
        self.assertEqual(client.post(self.logout_url, format="json").status_code, 403)
        token = client.cookies["csrftoken"].value
        response = client.post(
            self.logout_url, format="json", HTTP_X_CSRFTOKEN=token
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"is_authenticated": False})
        self.assertEqual(client.get(self.me_url).json(), {"is_authenticated": False})

    def test_auth_routes_are_post_only(self):
        self.assertEqual(self.client.get(self.login_url).status_code, 405)
        self.assertEqual(self.client.get(self.logout_url).status_code, 405)
