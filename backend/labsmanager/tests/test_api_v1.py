import platform
from types import SimpleNamespace
from unittest.mock import patch

import django
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.db import connection
from django.urls import resolve, reverse
from labsmanager import lab_version
from labsmanager.api_v1 import get_system_info
from rest_framework.test import APIClient, APITestCase

from staff.models import Employee


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

    def test_authenticated_user_omits_help_links_and_system_info(self):
        user = self.create_user("support-user")
        self.login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse({"help_links", "version", "runtime", "labsmanager_version"} & set(response.data))

    def test_system_info_requires_authentication(self):
        response = self.client.get(reverse("api_v1:system-info"))

        self.assertIn(response.status_code, (401, 403))

    @override_settings(HELP_LINKS=[{"label": "Documentation", "url": "https://example.test/docs"}], LABSMANAGER_SHOW_HELP=True)
    def test_system_info_contains_only_whitelisted_versions_and_help_links(self):
        self.login(self.create_user("system-info-user"))

        response = self.client.get(reverse("api_v1:system-info"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"labsmanager_version", "python_version", "django_version", "database", "help_links"})
        self.assertEqual(response.data["labsmanager_version"], lab_version.LABSMANAGER_VERSION)
        self.assertEqual(response.data["python_version"], platform.python_version())
        self.assertEqual(response.data["django_version"], django.get_version())
        self.assertEqual(set(response.data["database"]), {"vendor", "version"})
        self.assertEqual(response.data["database"]["vendor"], connection.vendor)
        self.assertEqual(response.data["help_links"], [{"label": "Documentation", "url": "https://example.test/docs"}])
        self.assertFalse({"host", "name", "user", "password", "dsn", "path", "secret"} & set(response.data))

    def test_postgresql_runtime_contains_only_formatted_server_version(self):
        with patch("labsmanager.api_v1.connection", SimpleNamespace(vendor="postgresql", pg_version=130017)):
            info = get_system_info()

        self.assertEqual(info["database"], {"vendor": "postgresql", "version": "13.17"})

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
        data = response.json()
        self.assertEqual(
            {key: data[key] for key in (
                "id", "username", "first_name", "last_name", "email", "is_authenticated",
                "is_staff", "is_superuser", "employee",
            )},
            {
                "id": user.pk,
                "username": "react-user",
                "first_name": "React",
                "last_name": "User",
                "email": "react@example.com",
                "is_authenticated": True,
                "is_staff": True,
                "is_superuser": False,
                "employee": None,
            },
        )
        self.assertEqual(data["capabilities"], CAPABILITIES_DENIED | {"manage_data_consistency": True})
        self.assertFalse({"version", "runtime", "help_links"} & set(data))
        self.assertIn("sessionid", self.client.cookies)

    def test_authenticated_user_includes_linked_employee_identity(self):
        user = self.create_user("employee-user")
        employee = Employee.objects.create(
            user=user,
            first_name="Benjamin",
            last_name="LEGENDRE",
        )
        self.login(user)

        response = self.client.get(self.url)

        self.assertEqual(
            response.json()["employee"],
            {
                "id": employee.pk,
                "first_name": "Benjamin",
                "last_name": "LEGENDRE",
            },
        )

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
            {capability: True for capability in CAPABILITIES_DENIED} | {"manage_data_consistency": False},
        )

    def test_superuser_has_all_capabilities(self):
        user = self.create_user("superuser", is_staff=True, is_superuser=True)
        self.login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["capabilities"],
            {capability: True for capability in CAPABILITIES_DENIED} | {"manage_data_consistency": True},
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
