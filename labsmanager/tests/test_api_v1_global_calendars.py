"""Visibility and filter contracts for the two read-only global calendars."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from common.calendar import LabsManagerCalendarEvent
from endpoints.models import Milestones
from fund.models import Cost_Type, Fund, Fund_Institution
from leave.models import Leave, Leave_Type
from plugin.samples.FrenchHollidayPlugin.FrenchHollidayPlugin import FrenchHollidayPlugin
from project.models import Institution, Participant, Project
from staff.models import Employee, Employee_Status, Employee_Type, Team, TeamMate


class GlobalCalendarsV1Tests(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.user = get_user_model().objects.create_user("calendar-viewer")
        self.employee = Employee.objects.create(first_name="Ada", last_name="Viewer", user=self.user)
        self.hidden_employee = Employee.objects.create(first_name="Hidden", last_name="Person")
        self.leave_type = Leave_Type.objects.create(short_name="CP", name="Annual leave")
        self.other_type = Leave_Type.objects.create(short_name="RTT", name="Other leave")
        self.visible_leave = Leave.objects.create(employee=self.employee, type=self.leave_type,
                                                  start_date=self.today, end_date=self.today)
        self.other_leave = Leave.objects.create(employee=self.employee, type=self.other_type,
                                                start_date=self.today, end_date=self.today)
        Leave.objects.create(employee=self.hidden_employee, type=self.leave_type,
                             start_date=self.today, end_date=self.today)
        self.status = Employee_Type.objects.create(shortname="STA", name="Staff")
        self.other_status = Employee_Type.objects.create(shortname="EXT", name="External")
        Employee_Status.objects.create(employee=self.employee, type=self.status,
                                       start_date=self.today - timedelta(days=2))
        self.team = Team.objects.create(name="Visible team", leader=self.employee)
        self.other_team = Team.objects.create(name="Other team", leader=self.hidden_employee)
        TeamMate.objects.create(team=self.team, employee=self.employee)
        self.project = Project.objects.create(name="Visible Project", start_date=self.today - timedelta(days=10),
                                              end_date=self.today + timedelta(days=30), status=True)
        self.hidden_project = Project.objects.create(name="Hidden Project")
        Participant.objects.create(project=self.project, employee=self.employee, status="l")
        self.institution = Institution.objects.create(name="Institution", short_name="INST")
        self.funder = Fund_Institution.objects.create(name="Funder", short_name="FND")
        Cost_Type.objects.create(name="Human resources", short_name="HR")
        self.fund = Fund.objects.create(project=self.project, institution=self.institution, funder=self.funder,
                                        start_date=self.today - timedelta(days=5),
                                        end_date=self.today + timedelta(days=25), ref="V-1")
        self.task = Milestones.objects.create(project=self.project, name="Visible task", status=False,
                                              start_date=self.today - timedelta(days=1),
                                              end_date=self.today + timedelta(days=5))
        Milestones.objects.create(project=self.hidden_project, name="Secret task",
                                  start_date=self.today, end_date=self.today)
        self.client.force_login(self.user)

    def range(self, **filters):
        return {"from": str(self.today - timedelta(days=10)),
                "to": str(self.today + timedelta(days=40)), **filters}

    @patch("common.calendar.service.CalendarService.get_plugin_events", return_value=[])
    def test_general_scope_and_combined_filters(self, _plugins):
        url = "/api/v1/calendars/employees/"
        response = self.client.get(url, self.range())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual({item["id"] for item in response.data["events"]},
                         {f"leave:{self.visible_leave.pk}", f"leave:{self.other_leave.pk}"})
        self.assertEqual(response.data["employee_names"], {str(self.employee.pk): str(self.employee)})
        self.assertEqual(response.data["resources"], [{"id": str(self.employee.pk), "title": str(self.employee)}])
        filtered = self.client.get(url, self.range(type=self.leave_type.pk,
                                                  current_status=self.status.pk, team=self.team.pk,
                                                  employee=self.employee.pk, is_active="true"))
        self.assertEqual([item["id"] for item in filtered.data["events"]], [f"leave:{self.visible_leave.pk}"])
        for query in ({"type": self.other_type.pk}, {"current_status": self.other_status.pk},
                      {"team": self.other_team.pk}, {"employee": self.hidden_employee.pk},
                      {"is_active": "false"}):
            expected = 1 if "type" in query else 0
            self.assertEqual(len(self.client.get(url, self.range(**query)).data["events"]), expected)
        empty_period = self.client.get(url, {"from": "2020-01-01", "to": "2020-01-31"}).data
        self.assertEqual(empty_period["events"], [])
        self.assertEqual(empty_period["resources"], [{"id": str(self.employee.pk), "title": str(self.employee)}])
        self.assertEqual(self.client.get(url, self.range(team=self.other_team.pk)).data["resources"], [])
        self.assertEqual(self.client.get(url).status_code, 400)

    @patch("common.calendar.service.CalendarService.get_plugin_events")
    def test_general_plugins_cannot_broaden_employee_visibility(self, plugins):
        plugins.return_value = [
            LabsManagerCalendarEvent(id="visible-plugin", title="Visible", start=self.today,
                                     metadata={"employee_id": self.employee.pk}),
            LabsManagerCalendarEvent(id="hidden-plugin", title="Secret", start=self.today,
                                     metadata={"employee_id": self.hidden_employee.pk}),
        ]
        with patch("common.calendar.service.CalendarService.filter_calendar_queryset",
                   return_value=Leave.objects.all()):
            response = self.client.get("/api/v1/calendars/employees/", self.range())
        self.assertEqual({item["id"] for item in response.data["events"]},
                         {f"leave:{self.visible_leave.pk}", f"leave:{self.other_leave.pk}", "visible-plugin"})

    @patch("common.calendar.service.CalendarService.get_plugin_events")
    def test_project_scope_filters_period_and_plugin_visibility(self, plugins):
        plugins.return_value = [
            LabsManagerCalendarEvent(id="visible", title="Visible", start=self.today,
                                     metadata={"project_id": self.project.pk}),
            LabsManagerCalendarEvent(id="hidden", title="Secret", start=self.today,
                                     metadata={"project_id": self.hidden_project.pk}),
        ]
        url = "/api/v1/calendars/projects/"
        response = self.client.get(url, self.range())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([project["id"] for project in response.data["projects"]], [self.project.pk])
        self.assertEqual([item["id"] for item in response.data["items"]], [self.task.pk])
        self.assertEqual([event["id"] for event in response.data["events"]], ["visible"])
        combined = self.client.get(url, self.range(project=self.project.pk, status="true", team=self.team.pk,
                                                   institution_name=self.institution.pk, funder=self.funder.pk,
                                                   milestone_status="due_soon"))
        self.assertEqual(combined.status_code, 200, combined.data)
        self.assertEqual([item["id"] for item in combined.data["items"]], [self.task.pk])
        for query in ({"project": self.hidden_project.pk}, {"status": "false"},
                      {"team": self.other_team.pk}, {"milestone_status": "completed"},
                      {"funder": 999999}, {"institution_name": 999999}):
            result = self.client.get(url, self.range(**query)).data
            self.assertFalse(result["items"])
        self.assertEqual(self.client.get(url, {"from": "2020-01-01", "to": "2020-01-31"}).data["items"], [])
        self.assertEqual(self.client.get(url).status_code, 400)

    @patch("common.calendar.service.CalendarService.get_filters", return_value=[])
    def test_plugin_filter_contexts(self, filters):
        self.assertEqual(self.client.get("/api/v1/calendars/employees/filters/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/calendars/projects/filters/").status_code, 200)
        self.assertEqual([call.args[0].calendar_type.value for call in filters.call_args_list],
                         ["main", "project_all"])

    @patch("common.calendar.service.CalendarService.plugins", return_value=[FrenchHollidayPlugin])
    @patch.object(FrenchHollidayPlugin, "get_setting")
    @patch.object(FrenchHollidayPlugin, "load_json_file")
    def test_general_calendar_returns_zone_b_school_holiday_in_background(self, load_json, get_setting, _plugins):
        load_json.side_effect = [
            [{"zones": "Zone B", "start_date": "2026-12-18T23:00:00+00:00",
              "end_date": "2027-01-03T23:00:00+00:00", "description": "Vacances de Noël"}],
            {"2026-12-25": "Jour de Noël", "2027-01-01": "1er janvier"},
        ]
        get_setting.side_effect = lambda _instance, key: {"FHP_COLOR": "#abcdef", "FHP_TITLE": True}[key]

        response = self.client.get("/api/v1/calendars/employees/", {
            "from": "2026-12-01", "to": "2027-01-31", "frenchholliday-zone": "Zone B",
        })

        self.assertEqual(response.status_code, 200, response.data)
        events = response.data["events"]
        self.assertEqual({event["description"] for event in events},
                         {"Vacances de Noël", "Jour de Noël", "1er janvier"})
        vacation = next(event for event in events if event["kind"] == "school_holiday")
        self.assertEqual(vacation["metadata"]["zone"], "Zone B")
        self.assertEqual(vacation["display"], "background")
