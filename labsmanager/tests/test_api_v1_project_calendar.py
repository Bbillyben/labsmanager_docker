from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from rest_framework.test import APITestCase

from common.calendar import CalendarContext, CalendarService, CalendarType, LabsManagerCalendarEvent
from leave.calendar import produce_leave_calendar_events
from leave.models import Leave, Leave_Type
from project.models import Participant, Project
from staff.models import Employee


class ProjectCalendarV1Tests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="project-calendar", password="test")
        self.project = Project.objects.create(name="Visible calendar")
        self.hidden = Project.objects.create(name="Hidden calendar")
        self.employee = Employee.objects.create(first_name="Ada", last_name="Reader")
        self.outsider = Employee.objects.create(first_name="Other", last_name="Person")
        Participant.objects.create(project=self.project, employee=self.employee)
        Participant.objects.create(project=self.hidden, employee=self.outsider)
        self.leave_type = Leave_Type.objects.create(short_name="CP", name="Paid leave", color="#336699")
        self.leave = Leave.objects.create(employee=self.employee, type=self.leave_type, start_date=date(2026, 9, 10), end_date=date(2026, 9, 12))
        Leave.objects.create(employee=self.outsider, type=self.leave_type, start_date=date(2026, 9, 10), end_date=date(2026, 9, 12))
        self.client.force_login(self.user)

    def url(self, suffix=""):
        return f"/api/v1/projects/{self.project.pk}/calendar/{suffix}"

    def grant(self, app, codename):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    @patch("common.calendar.service.CalendarService.get_plugin_events", return_value=[])
    def test_view_project_reads_only_participants_and_resource_metadata(self, _plugins):
        self.grant("project", "view_project")
        response = self.client.get(self.url(), {"from": "2026-09-01", "to": "2026-09-30"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        event = response.json()[0]
        self.assertEqual(event["metadata"]["employee_id"], self.employee.pk)
        self.assertEqual(event["color"], "#336699")
        self.assertEqual(event["kind"], "leave")
        self.assertFalse(self.client.get(self.url("participants/")).json()[0]["capabilities"]["can_add"])
        self.assertEqual(self.client.get(f"/api/v1/projects/999999/calendar/", {"from": "2026-09-01", "to": "2026-09-30"}).status_code, 404)

    @patch("common.calendar.service.CalendarService.get_plugin_events")
    def test_plugin_events_are_aggregated_after_core_events(self, plugin_events):
        self.grant("project", "view_project")
        plugin_events.return_value = [LabsManagerCalendarEvent(id="plugin:1", title="Holiday", start=date(2026, 9, 11), display="background", source="plugin")]
        response = self.client.get(self.url(), {"from": "2026-09-01", "to": "2026-09-30"})
        self.assertEqual([item["id"] for item in response.json()], [f"leave:{self.leave.pk}", "plugin:1"])

    def test_project_change_cannot_create_leave_and_outsider_is_rejected(self):
        self.grant("project", "change_project")
        payload = {"employee_id": self.employee.pk, "type_id": self.leave_type.pk, "start_date": "2026-10-01", "start_period": "ST", "end_date": "2026-10-01", "end_period": "EN"}
        self.assertEqual(self.client.post(self.url("leaves/"), payload, format="json").status_code, 403)
        detail = self.url(f"leaves/{self.leave.pk}/")
        self.assertEqual(self.client.patch(detail, {"comment": "Denied"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(detail).status_code, 403)
        self.grant("staff", "change_employee")
        self.assertTrue(self.client.get(self.url("participants/")).json()[0]["capabilities"]["can_add"])
        payload["employee_id"] = "invalid"
        self.assertEqual(self.client.post(self.url("leaves/"), payload, format="json").status_code, 400)
        payload["employee_id"] = self.outsider.pk
        self.assertEqual(self.client.post(self.url("leaves/"), payload, format="json").status_code, 404)
        payload["employee_id"] = self.employee.pk
        created = self.client.post(self.url("leaves/"), payload, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(Leave.objects.filter(employee=self.employee).count(), 2)
        self.assertEqual(self.client.patch(detail, {"comment": "Updated"}, format="json").status_code, 200)
        self.assertEqual(Leave.objects.get(pk=self.leave.pk).comment, "Updated")
        self.assertEqual(self.client.delete(detail).status_code, 204)
        self.assertFalse(Leave.objects.filter(pk=self.leave.pk).exists())

    def test_employee_and_project_contexts_share_the_same_leave_producer(self):
        service = CalendarService(plugins=[])
        common = {"user": self.user, "start": date(2026, 9, 1), "end": date(2026, 9, 30)}
        employee = produce_leave_calendar_events(CalendarContext(calendar_type=CalendarType.EMPLOYEE, employee_id=self.employee.pk, **common), service)
        project = produce_leave_calendar_events(CalendarContext(calendar_type=CalendarType.PROJECT, project_id=self.project.pk, **common), service)
        self.assertEqual([event.as_dict() for event in employee], [event.as_dict() for event in project])
