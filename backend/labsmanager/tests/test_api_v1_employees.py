from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from common.calendar import LabsManagerCalendarEvent
from endpoints.models import Milestones
from expense.models import Contract, Contract_expense, Contract_type
from fund.models import Budget, Contribution, Cost_Type, Fund, Fund_Institution
from leave.models import Leave, Leave_Type
from project.models import Institution, Participant, Project
from settings.models import LMUserSetting
from staff.models import (
    Employee,
    Employee_Status,
    Employee_Superior,
    Employee_Type,
    GenericInfo,
    GenericInfoType,
    Team,
    TeamMate,
)


class EmployeeLeaveV1ApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="leave-viewer", password="test-password"
        )
        self.employee = Employee.objects.create(
            first_name="Leave", last_name="Viewer", user=self.user
        )
        self.other = Employee.objects.create(first_name="Hidden", last_name="Person")
        self.leave_type = Leave_Type.objects.create(
            short_name="CP", name="Paid leave", color="#336699"
        )
        self.leave = Leave.objects.create(
            employee=self.employee,
            type=self.leave_type,
            start_date=date(2026, 9, 10),
            start_period="MI",
            end_date=date(2026, 9, 12),
            end_period="MI",
            comment="Family event",
        )
        Leave.objects.create(
            employee=self.other,
            type=self.leave_type,
            start_date=date(2026, 9, 10),
            end_date=date(2026, 9, 10),
        )
        self.assertTrue(self.client.login(username=self.user.username, password="test-password"))

    def test_leave_list_is_contextual_and_filters_by_intersection(self):
        url = reverse("api_v1:employee-leaves", kwargs={"pk": self.employee.pk})
        response = self.client.get(url, {"from": "2026-09-11", "to": "2026-09-20"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        payload = response.json()[0]
        self.assertEqual(payload["id"], self.leave.pk)
        self.assertEqual(payload["type"]["short_name"], "CP")
        self.assertEqual(payload["start_period"], "MI")
        self.assertEqual(payload["day_count"], 1.0)
        self.assertEqual(payload["comment"], "Family event")

    def test_leave_list_hides_an_employee_outside_the_root_scope(self):
        response = self.client.get(reverse("api_v1:employee-leaves", kwargs={"pk": self.other.pk}))
        self.assertEqual(response.status_code, 404)

    @patch("common.calendar.service.CalendarService.plugins", return_value=[])
    def test_calendar_is_bounded_and_preserves_half_day_metadata(self, _plugins):
        url = reverse("api_v1:employee-calendar", kwargs={"pk": self.employee.pk})
        missing = self.client.get(url)
        response = self.client.get(url, {"from": "2026-09-01", "to": "2026-09-30"})

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(response.status_code, 200)
        event = response.json()[0]
        self.assertEqual(event["kind"], "leave")
        self.assertEqual(event["start"], "2026-09-10T12:00:00")
        self.assertEqual(event["end"], "2026-09-12T12:00:00")
        self.assertEqual(event["metadata"]["start_period"], "MI")
        self.assertEqual(event["metadata"]["end_period"], "MI")

    @patch("common.calendar.service.CalendarService.get_plugin_events")
    def test_calendar_keeps_plugin_events_distinct_from_leave(self, plugin_events):
        plugin_events.return_value = [
            LabsManagerCalendarEvent(
                id="sample:holiday",
                title="Holiday",
                start=date(2026, 9, 15),
                source="sample",
                kind="public_holiday",
            )
        ]
        url = reverse("api_v1:employee-calendar", kwargs={"pk": self.employee.pk})
        response = self.client.get(
            url, {"from": "2026-09-01", "to": "2026-09-30"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {(event["source"], event["kind"]) for event in response.json()},
            {("core", "leave"), ("sample", "public_holiday")},
        )

    @patch("common.calendar.service.CalendarService.get_filters")
    def test_calendar_filter_endpoint_keeps_employee_scope_and_context(
        self, get_filters
    ):
        from common.calendar import LabsManagerCalendarFilter

        get_filters.return_value = [
            LabsManagerCalendarFilter(
                id="sample-value",
                title="Value",
                type="input-text",
                source="sample",
                default="initial",
            )
        ]
        url = reverse(
            "api_v1:employee-calendar-filters", kwargs={"pk": self.employee.pk}
        )

        response = self.client.get(url, {"sample-value": "chosen"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], "sample-value")
        context = get_filters.call_args.args[0]
        self.assertEqual(context.calendar_type.value, "employee")
        self.assertEqual(context.employee_id, self.employee.pk)
        self.assertEqual(context.filters["sample-value"], "chosen")

        hidden_url = reverse(
            "api_v1:employee-calendar-filters", kwargs={"pk": self.other.pk}
        )
        self.assertEqual(self.client.get(hidden_url).status_code, 404)

    @patch("common.calendar.service.CalendarService.get_plugin_events")
    def test_gantt_context_returns_only_plugin_events_with_existing_semantics(self, plugin_events):
        plugin_events.return_value = [LabsManagerCalendarEvent(
            id="sample:holiday", title="Holiday", start=date(2026, 9, 15),
            source="sample", display="background", color="#c9e0cf",
        )]
        url = reverse("api_v1:employee-calendar", kwargs={"pk": self.employee.pk})
        response = self.client.get(url, {
            "context": "employee-gantt", "from": "2026-09-01", "to": "2026-09-30",
            "sample-choice": "visible",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["display"], "background")
        self.assertEqual(response.json()[0]["color"], "#c9e0cf")
        context = plugin_events.call_args.args[0]
        self.assertEqual(context.calendar_type.value, "employee-gantt")
        self.assertEqual(context.filters["sample-choice"], "visible")
        self.assertEqual(self.client.get(url, {"context": "employee-gantt"}).status_code, 400)
        hidden_url = reverse("api_v1:employee-calendar", kwargs={"pk": self.other.pk})
        self.assertEqual(self.client.get(hidden_url, {"context": "employee-gantt", "from": "2026-09-01", "to": "2026-09-30"}).status_code, 404)

    @patch("common.calendar.service.CalendarService.get_filters")
    def test_gantt_filter_context_preserves_employee_access(self, get_filters):
        get_filters.return_value = []
        url = reverse("api_v1:employee-calendar-filters", kwargs={"pk": self.employee.pk})
        self.assertEqual(self.client.get(url, {"context": "employee-gantt"}).status_code, 200)
        self.assertEqual(get_filters.call_args.args[0].calendar_type.value, "employee-gantt")

    def test_anonymous_requests_are_rejected(self):
        self.client.logout()
        url = reverse("api_v1:employee-leaves", kwargs={"pk": self.employee.pk})
        self.assertEqual(self.client.get(url).status_code, 401)
        filters_url = reverse(
            "api_v1:employee-calendar-filters", kwargs={"pk": self.employee.pk}
        )
        self.assertEqual(self.client.get(filters_url).status_code, 401)


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

    def test_complete_filters_intersect_with_project_membership_and_temporal_status(self):
        user = self.create_user("complete-filter-viewer")
        self.grant_global_view(user)
        leader = self.create_employee("Alice", "Leader", is_active=True)
        member = self.create_employee("Bea", "Member", is_active=True)
        outsider = self.create_employee("Cara", "Outside", is_active=False)
        old_type = Employee_Type.objects.create(shortname="OLD-F", name="Former role")
        current_type = Employee_Type.objects.create(shortname="NOW-F", name="Current role")
        Employee_Status.objects.create(employee=member, type=old_type, end_date=date.today() - timedelta(days=1))
        Employee_Status.objects.create(employee=member, type=current_type)
        Employee_Status.objects.create(employee=member, type=current_type)
        Employee_Status.objects.create(employee=leader, type=current_type)
        Employee_Superior.objects.create(employee=member, superior=leader)
        team = Team.objects.create(name="Project team", leader=leader)
        TeamMate.objects.create(team=team, employee=member, end_date=date.today() - timedelta(days=1))
        project = Project.objects.create(name="Filtered Project")
        Participant.objects.create(project=project, employee=leader, status="l")
        Participant.objects.create(project=project, employee=member, status="p")
        self.login(user)

        self.assertEqual(self.result_ids(self.client.get(self.url, {"search": "Bea"})), [member.pk])
        self.assertEqual(self.result_ids(self.client.get(self.url, {"is_active": "false"})), [outsider.pk])
        self.assertEqual(self.result_ids(self.client.get(self.url, {"status": old_type.pk})), [member.pk])
        self.assertEqual(self.client.get(self.url, {"current_status": old_type.pk}).json()["count"], 0)
        self.assertEqual(set(self.result_ids(self.client.get(self.url, {"team": team.pk}))), {leader.pk, member.pk})
        self.assertEqual(set(self.result_ids(self.client.get(self.url, {"project": project.pk}))), {leader.pk, member.pk})
        self.assertEqual(self.result_ids(self.client.get(self.url, {"superior": leader.pk})), [member.pk])
        combined = self.client.get(self.url, {"is_active": "true", "current_status": current_type.pk,
                                              "team": team.pk, "project": project.pk, "superior": leader.pk})
        self.assertEqual(self.result_ids(combined), [member.pk])
        self.assertEqual(combined.json()["count"], 1)
        self.assertEqual(self.result_ids(self.client.get(self.url, {"status": old_type.pk, "superior": leader.pk})), [member.pk])
        page = self.client.get(self.url, {"current_status": current_type.pk, "ordering": "-first_name", "limit": 1})
        self.assertEqual(page.json()["count"], 2)
        self.assertEqual(self.result_ids(page), [member.pk])
        self.assertIsNotNone(page.json()["next"])
        self.assertEqual(self.result_ids(self.client.get(self.url, {"current_status": current_type.pk,
                                                                  "ordering": "-first_name", "limit": 1, "offset": 1})), [leader.pk])

    def test_filter_options_are_bounded_to_visible_employees(self):
        user = self.create_user("filter-options-viewer")
        own = self.create_employee("Own", "Employee", user=user)
        hidden = self.create_employee("Hidden", "Employee")
        visible_type = Employee_Type.objects.create(shortname="VIS-F", name="Visible role")
        hidden_type = Employee_Type.objects.create(shortname="HID-F", name="Hidden role")
        Employee_Status.objects.create(employee=own, type=visible_type)
        Employee_Status.objects.create(employee=hidden, type=hidden_type)
        Team.objects.create(name="Visible team", leader=own)
        Team.objects.create(name="Hidden team", leader=hidden)
        self.login(user)
        response = self.client.get(reverse("api_v1:employee-filter-options"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.json()["statuses"]], ["Visible role"])
        self.assertEqual([item["name"] for item in response.json()["teams"]], ["Visible team"])

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
                "admin_url",
                "first_name",
                "last_name",
                "entry_date",
                "exit_date",
                "is_active",
                "current_statuses",
                "superiors",
                "capabilities",
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

    def test_staff_without_global_change_can_edit_employee(self):
        user = self.create_user("staff-editor")
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        employee = self.create_employee("Staff", "Target")
        self.login(user)

        detail = self.client.get(self.detail_url(employee.pk))
        self.assertEqual(detail.status_code, 200)
        self.assertTrue(detail.json()["capabilities"]["can_change"])
        listed = self.client.get(self.list_url)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["results"][0]["id"], employee.pk)
        self.assertTrue(listed.json()["results"][0]["capabilities"]["can_change"])
        response = self.client.patch(self.detail_url(employee.pk), {"email": "new@example.test"})
        self.assertEqual(response.status_code, 200)
        employee.refresh_from_db()
        self.assertEqual(employee.email, "new@example.test")

    def test_superuser_can_edit_employee(self):
        user = self.create_user("super-editor")
        user.is_superuser = True
        user.save(update_fields=["is_superuser"])
        employee = self.create_employee("Super", "Target")
        self.login(user)

        self.assertTrue(self.client.get(self.detail_url(employee.pk)).json()["capabilities"]["can_change"])
        self.assertEqual(self.client.patch(self.detail_url(employee.pk), {"is_active": False}).status_code, 200)
        employee.refresh_from_db()
        self.assertFalse(employee.is_active)

    def test_global_change_and_explicit_self_edit_remain_authorized(self):
        global_user = self.create_user("global-editor")
        global_user.user_permissions.add(Permission.objects.get(content_type__app_label="staff", codename="change_employee"))
        target = self.create_employee("Global", "Target")
        self.login(global_user)
        self.assertTrue(self.client.get(self.detail_url(target.pk)).json()["capabilities"]["can_change"])
        self.assertEqual(self.client.patch(self.detail_url(target.pk), {"email": "global@example.test"}).status_code, 200)

        self_user = self.create_user("self-editor")
        self_user.user_permissions.add(Permission.objects.get(content_type__app_label="common", codename="self_edit"))
        own = self.create_employee("Self", "Editor", user=self_user)
        self.login(self_user)
        self.assertTrue(self.client.get(self.detail_url(own.pk)).json()["capabilities"]["can_change"])
        self.assertEqual(self.client.patch(self.detail_url(own.pk), {"email": "self@example.test"}).status_code, 200)

    def test_subordinate_edit_uses_existing_change_rule(self):
        user = self.create_user("superior-editor")
        superior = self.create_employee("Superior", "Person", user=user)
        subordinate = self.create_employee("Subordinate", "Person")
        Employee_Superior.objects.create(employee=subordinate, superior=superior)
        self.login(user)

        can_change = user.has_perm("staff.change_employee", subordinate)
        self.assertTrue(can_change)
        self.assertEqual(self.client.get(self.detail_url(subordinate.pk)).json()["capabilities"]["can_change"], can_change)
        response = self.client.patch(self.detail_url(subordinate.pk), {"email": "sub@example.test"})
        self.assertEqual(response.status_code, 200)

    def test_visible_reader_cannot_edit_employee(self):
        user = self.create_user("detail-reader")
        employee = self.create_employee("Read", "Only")
        self.grant_global_view(user)
        self.login(user)

        self.assertFalse(self.client.get(self.detail_url(employee.pk)).json()["capabilities"]["can_change"])
        response = self.client.patch(self.detail_url(employee.pk), {"email": "forbidden@example.test"})
        self.assertEqual(response.status_code, 403)
        employee.refresh_from_db()
        self.assertIsNone(employee.email)

    def test_edit_validates_dates_and_does_not_edit_identity(self):
        user = self.create_user("staff-validator")
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        employee = self.create_employee("Original", "Name", entry_date=date(2025, 1, 1))
        self.login(user)

        invalid = self.client.patch(self.detail_url(employee.pk), {"exit_date": "2024-01-01"})
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("exit_date", invalid.json())
        valid = self.client.patch(self.detail_url(employee.pk), {"email": "valid@example.test", "first_name": "Changed"})
        self.assertEqual(valid.status_code, 200)
        employee.refresh_from_db()
        self.assertEqual(employee.first_name, "Original")
        self.assertEqual(employee.email, "valid@example.test")

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

    def test_detail_contract_extends_list_with_summary_fields_only(self):
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

        milestones = MagicMock()
        milestones.count.return_value = 3
        with (
            patch.object(Employee, "contracts_quotity", return_value=Decimal("0.500")),
            patch.object(Employee, "projects_quotity", return_value=Decimal("0.250")),
            patch.object(Employee, "contribution_quotity", return_value=None),
            patch.object(Employee, "active_milestones", return_value=milestones),
        ):
            detail_response = self.client.get(self.detail_url(employee.pk))
        list_response = self.client.get(self.list_url, {"search": "Bob"})

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(
            list_response.json()["results"][0]["id"],
            detail_response.json()["id"],
        )
        self.assertEqual(
            set(detail_response.json()),
            {
                "id",
                "admin_url",
                "first_name",
                "last_name",
                "entry_date",
                "exit_date",
                "is_active",
                "current_statuses",
                "superiors",
                "birth_date",
                "email",
                "contract_quotity",
                "project_quotity",
                "contribution_quotity",
                "active_milestones_count",
                "capabilities",
            },
        )
        self.assertEqual(detail_response.json()["birth_date"], "1990-03-04")
        self.assertEqual(detail_response.json()["email"], "bob@example.com")
        self.assertEqual(detail_response.json()["contract_quotity"], "0.500")
        self.assertEqual(detail_response.json()["project_quotity"], "0.250")
        self.assertIsNone(detail_response.json()["contribution_quotity"])
        self.assertEqual(detail_response.json()["active_milestones_count"], 3)
        self.assertNotIn("user", detail_response.json())
        self.assertNotIn("email", list_response.json()["results"][0])


@override_settings(
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
)
class EmployeeGenericInfoV1ApiTests(APITestCase):
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

    def url(self, employee_id):
        return reverse("api_v1:employee-generic-info", kwargs={"pk": employee_id})

    def login(self, user):
        self.assertTrue(self.client.login(username=user.username, password="test-password"))

    def grant_global_view(self, user):
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="staff",
                codename="view_employee",
            )
        )

    def test_visible_employee_generic_info_contract_is_read_only(self):
        user = self.create_user("generic-info-viewer")
        employee = self.create_employee("Generic", "Target")
        phone = GenericInfoType.objects.create(
            name="Téléphone",
            icon="style:fas,icon:phone",
        )
        info = GenericInfo.objects.create(
            employee=employee,
            info=phone,
            value="01 02 03 04 05",
        )
        self.grant_global_view(user)
        self.login(user)

        response = self.client.get(self.url(employee.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["items"],
            [{
                "id": info.pk,
                "type": {
                    "id": phone.pk,
                    "name": "Téléphone",
                    "icon": "style:fas,icon:phone",
                },
                "value": "01 02 03 04 05",
            }],
        )

    def test_visible_employee_without_generic_info_returns_empty_collection(self):
        user = self.create_user("empty-generic-info")
        employee = self.create_employee("Empty", "Info", user=user)
        self.login(user)

        response = self.client.get(self.url(employee.pk))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])

    def test_unknown_or_out_of_scope_employee_returns_not_found(self):
        user = self.create_user("hidden-generic-info")
        self.create_employee("Own", "Employee", user=user)
        hidden = self.create_employee("Hidden", "Employee")
        self.login(user)

        self.assertEqual(self.client.get(self.url(hidden.pk)).status_code, 404)
        self.assertEqual(self.client.get(self.url(999999)).status_code, 404)


@override_settings(
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
)
class EmployeeMilestoneV1ApiTests(APITestCase):
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

    def create_milestone(self, project, name, employees, **fields):
        milestone = Milestones.objects.create(
            project=project,
            name=name,
            **fields,
        )
        milestone.employee.set(employees)
        return milestone

    def url(self, employee_id):
        return reverse("api_v1:employee-milestones", kwargs={"pk": employee_id})

    def login(self, user):
        self.assertTrue(
            self.client.login(username=user.username, password="test-password")
        )

    def test_context_returns_all_assigned_milestones_without_expanding_scopes(self):
        user = self.create_user("milestone-context-viewer")
        viewer = self.create_employee("Alice", "Manager", user=user)
        target = self.create_employee("Bob", "Visible")
        hidden_colleague = self.create_employee("Cara", "Hidden")
        Employee_Superior.objects.create(
            employee=target,
            superior=viewer,
        )
        visible_project = Project.objects.create(name="Visible project")
        hidden_project = Project.objects.create(name="Context only project")
        Participant.objects.create(project=visible_project, employee=viewer)
        visible = self.create_milestone(
            visible_project,
            "Visible task",
            [target],
            start_date=date.today(),
        )
        contextual = self.create_milestone(
            hidden_project,
            "Contextual milestone",
            [target, viewer, hidden_colleague],
            desc="Full contextual description",
            type="q",
            quotity=Decimal("0.650"),
        )
        self.login(user)

        response = self.client.get(self.url(target.pk))

        self.assertEqual(response.status_code, 200)
        by_id = {item["id"]: item for item in response.json()}
        self.assertEqual(set(by_id), {visible.pk, contextual.pk})
        self.assertTrue(by_id[visible.pk]["project"]["can_view"])
        self.assertFalse(by_id[contextual.pk]["project"]["can_view"])
        self.assertEqual(by_id[visible.pk]["work_kind"], "task")
        self.assertEqual(by_id[contextual.pk]["work_kind"], "milestone")
        self.assertEqual(by_id[contextual.pk]["quotity"], "0.650")
        employee_visibility = {
            item["id"]: item["can_view"]
            for item in by_id[contextual.pk]["employees"]
        }
        self.assertEqual(
            employee_visibility,
            {
                target.pk: True,
                viewer.pk: True,
                hidden_colleague.pk: False,
            },
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "api_v1:employee-detail",
                    kwargs={"pk": hidden_colleague.pk},
                )
            ).status_code,
            404,
        )

    def test_classification_uses_viewer_due_soon_setting_and_strict_order(self):
        today = date.today()
        user = self.create_user("milestone-state-viewer")
        target = self.create_employee("State", "Viewer", user=user)
        project = Project.objects.create(name="State project")
        LMUserSetting.objects.create(
            key="NOTIFICATION_ENDPOINTS_MILESTONES_STALE",
            value="3",
            user=user,
        )
        milestones = {
            "completed": self.create_milestone(
                project,
                "Completed",
                [target],
                status=True,
                end_date=today - timedelta(days=5),
            ),
            "overdue": self.create_milestone(
                project,
                "Overdue",
                [target],
                end_date=today - timedelta(days=2),
            ),
            "due_soon": self.create_milestone(
                project,
                "Due boundary",
                [target],
                end_date=today + timedelta(days=3),
            ),
            "planned": self.create_milestone(
                project,
                "Planned",
                [target],
                start_date=today + timedelta(days=4),
            ),
            "in_progress": self.create_milestone(
                project,
                "In progress",
                [target],
                start_date=today - timedelta(days=1),
                end_date=today + timedelta(days=4),
            ),
        }
        self.login(user)

        response = self.client.get(self.url(target.pk))

        self.assertEqual(response.status_code, 200)
        by_name = {item["name"]: item for item in response.json()}
        for expected_state, milestone in milestones.items():
            self.assertEqual(
                by_name[milestone.name]["display_state"],
                expected_state,
            )
        self.assertEqual(by_name["Overdue"]["days_to_due"], -2)
        self.assertEqual(by_name["Due boundary"]["days_to_due"], 3)
        self.assertIsNone(by_name["Planned"]["days_to_due"])

    def test_planning_filters_apply_inside_authorized_employee_scope(self):
        user = self.create_user("milestone-filter-viewer")
        target = self.create_employee("Filter", "Owner", user=user)
        hidden = self.create_employee("Other", "Employee")
        project = Project.objects.create(name="Planning filters")
        task = self.create_milestone(project, "Report task", [target], start_date=date.today())
        milestone = self.create_milestone(project, "Report milestone", [target])
        self.create_milestone(project, "Report hidden", [hidden], start_date=date.today())
        self.login(user)

        tasks = self.client.get(self.url(target.pk), {"search": "report", "kind": "task"})
        points = self.client.get(self.url(target.pk), {"search": "report", "kind": "milestone"})

        self.assertEqual(tasks.status_code, 200)
        self.assertEqual([item["id"] for item in tasks.json()], [task.pk])
        self.assertEqual([item["id"] for item in points.json()], [milestone.pk])
        self.assertEqual(self.client.get(self.url(hidden.pk), {"search": "report"}).status_code, 404)

    def test_unknown_and_out_of_scope_employee_are_both_not_found(self):
        user = self.create_user("milestone-hidden-viewer")
        self.create_employee("Own", "Employee", user=user)
        hidden = self.create_employee("Hidden", "Employee")
        self.login(user)

        self.assertEqual(self.client.get(self.url(hidden.pk)).status_code, 404)
        self.assertEqual(self.client.get(self.url(999999)).status_code, 404)


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
            {"superiors": [], "subordinates": [], "capabilities": {"can_add": False, "can_change": False, "can_delete": False}},
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
                        "can_view": True,
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
                        "can_view": True,
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
                        "can_view": True,
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
                        "can_view": True,
                    },
                ],
                "capabilities": {"can_add": False, "can_change": False, "can_delete": False},
            },
        )
        for collection in (response.json()["superiors"], response.json()["subordinates"]):
            for item in collection:
                self.assertEqual(
                    set(item),
                    {"id", "employee", "start_date", "end_date", "is_active", "can_view"},
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
                    "can_view": False,
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
        self.assertFalse(response.json()[0]["project"]["can_view"])
        self.assertFalse(user.has_perm("project.view_project", project))

    def test_project_reference_reports_independent_view_permission(self):
        user = self.create_user("participation-project-viewer")
        viewer = self.create_employee("Project", "Viewer", user=user)
        target = self.create_employee("Project", "Target")
        Employee_Superior.objects.create(employee=target, superior=viewer)
        visible_project = self.create_project("Visible project")
        hidden_project = self.create_project("Context only project")
        self.create_participation(viewer, visible_project)
        self.create_participation(target, visible_project)
        self.create_participation(target, hidden_project)
        self.login(user)

        response = self.client.get(self.participations_url(target.pk))

        self.assertEqual(response.status_code, 200)
        by_project = {item["project"]["id"]: item["project"] for item in response.json()}
        self.assertTrue(by_project[visible_project.pk]["can_view"])
        self.assertFalse(by_project[hidden_project.pk]["can_view"])

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
                    "can_view": False,
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
                {"id", "name", "start_date", "end_date", "can_view"},
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


@override_settings(
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
)
class EmployeeProjectWorkloadV1ApiTests(APITestCase):
    def create_user(self, username):
        return get_user_model().objects.create_user(username=username, password="test-password")

    def create_employee(self, first_name, last_name, user=None):
        return Employee.objects.create(first_name=first_name, last_name=last_name, user=user)

    def create_project(self, name):
        return Project.objects.create(name=name)

    def create_participation(self, employee, project, **fields):
        return Participant.objects.create(employee=employee, project=project, **fields)

    def login(self, user):
        self.assertTrue(self.client.login(username=user.username, password="test-password"))

    def url(self, employee_id):
        return reverse("api_v1:employee-project-workload", kwargs={"pk": employee_id})

    def bounded(self, employee_id, start="2026-01-01", end="2026-01-31"):
        return self.client.get(self.url(employee_id), {"start": start, "end": end})

    def test_visible_employee_and_out_of_scope_employee(self):
        user = self.create_user("workload-scope")
        visible = self.create_employee("Visible", "Employee", user=user)
        hidden = self.create_employee("Hidden", "Employee")
        self.login(user)

        self.assertEqual(self.bounded(visible.pk).status_code, 200)
        self.assertEqual(self.bounded(hidden.pk).status_code, 404)

    def test_contextual_projects_are_all_returned_with_independent_can_view(self):
        user = self.create_user("workload-project-scope")
        viewer = self.create_employee("Project", "Viewer", user=user)
        employee = self.create_employee("Project", "Scope")
        Employee_Superior.objects.create(employee=employee, superior=viewer)
        visible_project = self.create_project("Visible project")
        hidden_project = self.create_project("Hidden project")
        self.create_participation(viewer, visible_project, quotity="0.100")
        self.create_participation(employee, visible_project, quotity="0.400")
        self.create_participation(employee, hidden_project, quotity="0.300")
        self.login(user)

        response = self.bounded(employee.pk)

        self.assertEqual(response.status_code, 200)
        projects = response.json()["segments"][0]["projects"]
        self.assertEqual({item["id"] for item in projects}, {visible_project.pk, hidden_project.pk})
        by_id = {item["id"]: item for item in projects}
        self.assertTrue(by_id[visible_project.pk]["can_view"])
        self.assertFalse(by_id[hidden_project.pk]["can_view"])

    def test_intersection_overlap_aggregation_and_zero_periods(self):
        user = self.create_user("workload-segments")
        employee = self.create_employee("Segment", "Employee", user=user)
        alpha = self.create_project("Alpha")
        beta = self.create_project("Beta")
        outside = self.create_project("Outside")
        self.create_participation(employee, alpha, start_date=date(2026, 1, 5), end_date=date(2026, 1, 15), quotity="0.600")
        self.create_participation(employee, alpha, start_date=date(2026, 1, 10), end_date=date(2026, 1, 20), quotity="0.400")
        self.create_participation(employee, beta, start_date=date(2026, 1, 10), end_date=date(2026, 1, 12), quotity="0.500")
        self.create_participation(employee, outside, end_date=date(2025, 12, 31), quotity="1.000")
        self.login(user)

        response = self.bounded(employee.pk)

        self.assertEqual(response.status_code, 200)
        segments = response.json()["segments"]
        self.assertEqual([(item["start"], item["end"]) for item in segments], [
            ("2026-01-01", "2026-01-04"),
            ("2026-01-05", "2026-01-09"),
            ("2026-01-10", "2026-01-12"),
            ("2026-01-13", "2026-01-15"),
            ("2026-01-16", "2026-01-20"),
            ("2026-01-21", "2026-01-31"),
        ])
        self.assertEqual([item["total_quotity"] for item in segments], ["0", "0.600", "1.500", "1.000", "0.400", "0"])
        peak = segments[2]
        self.assertEqual(next(item["quotity"] for item in peak["projects"] if item["id"] == alpha.pk), "1.000")
        for segment in segments:
            self.assertEqual(Decimal(segment["total_quotity"]), sum((Decimal(item["quotity"]) for item in segment["projects"]), Decimal("0")))
        self.assertNotIn(outside.pk, {item["id"] for segment in segments for item in segment["projects"]})

    def test_open_dates_follow_active_date_semantics_in_bounded_window(self):
        user = self.create_user("workload-open-dates")
        employee = self.create_employee("Open", "Dates", user=user)
        project = self.create_project("Always")
        self.create_participation(employee, project, end_date=date(2026, 1, 10), quotity="0.300")
        self.create_participation(employee, project, start_date=date(2026, 1, 20), quotity="0.700")
        self.login(user)

        segments = self.bounded(employee.pk).json()["segments"]

        self.assertEqual([(item["start"], item["end"], item["total_quotity"]) for item in segments], [
            ("2026-01-01", "2026-01-10", "0.300"),
            ("2026-01-11", "2026-01-19", "0"),
            ("2026-01-20", "2026-01-31", "0.700"),
        ])

    def test_invalid_and_ambiguous_ranges_are_rejected(self):
        user = self.create_user("workload-invalid")
        employee = self.create_employee("Invalid", "Range", user=user)
        self.login(user)

        requests = [
            {},
            {"start": "2026-01-01"},
            {"start": "bad", "end": "2026-01-31"},
            {"start": "2026-02-01", "end": "2026-01-31"},
            {"range": "all", "start": "2026-01-01"},
            {"range": "unknown"},
        ]
        for params in requests:
            with self.subTest(params=params):
                self.assertEqual(self.client.get(self.url(employee.pk), params).status_code, 400)

    def test_range_all_preserves_open_bounds_without_invented_dates(self):
        user = self.create_user("workload-all-open")
        viewer = self.create_employee("All", "Viewer", user=user)
        employee = self.create_employee("All", "Open")
        Employee_Superior.objects.create(employee=employee, superior=viewer)
        project = self.create_project("Open project")
        self.create_participation(employee, project, quotity="1.200")
        self.login(user)

        response = self.client.get(self.url(employee.pk), {"range": "all"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["range"], {"start": None, "end": None})
        self.assertEqual(response.json()["segments"], [{
            "start": None,
            "end": None,
            "total_quotity": "1.200",
            "projects": [{
                "id": project.pk,
                "name": "Open project",
                "quotity": "1.200",
                "can_view": False,
            }],
        }])

    def test_range_all_uses_natural_finite_extent_and_exact_boundaries(self):
        user = self.create_user("workload-all-finite")
        employee = self.create_employee("All", "Finite", user=user)
        project = self.create_project("Finite project")
        self.create_participation(employee, project, start_date=date(2024, 2, 1), end_date=date(2024, 2, 29), quotity="1.000")
        self.login(user)

        response = self.client.get(self.url(employee.pk), {"range": "all"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["range"], {"start": "2024-02-01", "end": "2024-02-29"})
        self.assertEqual(response.json()["segments"][0]["start"], "2024-02-01")
        self.assertEqual(response.json()["segments"][0]["end"], "2024-02-29")


@override_settings(
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
)
class EmployeeContributionV1ApiTests(APITestCase):
    def setUp(self):
        self.today = date.today()
        self.hr_root = Cost_Type.objects.create(
            short_name="HR", name="Human resources", is_hr=True
        )
        self.hr_child = Cost_Type.objects.create(
            short_name="SAL", name="Salary", parent=self.hr_root, is_hr=False
        )
        self.employee_type = Employee_Type.objects.create(
            shortname="RES", name="Researcher"
        )
        self.contract_type = Contract_type.objects.create(name="Permanent")

    def create_user(self, username):
        return get_user_model().objects.create_user(
            username=username, password="test-password"
        )

    def create_employee(self, first_name, last_name, user=None):
        return Employee.objects.create(
            first_name=first_name, last_name=last_name, user=user
        )

    def create_fund(self, name):
        project = Project.objects.create(name=f"{name} project")
        funder = Fund_Institution.objects.create(
            short_name=f"F{name[:4]}", name=f"{name} funder"
        )
        institution = Institution.objects.create(
            short_name=f"I{name[:4]}", name=f"{name} institution"
        )
        return Fund.objects.create(
            project=project,
            funder=funder,
            institution=institution,
            ref=f"REF-{name}",
        )

    def create_contribution(self, employee, fund, **fields):
        contribution = Contribution.objects.create(
            employee=employee,
            fund=fund,
            cost_type=self.hr_child,
            **fields,
        )
        return contribution

    def login(self, user):
        self.assertTrue(
            self.client.login(username=user.username, password="test-password")
        )

    def grant_global_employee_view(self, user):
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="staff", codename="view_employee"
            )
        )

    def list_url(self, employee):
        return reverse("api_v1:employee-contributions", kwargs={"pk": employee.pk})

    def workload_url(self, employee):
        return reverse(
            "api_v1:employee-contribution-workload", kwargs={"pk": employee.pk}
        )

    def bounded(self, employee, start="2026-01-01", end="2026-01-31"):
        return self.client.get(
            self.workload_url(employee), {"start": start, "end": end}
        )

    def test_employee_gate_and_contextual_collection_prevent_cross_employee_leaks(self):
        user = self.create_user("contribution-scope")
        own = self.create_employee("Own", "Employee", user=user)
        hidden = self.create_employee("Hidden", "Employee")
        own_contribution = self.create_contribution(
            own, self.create_fund("Own"), quotity=Decimal("0.200")
        )
        hidden_contribution = self.create_contribution(
            hidden, self.create_fund("Hidden"), quotity=Decimal("0.900")
        )
        self.login(user)

        self.assertEqual(self.client.get(self.list_url(hidden)).status_code, 404)
        self.grant_global_employee_view(user)

        response = self.client.get(self.list_url(own))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [own_contribution.pk])
        self.assertNotIn(hidden_contribution.pk, [item["id"] for item in response.json()])

    def test_list_serializes_relations_hr_descendant_and_temporal_states(self):
        user = self.create_user("contribution-list")
        employee = self.create_employee("List", "Employee", user=user)
        fund = self.create_fund("List")
        current = self.create_contribution(
            employee,
            fund,
            start_date=None,
            end_date=None,
            quotity=Decimal("0.500"),
            amount=Decimal("12000.00"),
            desc="Salary valorisation",
            emp_type=self.employee_type,
        )
        current.contract_type.add(self.contract_type)
        future = self.create_contribution(
            employee,
            fund,
            start_date=self.today + timedelta(days=1),
            quotity=Decimal("0.250"),
        )
        past = self.create_contribution(
            employee,
            fund,
            end_date=self.today - timedelta(days=1),
            quotity=Decimal("0.100"),
        )
        self.login(user)

        response = self.client.get(self.list_url(employee))

        self.assertEqual(response.status_code, 200)
        by_id = {item["id"]: item for item in response.json()}
        self.assertEqual(by_id[current.pk]["temporal_state"], "current")
        self.assertEqual(by_id[future.pk]["temporal_state"], "future")
        self.assertEqual(by_id[past.pk]["temporal_state"], "past")
        self.assertTrue(by_id[current.pk]["cost_type"]["is_hr"])
        self.assertEqual(by_id[current.pk]["fund"]["project"]["name"], fund.project.name)
        self.assertEqual(by_id[current.pk]["employee_type"]["code"], "RES")
        self.assertEqual(by_id[current.pk]["contract_types"][0]["name"], "Permanent")
        self.assertEqual(by_id[current.pk]["amount"], "12000.00")

    def test_workload_aggregates_overlaps_and_excludes_other_employee(self):
        user = self.create_user("contribution-workload")
        employee = self.create_employee("Timeline", "Employee", user=user)
        other = self.create_employee("Other", "Employee")
        alpha = self.create_fund("Alpha")
        beta = self.create_fund("Beta")
        self.create_contribution(
            employee,
            alpha,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 20),
            quotity=Decimal("0.600"),
        )
        self.create_contribution(
            employee,
            beta,
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 31),
            quotity=Decimal("0.700"),
        )
        leaked = self.create_contribution(
            other,
            self.create_fund("Leak"),
            quotity=Decimal("1.000"),
        )
        self.login(user)

        response = self.bounded(employee)

        self.assertEqual(response.status_code, 200)
        segments = response.json()["segments"]
        self.assertEqual(
            [(item["start"], item["end"], item["total_quotity"]) for item in segments],
            [
                ("2026-01-01", "2026-01-09", "0.600"),
                ("2026-01-10", "2026-01-20", "1.300"),
                ("2026-01-21", "2026-01-31", "0.700"),
            ],
        )
        ids = {
            item["id"]
            for segment in segments
            for item in segment["contributions"]
        }
        self.assertNotIn(leaked.pk, ids)

    def test_workload_preserves_open_bounds(self):
        user = self.create_user("contribution-open")
        employee = self.create_employee("Open", "Employee", user=user)
        contribution = self.create_contribution(
            employee,
            self.create_fund("Open"),
            start_date=None,
            end_date=None,
            quotity=Decimal("0.400"),
        )
        self.login(user)

        response = self.client.get(self.workload_url(employee), {"range": "all"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["range"], {"start": None, "end": None})
        self.assertEqual(response.json()["segments"][0]["start"], None)
        self.assertEqual(response.json()["segments"][0]["end"], None)
        self.assertEqual(response.json()["segments"][0]["total_quotity"], "0.400")
        self.assertEqual(
            response.json()["segments"][0]["contributions"][0]["id"],
            contribution.pk,
        )


@override_settings(
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
)
class EmployeeBudgetV1ApiTests(APITestCase):
    def setUp(self):
        self.hr_root = Cost_Type.objects.create(
            short_name="HRB", name="HR budgets", is_hr=True
        )
        self.hr_child = Cost_Type.objects.create(
            short_name="PAY", name="Personnel", parent=self.hr_root, is_hr=False
        )
        self.employee_type = Employee_Type.objects.create(
            shortname="ENG", name="Engineer"
        )
        self.contract_type = Contract_type.objects.create(name="Fixed term")

    def create_user(self, username):
        return get_user_model().objects.create_user(
            username=username, password="test-password"
        )

    def create_employee(self, first_name, last_name, user=None):
        return Employee.objects.create(
            first_name=first_name, last_name=last_name, user=user
        )

    def create_fund(self, name):
        project = Project.objects.create(name=f"{name} project")
        funder = Fund_Institution.objects.create(
            short_name=f"F{name[:4]}", name=f"{name} funder"
        )
        institution = Institution.objects.create(
            short_name=f"I{name[:4]}", name=f"{name} institution"
        )
        return Fund.objects.create(
            project=project,
            funder=funder,
            institution=institution,
            ref=f"REF-{name}",
        )

    def create_budget(self, employee, fund, **fields):
        return Budget.objects.create(
            employee=employee,
            fund=fund,
            cost_type=self.hr_child,
            **fields,
        )

    def login(self, user):
        self.assertTrue(
            self.client.login(username=user.username, password="test-password")
        )

    def grant_global_employee_view(self, user):
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="staff", codename="view_employee"
            )
        )

    def url(self, employee):
        return reverse("api_v1:employee-budgets", kwargs={"pk": employee.pk})

    def test_employee_gate_and_contextual_collection_prevent_cross_employee_leaks(self):
        user = self.create_user("budget-scope")
        own = self.create_employee("Own", "Employee", user=user)
        other = self.create_employee("Other", "Visible")
        own_budget = self.create_budget(own, self.create_fund("Own"))
        other_budget = self.create_budget(other, self.create_fund("Other"))
        self.login(user)

        self.assertEqual(self.client.get(self.url(other)).status_code, 404)
        self.grant_global_employee_view(user)

        response = self.client.get(self.url(own))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [own_budget.pk])
        self.assertNotIn(other_budget.pk, [item["id"] for item in response.json()])

    def test_hr_descendant_relations_and_normal_financial_values(self):
        user = self.create_user("budget-normal")
        employee = self.create_employee("Budget", "Employee", user=user)
        fund = self.create_fund("Normal")
        budget = self.create_budget(
            employee,
            fund,
            emp_type=self.employee_type,
            quotity=Decimal("0.500"),
            desc="Research engineer",
            amount=Decimal("80000.00"),
            expense=Decimal("54000.00"),
        )
        budget.contract_type.add(self.contract_type)
        self.login(user)

        response = self.client.get(self.url(employee))

        self.assertEqual(response.status_code, 200)
        item = response.json()[0]
        self.assertEqual(item["fund"]["project"]["name"], fund.project.name)
        self.assertTrue(item["cost_type"]["is_hr"])
        self.assertEqual(item["employee_type"]["code"], "ENG")
        self.assertEqual(item["contract_types"][0]["name"], "Fixed term")
        self.assertEqual(item["amount"], "80000.00")
        self.assertEqual(item["consumed"], "54000.00")
        self.assertEqual(item["available"], "26000.00")
        self.assertEqual(item["consumption_ratio"], "0.675")
        self.assertNotIn("expense", item)
        self.assertEqual(budget.available, Decimal("26000.00"))
        self.assertEqual(budget.get_consumption_ratio(), Decimal("0.675"))

    def test_zero_and_null_amounts_do_not_invent_ratios(self):
        user = self.create_user("budget-non-calculable")
        employee = self.create_employee("Zero", "Budget", user=user)
        fund = self.create_fund("Zero")
        zero = self.create_budget(
            employee,
            fund,
            amount=Decimal("0.00"),
            expense=Decimal("10.00"),
        )
        nulls = self.create_budget(
            employee,
            fund,
            amount=None,
            expense=None,
        )
        self.login(user)

        response = self.client.get(self.url(employee))

        by_id = {item["id"]: item for item in response.json()}
        self.assertEqual(by_id[zero.pk]["consumed"], "10.00")
        self.assertEqual(by_id[zero.pk]["available"], "-10.00")
        self.assertIsNone(by_id[zero.pk]["consumption_ratio"])
        self.assertIsNone(by_id[nulls.pk]["amount"])
        self.assertIsNone(by_id[nulls.pk]["consumed"])
        self.assertIsNone(by_id[nulls.pk]["available"])
        self.assertIsNone(by_id[nulls.pk]["consumption_ratio"])

    def test_overconsumption_keeps_true_ratio_and_negative_available(self):
        user = self.create_user("budget-overrun")
        employee = self.create_employee("Over", "Budget", user=user)
        budget = self.create_budget(
            employee,
            self.create_fund("Overrun"),
            amount=Decimal("100.00"),
            expense=Decimal("112.00"),
        )
        self.login(user)

        item = self.client.get(self.url(employee)).json()[0]

        self.assertEqual(item["id"], budget.pk)
        self.assertEqual(item["consumed"], "112.00")
        self.assertEqual(item["available"], "-12.00")
        self.assertEqual(item["consumption_ratio"], "1.12")

    def test_negative_expense_is_preserved_as_a_refund(self):
        user = self.create_user("budget-refund")
        employee = self.create_employee("Refund", "Budget", user=user)
        budget = self.create_budget(
            employee,
            self.create_fund("Refund"),
            amount=Decimal("40000.00"),
            expense=Decimal("-1000.00"),
        )
        self.login(user)

        item = self.client.get(self.url(employee)).json()[0]

        self.assertEqual(item["id"], budget.pk)
        self.assertEqual(item["consumed"], "-1000.00")
        self.assertEqual(item["available"], "41000.00")
        self.assertEqual(item["consumption_ratio"], "-0.025")
        self.assertEqual(budget.available, Decimal("41000.00"))
        self.assertEqual(budget.get_consumption_ratio(), Decimal("-0.025"))


@override_settings(
    CSRF_COOKIE_SECURE=False,
    SESSION_COOKIE_SECURE=False,
    SECURE_SSL_REDIRECT=False,
)
class EmployeeContractV1ApiTests(APITestCase):
    def setUp(self):
        self.today = date.today()
        self.contract_type = Contract_type.objects.create(name="Doctoral")
        self.cost_type = Cost_Type.objects.create(
            short_name="SAL", name="Salary", is_hr=True
        )

    def create_user(self, username):
        return get_user_model().objects.create_user(
            username=username, password="test-password"
        )

    def create_employee(self, first_name, last_name, user=None):
        return Employee.objects.create(
            first_name=first_name, last_name=last_name, user=user
        )

    def create_fund(self, name, suffix=""):
        project = Project.objects.create(name=f"{name} project {suffix}".strip())
        funder = Fund_Institution.objects.create(
            short_name=f"F{suffix or name[:2]}", name=f"{name} Funder {suffix}".strip()
        )
        institution = Institution.objects.create(
            short_name=f"I{suffix or name[:2]}", name=f"{name} Institution {suffix}".strip()
        )
        return Fund.objects.create(
            project=project,
            funder=funder,
            institution=institution,
            ref=f"REF-{suffix or name}",
        )

    def create_contract(self, employee, fund, **fields):
        return Contract.objects.create(
            employee=employee,
            fund=fund,
            contract_type=self.contract_type,
            **fields,
        )

    def login(self, user):
        self.assertTrue(
            self.client.login(username=user.username, password="test-password")
        )

    def list_url(self, employee):
        return reverse("api_v1:employee-contracts", kwargs={"pk": employee.pk})

    def detail_url(self, employee, contract):
        return reverse(
            "api_v1:employee-contract-detail",
            kwargs={"pk": employee.pk, "contract_pk": contract.pk},
        )

    def grant(self, user, app_label, codename):
        user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label=app_label, codename=codename
            )
        )

    def test_employee_gate_then_contextual_contract_collection(self):
        user = self.create_user("contract-scope")
        own = self.create_employee("Own", "Viewer", user=user)
        hidden = self.create_employee("Hidden", "Employee")
        hidden_contract = self.create_contract(hidden, self.create_fund("Hidden"))
        self.login(user)

        self.assertEqual(self.client.get(self.list_url(hidden)).status_code, 404)
        self.assertEqual(
            self.client.get(self.detail_url(hidden, hidden_contract)).status_code,
            404,
        )

        self.grant(user, "staff", "view_employee")
        response = self.client.get(self.list_url(hidden))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [hidden_contract.pk])
        self.assertEqual(
            self.client.get(self.detail_url(hidden, hidden_contract)).status_code,
            200,
        )
        self.assertNotEqual(own.pk, hidden.pk)

    def test_subordinate_contracts_are_visible_and_classified_from_dates(self):
        user = self.create_user("contract-manager")
        manager = self.create_employee("Line", "Manager", user=user)
        subordinate = self.create_employee("Visible", "Subordinate")
        Employee_Superior.objects.create(employee=subordinate, superior=manager)
        fund = self.create_fund("Scoped")
        current_open = self.create_contract(
            subordinate, fund, start_date=None, end_date=None, is_active=True
        )
        current_ending = self.create_contract(
            subordinate, fund, end_date=self.today + timedelta(days=3), is_active=False
        )
        future = self.create_contract(
            subordinate,
            fund,
            start_date=self.today + timedelta(days=2),
            end_date=self.today + timedelta(days=30),
            status="prov",
        )
        past = self.create_contract(
            subordinate,
            fund,
            start_date=self.today - timedelta(days=30),
            end_date=self.today - timedelta(days=1),
        )
        self.login(user)

        response = self.client.get(self.list_url(subordinate))

        self.assertEqual(response.status_code, 200)
        items = response.json()
        self.assertEqual(
            [item["id"] for item in items],
            [current_ending.pk, current_open.pk, future.pk, past.pk],
        )
        by_id = {item["id"]: item for item in items}
        self.assertEqual(by_id[current_open.pk]["temporal_state"], "current")
        self.assertEqual(by_id[future.pk]["temporal_state"], "future")
        self.assertEqual(by_id[past.pk]["temporal_state"], "past")
        self.assertTrue(by_id[current_open.pk]["requires_follow_up"])
        self.assertFalse(by_id[current_ending.pk]["requires_follow_up"])
        self.assertEqual(by_id[future.pk]["status"]["code"], "prov")

    def test_fund_relations_and_independent_visibility_are_serialized(self):
        user = self.create_user("contract-relations")
        employee = self.create_employee("Relation", "Viewer", user=user)
        fund = self.create_fund("Relation")
        contract = self.create_contract(employee, fund)
        Participant.objects.create(project=fund.project, employee=employee)
        self.login(user)

        without_permission = self.client.get(self.list_url(employee)).json()[0]
        self.assertEqual(without_permission["fund"]["reference"], fund.ref)
        self.assertEqual(without_permission["fund"]["project"]["name"], fund.project.name)
        self.assertTrue(without_permission["fund"]["project"]["can_view"])
        self.assertFalse(without_permission["fund"]["institution"]["can_view"])
        self.assertIsNone(without_permission["fund"]["institution"]["url"])

        self.grant(user, "common", "display_infos")
        with_permission = self.client.get(self.list_url(employee)).json()[0]
        self.assertTrue(with_permission["fund"]["institution"]["can_view"])
        self.assertEqual(
            with_permission["fund"]["institution"]["url"],
            f"/infos/project/institution/{fund.institution_id}",
        )
        self.assertEqual(contract.employee_id, employee.pk)

    def test_detail_loads_only_requested_contract_expenses_and_ignores_status(self):
        user = self.create_user("contract-expenses")
        employee = self.create_employee("Expense", "Viewer", user=user)
        fund = self.create_fund("Expense")
        other_fund = self.create_fund("Other", "2")
        contract = self.create_contract(employee, fund, quotity=Decimal("0.500"))
        other = self.create_contract(employee, other_fund)
        first = Contract_expense.objects.create(
            contract=contract,
            fund_item=fund,
            type=self.cost_type,
            expense_id="PAY-1",
            desc="First salary",
            date=self.today,
            amount=Decimal("120.00"),
            status="e",
        )
        second = Contract_expense.objects.create(
            contract=contract,
            fund_item=fund,
            type=self.cost_type,
            expense_id="PAY-2",
            desc="Correction",
            date=self.today - timedelta(days=1),
            amount=Decimal("-20.00"),
            status="p",
        )
        Contract_expense.objects.create(
            contract=other,
            fund_item=other_fund,
            type=self.cost_type,
            date=self.today,
            amount=Decimal("999.00"),
            status="r",
        )
        self.login(user)

        response = self.client.get(self.detail_url(employee, contract))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["expense_count"], 2)
        self.assertEqual(payload["expense_total"], "100.00")
        self.assertEqual({item["id"] for item in payload["expenses"]}, {first.pk, second.pk})
        self.assertNotIn("status", payload["expenses"][0])
        self.assertEqual(payload["quotity"], "0.500")
