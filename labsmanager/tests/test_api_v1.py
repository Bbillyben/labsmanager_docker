from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import resolve, reverse
from rest_framework.test import APIClient, APITestCase


CAPABILITIES_DENIED = {
    "view_employee_list": False,
    "view_team_list": False,
    "view_contract_list": False,
    "view_project_list": False,
    "view_organizations": False,
    "view_calendar": False,
    "view_dashboard": False,
    "use_fund_finder": False,
    "import_data": False,
}

CAPABILITY_PERMISSION_CODENAMES = (
    ("common", "employee_list"),
    ("common", "team_list"),
    ("common", "contract_list"),
    ("common", "project_list"),
    ("common", "display_infos"),
    ("common", "display_calendar"),
    ("common", "display_dashboard"),
    ("fund", "view_fund"),
    ("common", "import"),
)


@override_settings(
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
)
class CurrentUserApiTests(APITestCase):
    def setUp(self):
        self.url = reverse("api_v1:me")

    def create_user(self, username, **extra_fields):
        return get_user_model().objects.create_user(
            username=username,
            password="test-password",
            **extra_fields,
        )

    def login(self, user):
        self.assertTrue(
            self.client.login(username=user.username, password="test-password")
        )

    def test_anonymous_response_is_minimal_and_sets_csrf_cookie(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"is_authenticated": False})
        self.assertIn("csrftoken", response.cookies)

    def test_authenticated_user_without_permissions_has_no_capabilities(self):
        user = self.create_user(
            "react-user",
            first_name="React",
            last_name="User",
            email="react@example.com",
            is_staff=True,
        )
        self.login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": user.pk,
                "username": "react-user",
                "first_name": "React",
                "last_name": "User",
                "email": "react@example.com",
                "is_authenticated": True,
                "is_staff": True,
                "is_superuser": False,
                "capabilities": CAPABILITIES_DENIED,
            },
        )
        self.assertIn("sessionid", self.client.cookies)

    def test_authenticated_user_capabilities_follow_existing_permissions(self):
        user = self.create_user("permitted-user")
        permissions = [
            Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename,
            )
            for app_label, codename in CAPABILITY_PERMISSION_CODENAMES
        ]
        user.user_permissions.add(*permissions)
        self.login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["capabilities"],
            {capability: True for capability in CAPABILITIES_DENIED},
        )

    def test_superuser_has_all_capabilities(self):
        user = self.create_user("superuser", is_staff=True, is_superuser=True)
        self.login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["capabilities"],
            {capability: True for capability in CAPABILITIES_DENIED},
        )

    def test_session_authentication_enforces_csrf_for_unsafe_requests(self):
        user = self.create_user("csrf-user")
        client = APIClient(enforce_csrf_checks=True)
        self.assertTrue(client.login(username=user.username, password="test-password"))

        response = client.post(self.url, data={})

        self.assertEqual(response.status_code, 403)

    def test_historical_api_route_is_still_resolved(self):
        match = resolve("/api/users/")

        self.assertEqual(match.namespace, "api")
        self.assertEqual(match.url_name, "user-list")
