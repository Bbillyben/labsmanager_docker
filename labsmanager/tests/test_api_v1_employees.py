from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from project.models import Participant, Project
from staff.models import (
    Employee,
    Employee_Status,
    Employee_Superior,
    Employee_Type,
    Team,
    TeamMate,
)


@override_settings(
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
)
class EmployeeListV1ApiTests(APITestCase):
    def setUp(self):
        self.url = reverse("api_v1:employees")

    def create_user(self, username):
        return get_user_model().objects.create_user(
            username=username,
            password="test-password",
        )

    def create_employee(self, first_name, last_name, user=None, **extra_fields):
        return Employee.objects.create(
            first_name=first_name,
            last_name=last_name,
            user=user,
            **extra_fields,
        )

    def login(self, user):
        self.assertTrue(
            self.client.login(username=user.username, password="test-password")
        )

    def grant_global_view(self, user):
        permission = Permission.objects.get(
            content_type__app_label="staff",
            codename="view_employee",
        )
        user.user_permissions.add(permission)

    def result_ids(self, response):
        return [item["id"] for item in response.json()["results"]]

    def test_anonymous_user_is_rejected(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 401)

    def test_global_permission_returns_all_employees(self):
        user = self.create_user("global-viewer")
        employees = [
            self.create_employee("Alice", "Alpha"),
            self.create_employee("Bob", "Beta"),
            self.create_employee("Claire", "Gamma"),
        ]
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 3)
        self.assertEqual(set(self.result_ids(response)), {item.pk for item in employees})

    def test_limited_user_sees_self_and_subordinates_only(self):
        user = self.create_user("limited-viewer")
        own_employee = self.create_employee("Limited", "Viewer", user=user)
        subordinate = self.create_employee("Visible", "Subordinate")
        outsider = self.create_employee("Hidden", "Outsider")
        Employee_Superior.objects.create(
            employee=subordinate,
            superior=own_employee,
        )
        self.login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(self.result_ids(response)),
            {own_employee.pk, subordinate.pk},
        )
        self.assertNotIn(outsider.pk, self.result_ids(response))

    def test_authenticated_user_without_employee_has_empty_scope(self):
        user = self.create_user("empty-viewer")
        self.create_employee("Hidden", "Employee")
        self.login(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)
        self.assertEqual(response.json()["results"], [])

    def test_search_cannot_escape_limited_scope(self):
        user = self.create_user("search-viewer")
        own_employee = self.create_employee("Scoped", "Person", user=user)
        self.create_employee("Outside", "Match")
        self.login(user)

        visible_response = self.client.get(self.url, {"search": "Scoped"})
        hidden_response = self.client.get(self.url, {"search": "Outside"})

        self.assertEqual(self.result_ids(visible_response), [own_employee.pk])
        self.assertEqual(hidden_response.json()["count"], 0)

    def test_pagination_uses_limit_and_offset(self):
        user = self.create_user("pagination-viewer")
        self.grant_global_view(user)
        for index in range(5):
            self.create_employee(f"Employee {index}", "Pagination")
        self.login(user)

        response = self.client.get(
            self.url,
            {"limit": 2, "offset": 2, "ordering": "first_name"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 5)
        self.assertEqual(len(response.json()["results"]), 2)
        self.assertIsNotNone(response.json()["next"])
        self.assertIsNotNone(response.json()["previous"])

    def test_active_filter_cannot_escape_limited_scope(self):
        user = self.create_user("active-viewer")
        own_employee = self.create_employee(
            "Active", "Scoped", user=user, is_active=True
        )
        inactive_subordinate = self.create_employee(
            "Inactive", "Scoped", is_active=False
        )
        self.create_employee("Active", "Outside", is_active=True)
        Employee_Superior.objects.create(
            employee=inactive_subordinate,
            superior=own_employee,
        )
        self.login(user)

        active_response = self.client.get(self.url, {"is_active": "true"})
        inactive_response = self.client.get(self.url, {"is_active": "false"})

        self.assertEqual(self.result_ids(active_response), [own_employee.pk])
        self.assertEqual(self.result_ids(inactive_response), [inactive_subordinate.pk])

    def test_allowed_ordering_is_applied(self):
        user = self.create_user("ordering-viewer")
        self.grant_global_view(user)
        second = self.create_employee("Alice", "Zulu")
        first = self.create_employee("Zoe", "Alpha")
        self.login(user)

        response = self.client.get(self.url, {"ordering": "last_name"})

        self.assertEqual(self.result_ids(response), [first.pk, second.pk])

    def test_relational_filters_use_existing_current_relations(self):
        user = self.create_user("filter-viewer")
        self.grant_global_view(user)
        leader = self.create_employee("Team", "Leader")
        member = self.create_employee("Team", "Member")
        subordinate = self.create_employee("Team", "Subordinate")
        other = self.create_employee("Other", "Employee")
        employee_type = Employee_Type.objects.create(shortname="RES", name="Researcher")
        Employee_Status.objects.create(employee=member, type=employee_type)
        Employee_Superior.objects.create(employee=subordinate, superior=leader)
        team = Team.objects.create(name="Research", leader=leader)
        TeamMate.objects.create(team=team, employee=member)
        self.login(user)

        status_response = self.client.get(
            self.url, {"current_status": employee_type.pk}
        )
        superior_response = self.client.get(self.url, {"superior": leader.pk})
        team_response = self.client.get(self.url, {"team": team.pk})

        self.assertEqual(self.result_ids(status_response), [member.pk])
        self.assertEqual(self.result_ids(superior_response), [subordinate.pk])
        self.assertEqual(set(self.result_ids(team_response)), {leader.pk, member.pk})
        self.assertNotIn(other.pk, self.result_ids(team_response))

    def test_response_contains_only_the_v1_list_contract(self):
        user = self.create_user("contract-viewer")
        self.grant_global_view(user)
        superior = self.create_employee("Alice", "Manager")
        employee = self.create_employee(
            "Bob",
            "Employee",
            entry_date=date(2020, 1, 2),
            is_active=True,
        )
        employee_type = Employee_Type.objects.create(shortname="ENG", name="Engineer")
        Employee_Status.objects.create(employee=employee, type=employee_type)
        Employee_Status.objects.create(
            employee=employee,
            type=Employee_Type.objects.create(shortname="OLD", name="Former"),
            end_date=date.today() - timedelta(days=1),
        )
        Employee_Superior.objects.create(employee=employee, superior=superior)
        self.login(user)

        response = self.client.get(self.url, {"search": "Bob"})
        result = response.json()["results"][0]

        self.assertEqual(
            set(result),
            {
                "id",
                "first_name",
                "last_name",
                "entry_date",
                "exit_date",
                "is_active",
                "current_statuses",
                "superiors",
            },
        )
        self.assertEqual(
            result["current_statuses"],
            [{"id": employee_type.pk, "code": "ENG", "name": "Engineer"}],
        )
        self.assertEqual(
            result["superiors"],
            [
                {
                    "id": superior.pk,
                    "first_name": "Alice",
                    "last_name": "MANAGER",
                }
            ],
        )


@override_settings(
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
)
class EmployeeDetailV1ApiTests(APITestCase):
    def setUp(self):
        self.list_url = reverse("api_v1:employees")

    def create_user(self, username):
        return get_user_model().objects.create_user(
            username=username,
            password="test-password",
        )

    def create_employee(self, first_name, last_name, user=None, **extra_fields):
        return Employee.objects.create(
            first_name=first_name,
            last_name=last_name,
            user=user,
            **extra_fields,
        )

    def login(self, user):
        self.assertTrue(
            self.client.login(username=user.username, password="test-password")
        )

    def grant_global_view(self, user):
        permission = Permission.objects.get(
            content_type__app_label="staff",
            codename="view_employee",
        )
        user.user_permissions.add(permission)

    def detail_url(self, employee_id):
        return reverse("api_v1:employee-detail", kwargs={"pk": employee_id})

    def test_anonymous_user_is_rejected_from_detail(self):
        employee = self.create_employee("Anonymous", "Target")

        response = self.client.get(self.detail_url(employee.pk))

        self.assertEqual(response.status_code, 401)

    def test_global_permission_can_retrieve_detail(self):
        user = self.create_user("global-detail-viewer")
        employee = self.create_employee("Global", "Target")
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(self.detail_url(employee.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], employee.pk)

    def test_relational_scope_can_retrieve_subordinate_detail(self):
        user = self.create_user("relational-detail-viewer")
        own_employee = self.create_employee("Relational", "Viewer", user=user)
        subordinate = self.create_employee("Visible", "Subordinate")
        Employee_Superior.objects.create(employee=subordinate, superior=own_employee)
        self.login(user)

        response = self.client.get(self.detail_url(subordinate.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], subordinate.pk)

    def test_relational_scope_can_retrieve_own_detail(self):
        user = self.create_user("own-detail-viewer")
        own_employee = self.create_employee("Own", "Employee", user=user)
        self.login(user)

        response = self.client.get(self.detail_url(own_employee.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], own_employee.pk)

    def test_known_employee_outside_scope_returns_not_found(self):
        user = self.create_user("limited-detail-viewer")
        self.create_employee("Limited", "Viewer", user=user)
        outsider = self.create_employee("Hidden", "Outsider")
        self.login(user)

        response = self.client.get(self.detail_url(outsider.pk))

        self.assertEqual(response.status_code, 404)

    def test_unknown_employee_returns_not_found(self):
        user = self.create_user("missing-detail-viewer")
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(self.detail_url(999999))

        self.assertEqual(response.status_code, 404)

    def test_detail_contract_matches_list_item_and_excludes_other_fields(self):
        user = self.create_user("detail-contract-viewer")
        superior = self.create_employee("Alice", "Manager")
        employee = self.create_employee(
            "Bob",
            "Employee",
            user=user,
            entry_date=date(2020, 1, 2),
            is_active=True,
            email="bob@example.com",
            birth_date=date(1990, 3, 4),
        )
        employee_type = Employee_Type.objects.create(shortname="ENG", name="Engineer")
        Employee_Status.objects.create(employee=employee, type=employee_type)
        Employee_Superior.objects.create(employee=employee, superior=superior)
        self.login(user)

        detail_response = self.client.get(self.detail_url(employee.pk))
        list_response = self.client.get(self.list_url, {"search": "Bob"})

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json(), list_response.json()["results"][0])
        self.assertEqual(
            set(detail_response.json()),
            {
                "id",
                "first_name",
                "last_name",
                "entry_date",
                "exit_date",
                "is_active",
                "current_statuses",
                "superiors",
            },
        )
        self.assertNotIn("email", detail_response.json())
        self.assertNotIn("birth_date", detail_response.json())
        self.assertNotIn("user", detail_response.json())


@override_settings(
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
)
class EmployeeStatusHistoryV1ApiTests(APITestCase):
    def create_user(self, username):
        return get_user_model().objects.create_user(
            username=username,
            password="test-password",
        )

    def create_employee(self, first_name, last_name, user=None):
        return Employee.objects.create(
            first_name=first_name,
            last_name=last_name,
            user=user,
        )

    def create_status(self, employee, code, name, **extra_fields):
        employee_type = Employee_Type.objects.create(shortname=code, name=name)
        return Employee_Status.objects.create(
            employee=employee,
            type=employee_type,
            **extra_fields,
        )

    def login(self, user):
        self.assertTrue(
            self.client.login(username=user.username, password="test-password")
        )

    def grant_global_view(self, user):
        permission = Permission.objects.get(
            content_type__app_label="staff",
            codename="view_employee",
        )
        user.user_permissions.add(permission)

    def statuses_url(self, employee_id):
        return reverse("api_v1:employee-statuses", kwargs={"pk": employee_id})

    def test_anonymous_user_is_rejected(self):
        employee = self.create_employee("Anonymous", "Target")

        response = self.client.get(self.statuses_url(employee.pk))

        self.assertEqual(response.status_code, 401)

    def test_global_permission_can_retrieve_statuses(self):
        user = self.create_user("global-status-viewer")
        employee = self.create_employee("Global", "Target")
        status = self.create_status(employee, "ENG", "Engineer")
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(self.statuses_url(employee.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [status.pk])

    def test_relational_scope_can_retrieve_subordinate_statuses(self):
        user = self.create_user("relational-status-viewer")
        own_employee = self.create_employee("Relational", "Viewer", user=user)
        subordinate = self.create_employee("Visible", "Subordinate")
        status = self.create_status(subordinate, "RES", "Researcher")
        Employee_Superior.objects.create(employee=subordinate, superior=own_employee)
        self.login(user)

        response = self.client.get(self.statuses_url(subordinate.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [status.pk])

    def test_relational_scope_can_retrieve_own_statuses(self):
        user = self.create_user("own-status-viewer")
        own_employee = self.create_employee("Own", "Employee", user=user)
        status = self.create_status(own_employee, "OWN", "Own status")
        self.login(user)

        response = self.client.get(self.statuses_url(own_employee.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [status.pk])

    def test_known_employee_outside_scope_returns_not_found(self):
        user = self.create_user("limited-status-viewer")
        self.create_employee("Limited", "Viewer", user=user)
        outsider = self.create_employee("Hidden", "Outsider")
        self.create_status(outsider, "HID", "Hidden status")
        self.login(user)

        response = self.client.get(self.statuses_url(outsider.pk))

        self.assertEqual(response.status_code, 404)

    def test_unknown_employee_returns_not_found(self):
        user = self.create_user("missing-status-viewer")
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(self.statuses_url(999999))

        self.assertEqual(response.status_code, 404)

    def test_visible_employee_without_statuses_returns_empty_collection(self):
        user = self.create_user("empty-status-viewer")
        employee = self.create_employee("Empty", "History")
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(self.statuses_url(employee.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_history_contract_and_order_are_deterministic(self):
        user = self.create_user("status-contract-viewer")
        employee = self.create_employee("Status", "History")
        today = date.today()
        current = self.create_status(
            employee,
            "CUR",
            "Current",
            start_date=today - timedelta(days=5),
            is_contractual="c",
        )
        most_recent_past = self.create_status(
            employee,
            "REC",
            "Recent",
            start_date=today - timedelta(days=50),
            end_date=today - timedelta(days=10),
            is_contractual="s",
        )
        oldest = self.create_status(
            employee,
            "OLD",
            "Old",
            start_date=today - timedelta(days=100),
            end_date=today - timedelta(days=20),
            is_contractual="c",
        )
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(self.statuses_url(employee.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": oldest.pk,
                    "type": {
                        "id": oldest.type_id,
                        "code": "OLD",
                        "name": "Old",
                    },
                    "start_date": (today - timedelta(days=100)).isoformat(),
                    "end_date": (today - timedelta(days=20)).isoformat(),
                    "contractuality": {
                        "code": "c",
                        "label": str(oldest.get_is_contractual_display()),
                    },
                    "is_active": False,
                },
                {
                    "id": most_recent_past.pk,
                    "type": {
                        "id": most_recent_past.type_id,
                        "code": "REC",
                        "name": "Recent",
                    },
                    "start_date": (today - timedelta(days=50)).isoformat(),
                    "end_date": (today - timedelta(days=10)).isoformat(),
                    "contractuality": {
                        "code": "s",
                        "label": str(
                            most_recent_past.get_is_contractual_display()
                        ),
                    },
                    "is_active": False,
                },
                {
                    "id": current.pk,
                    "type": {
                        "id": current.type_id,
                        "code": "CUR",
                        "name": "Current",
                    },
                    "start_date": (today - timedelta(days=5)).isoformat(),
                    "end_date": None,
                    "contractuality": {
                        "code": "c",
                        "label": str(current.get_is_contractual_display()),
                    },
                    "is_active": True,
                },
            ],
        )
        for item in response.json():
            self.assertEqual(
                set(item),
                {
                    "id",
                    "type",
                    "start_date",
                    "end_date",
                    "contractuality",
                    "is_active",
                },
            )
            self.assertNotIn("has_perm", item)
            self.assertNotIn("can_edit", item)
            self.assertNotIn("employee", item)


@override_settings(
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
)
class EmployeeHierarchyV1ApiTests(APITestCase):
    def create_user(self, username):
        return get_user_model().objects.create_user(
            username=username,
            password="test-password",
        )

    def create_employee(self, first_name, last_name, user=None):
        return Employee.objects.create(
            first_name=first_name,
            last_name=last_name,
            user=user,
        )

    def login(self, user):
        self.assertTrue(
            self.client.login(username=user.username, password="test-password")
        )

    def grant_global_view(self, user):
        permission = Permission.objects.get(
            content_type__app_label="staff",
            codename="view_employee",
        )
        user.user_permissions.add(permission)

    def hierarchy_url(self, employee_id):
        return reverse("api_v1:employee-hierarchy", kwargs={"pk": employee_id})

    def detail_url(self, employee_id):
        return reverse("api_v1:employee-detail", kwargs={"pk": employee_id})

    def test_anonymous_user_is_rejected(self):
        employee = self.create_employee("Anonymous", "Target")

        response = self.client.get(self.hierarchy_url(employee.pk))

        self.assertEqual(response.status_code, 401)

    def test_global_permission_can_retrieve_hierarchy(self):
        user = self.create_user("global-hierarchy-viewer")
        target = self.create_employee("Global", "Target")
        superior = self.create_employee("Global", "Superior")
        relation = Employee_Superior.objects.create(
            employee=target,
            superior=superior,
        )
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(self.hierarchy_url(target.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["superiors"]],
            [relation.pk],
        )

    def test_relational_scope_can_retrieve_subordinate_hierarchy(self):
        user = self.create_user("relational-hierarchy-viewer")
        own_employee = self.create_employee("Relational", "Viewer", user=user)
        target = self.create_employee("Visible", "Subordinate")
        relation = Employee_Superior.objects.create(
            employee=target,
            superior=own_employee,
        )
        self.login(user)

        response = self.client.get(self.hierarchy_url(target.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.json()["superiors"]],
            [relation.pk],
        )

    def test_known_employee_outside_scope_returns_not_found(self):
        user = self.create_user("limited-hierarchy-viewer")
        self.create_employee("Limited", "Viewer", user=user)
        outsider = self.create_employee("Hidden", "Outsider")
        self.login(user)

        response = self.client.get(self.hierarchy_url(outsider.pk))

        self.assertEqual(response.status_code, 404)

    def test_unknown_employee_returns_not_found(self):
        user = self.create_user("missing-hierarchy-viewer")
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(self.hierarchy_url(999999))

        self.assertEqual(response.status_code, 404)

    def test_visible_employee_without_relations_returns_empty_collections(self):
        user = self.create_user("empty-hierarchy-viewer")
        target = self.create_employee("Empty", "Hierarchy", user=user)
        self.login(user)

        response = self.client.get(self.hierarchy_url(target.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"superiors": [], "subordinates": []},
        )

    def test_hierarchy_contract_history_and_order_are_deterministic(self):
        user = self.create_user("hierarchy-contract-viewer")
        target = self.create_employee("Hierarchy", "Target")
        old_superior = self.create_employee("Old", "Superior")
        current_superior = self.create_employee("Current", "Superior")
        old_subordinate = self.create_employee("Old", "Subordinate")
        current_subordinate = self.create_employee("Current", "Subordinate")
        today = date.today()
        superior_history = Employee_Superior.objects.create(
            employee=target,
            superior=old_superior,
            start_date=today - timedelta(days=100),
            end_date=today - timedelta(days=20),
        )
        superior_current = Employee_Superior.objects.create(
            employee=target,
            superior=current_superior,
            start_date=today - timedelta(days=5),
        )
        subordinate_history = Employee_Superior.objects.create(
            employee=old_subordinate,
            superior=target,
            start_date=today - timedelta(days=50),
            end_date=today - timedelta(days=10),
        )
        subordinate_current = Employee_Superior.objects.create(
            employee=current_subordinate,
            superior=target,
            start_date=today - timedelta(days=2),
        )
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(self.hierarchy_url(target.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "superiors": [
                    {
                        "id": superior_history.pk,
                        "employee": {
                            "id": old_superior.pk,
                            "first_name": "Old",
                            "last_name": "SUPERIOR",
                        },
                        "start_date": (today - timedelta(days=100)).isoformat(),
                        "end_date": (today - timedelta(days=20)).isoformat(),
                        "is_active": False,
                    },
                    {
                        "id": superior_current.pk,
                        "employee": {
                            "id": current_superior.pk,
                            "first_name": "Current",
                            "last_name": "SUPERIOR",
                        },
                        "start_date": (today - timedelta(days=5)).isoformat(),
                        "end_date": None,
                        "is_active": True,
                    },
                ],
                "subordinates": [
                    {
                        "id": subordinate_history.pk,
                        "employee": {
                            "id": old_subordinate.pk,
                            "first_name": "Old",
                            "last_name": "SUBORDINATE",
                        },
                        "start_date": (today - timedelta(days=50)).isoformat(),
                        "end_date": (today - timedelta(days=10)).isoformat(),
                        "is_active": False,
                    },
                    {
                        "id": subordinate_current.pk,
                        "employee": {
                            "id": current_subordinate.pk,
                            "first_name": "Current",
                            "last_name": "SUBORDINATE",
                        },
                        "start_date": (today - timedelta(days=2)).isoformat(),
                        "end_date": None,
                        "is_active": True,
                    },
                ],
            },
        )
        for collection in response.json().values():
            for item in collection:
                self.assertEqual(
                    set(item),
                    {"id", "employee", "start_date", "end_date", "is_active"},
                )
                self.assertEqual(
                    set(item["employee"]),
                    {"id", "first_name", "last_name"},
                )
                self.assertNotIn("has_perm", item)
                self.assertNotIn("email", item["employee"])

    def test_linked_identity_does_not_grant_linked_employee_detail_access(self):
        user = self.create_user("linked-hierarchy-viewer")
        target = self.create_employee("Visible", "Target", user=user)
        hidden_superior = self.create_employee("Hidden", "Superior")
        relation = Employee_Superior.objects.create(
            employee=target,
            superior=hidden_superior,
        )
        self.login(user)

        hierarchy_response = self.client.get(self.hierarchy_url(target.pk))
        detail_response = self.client.get(self.detail_url(hidden_superior.pk))

        self.assertEqual(hierarchy_response.status_code, 200)
        self.assertEqual(
            hierarchy_response.json()["superiors"],
            [
                {
                    "id": relation.pk,
                    "employee": {
                        "id": hidden_superior.pk,
                        "first_name": "Hidden",
                        "last_name": "SUPERIOR",
                    },
                    "start_date": None,
                    "end_date": None,
                    "is_active": True,
                }
            ],
        )
        self.assertEqual(detail_response.status_code, 404)


@override_settings(
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
)
class EmployeeProjectParticipationV1ApiTests(APITestCase):
    def create_user(self, username):
        return get_user_model().objects.create_user(
            username=username,
            password="test-password",
        )

    def create_employee(self, first_name, last_name, user=None):
        return Employee.objects.create(
            first_name=first_name,
            last_name=last_name,
            user=user,
        )

    def create_project(self, name, **extra_fields):
        return Project.objects.create(name=name, **extra_fields)

    def create_participation(self, employee, project, **extra_fields):
        return Participant.objects.create(
            employee=employee,
            project=project,
            **extra_fields,
        )

    def login(self, user):
        self.assertTrue(
            self.client.login(username=user.username, password="test-password")
        )

    def grant_global_view(self, user):
        permission = Permission.objects.get(
            content_type__app_label="staff",
            codename="view_employee",
        )
        user.user_permissions.add(permission)

    def participations_url(self, employee_id):
        return reverse(
            "api_v1:employee-project-participations",
            kwargs={"pk": employee_id},
        )

    def response_ids(self, response):
        return [item["id"] for item in response.json()]

    def test_anonymous_user_is_rejected(self):
        employee = self.create_employee("Anonymous", "Target")

        response = self.client.get(self.participations_url(employee.pk))

        self.assertEqual(response.status_code, 401)

    def test_global_permission_can_retrieve_participations(self):
        user = self.create_user("global-participation-viewer")
        employee = self.create_employee("Global", "Target")
        participation = self.create_participation(
            employee, self.create_project("Global project")
        )
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(self.participations_url(employee.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.response_ids(response), [participation.pk])

    def test_relational_scope_exposes_participation_without_project_visibility(self):
        user = self.create_user("relational-participation-viewer")
        own_employee = self.create_employee("Relational", "Viewer", user=user)
        target = self.create_employee("Visible", "Subordinate")
        Employee_Superior.objects.create(employee=target, superior=own_employee)
        project = self.create_project("Hidden standalone project")
        participation = self.create_participation(target, project)
        self.assertFalse(user.has_perm("project.view_project", project))
        self.login(user)

        response = self.client.get(self.participations_url(target.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.response_ids(response), [participation.pk])
        self.assertEqual(response.json()[0]["project"]["id"], project.pk)
        self.assertFalse(user.has_perm("project.view_project", project))

    def test_known_employee_outside_scope_returns_not_found(self):
        user = self.create_user("limited-participation-viewer")
        self.create_employee("Limited", "Viewer", user=user)
        outsider = self.create_employee("Hidden", "Outsider")
        self.create_participation(outsider, self.create_project("Hidden project"))
        self.login(user)

        response = self.client.get(self.participations_url(outsider.pk))

        self.assertEqual(response.status_code, 404)

    def test_unknown_employee_returns_not_found(self):
        user = self.create_user("missing-participation-viewer")
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(self.participations_url(999999))

        self.assertEqual(response.status_code, 404)

    def test_visible_employee_without_participations_returns_empty_collection(self):
        user = self.create_user("empty-participation-viewer")
        employee = self.create_employee("Empty", "Participations", user=user)
        self.login(user)

        response = self.client.get(self.participations_url(employee.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_contract_roles_quotity_and_order_are_deterministic(self):
        user = self.create_user("participation-contract-viewer")
        employee = self.create_employee("Project", "Participant")
        project = self.create_project(
            "Project reference",
            start_date=date(2020, 1, 1),
            end_date=date(2030, 12, 31),
            status=False,
        )
        today = date.today()
        historic = self.create_participation(
            employee,
            project,
            status="p",
            quotity="0.250",
            start_date=today - timedelta(days=100),
            end_date=today - timedelta(days=20),
        )
        current_leader = self.create_participation(
            employee,
            project,
            status="l",
            quotity="0.500",
            start_date=today - timedelta(days=5),
        )
        current_coleader = self.create_participation(
            employee,
            self.create_project("Second project"),
            status="cl",
            quotity="0.125",
            start_date=today - timedelta(days=2),
            end_date=today + timedelta(days=30),
        )
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(self.participations_url(employee.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.response_ids(response),
            [current_leader.pk, current_coleader.pk, historic.pk],
        )
        by_id = {item["id"]: item for item in response.json()}
        self.assertEqual(
            by_id[current_leader.pk],
            {
                "id": current_leader.pk,
                "project": {
                    "id": project.pk,
                    "name": "Project reference",
                    "start_date": "2020-01-01",
                    "end_date": "2030-12-31",
                },
                "role": {
                    "code": "l",
                    "label": str(current_leader.get_status_display()),
                },
                "start_date": (today - timedelta(days=5)).isoformat(),
                "end_date": None,
                "quotity": "0.500",
                "is_active": True,
            },
        )
        self.assertEqual(by_id[current_coleader.pk]["role"]["code"], "cl")
        self.assertEqual(
            by_id[current_coleader.pk]["role"]["label"],
            str(current_coleader.get_status_display()),
        )
        self.assertEqual(by_id[historic.pk]["role"]["code"], "p")
        for item in response.json():
            self.assertEqual(
                set(item),
                {
                    "id",
                    "project",
                    "role",
                    "start_date",
                    "end_date",
                    "quotity",
                    "is_active",
                },
            )
            self.assertEqual(
                set(item["project"]),
                {"id", "name", "start_date", "end_date"},
            )
            self.assertNotIn("status", item["project"])
            self.assertNotIn("is_active", item["project"])
            self.assertNotIn("has_perm", item)
            self.assertNotIn("can_edit", item)

    def test_active_filter_matches_all_mixin_boundary_cases(self):
        user = self.create_user("participation-filter-viewer")
        employee = self.create_employee("Filter", "Target")
        project = self.create_project("Filter project")
        today = date.today()
        expected_active = [
            self.create_participation(employee, project),
            self.create_participation(
                employee, project, start_date=today, end_date=today
            ),
            self.create_participation(
                employee, project, start_date=today - timedelta(days=1)
            ),
            self.create_participation(
                employee, project, end_date=today + timedelta(days=1)
            ),
        ]
        expected_inactive = [
            self.create_participation(
                employee, project, start_date=today + timedelta(days=1)
            ),
            self.create_participation(
                employee, project, end_date=today - timedelta(days=1)
            ),
        ]
        self.grant_global_view(user)
        self.login(user)

        all_response = self.client.get(self.participations_url(employee.pk))
        active_response = self.client.get(
            self.participations_url(employee.pk), {"is_active": "true"}
        )
        inactive_response = self.client.get(
            self.participations_url(employee.pk), {"is_active": "false"}
        )

        self.assertEqual(
            set(self.response_ids(all_response)),
            {item.pk for item in expected_active + expected_inactive},
        )
        self.assertEqual(
            set(self.response_ids(active_response)),
            {item.pk for item in expected_active},
        )
        self.assertEqual(
            set(self.response_ids(inactive_response)),
            {item.pk for item in expected_inactive},
        )
        for participation in expected_active + expected_inactive:
            serialized = next(
                item
                for item in all_response.json()
                if item["id"] == participation.pk
            )
            self.assertEqual(serialized["is_active"], participation.is_active)

    def test_invalid_active_filter_is_ignored_like_existing_v1_booleans(self):
        user = self.create_user("invalid-participation-filter-viewer")
        employee = self.create_employee("Invalid", "Filter")
        project = self.create_project("Invalid filter project")
        current = self.create_participation(employee, project)
        historic = self.create_participation(
            employee,
            project,
            end_date=date.today() - timedelta(days=1),
        )
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(
            self.participations_url(employee.pk), {"is_active": "invalid"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(self.response_ids(response)), {current.pk, historic.pk})
