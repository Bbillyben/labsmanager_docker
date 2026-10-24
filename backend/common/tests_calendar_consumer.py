"""Request-to-context propagation for calendar event consumers."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from rest_framework.request import Request

from common.calendar import CalendarContext, CalendarService, CalendarType, LabsManagerCalendarEvent
from common.global_calendar_api_v1 import GlobalEmployeeCalendar, GlobalProjectPlanning
from plugin.calendar_adapter import legacy_calendar_context
from project.calendar_api_v1 import ProjectCalendarV1View
from staff.api_v1 import EmployeeCalendarFilterV1View, EmployeeCalendarV1View
from staff.team_api_v1 import TeamCalendarV1View


class CalendarConsumerContextTests(SimpleTestCase):
    def request(self, **params):
        request = RequestFactory().get("/calendar/", {
            "from": "2026-10-01", "to": "2026-10-31", **params,
        })
        request.user = SimpleNamespace(is_authenticated=True)
        return Request(request)

    def test_default_and_explicit_consumer_reach_all_calendar_views(self):
        for params, expected_consumer, expected_details in (
            ({}, "labsmanager", False),
            ({"consumer": "ical", "include_details": "1"}, "ical", True),
        ):
            with self.subTest(params=params):
                request = self.request(**params)
                for view_class in (GlobalEmployeeCalendar, GlobalProjectPlanning):
                    context = view_class().context(request, bounded=True)
                    self.assertEqual(context.consumer, expected_consumer)
                    self.assertEqual(context.include_details, expected_details)

                project = ProjectCalendarV1View()
                project.request = request
                with patch.object(project, "project", return_value=SimpleNamespace(pk=3)):
                    context = project.context(bounded=True)
                self.assertEqual((context.consumer, context.include_details),
                                 (expected_consumer, expected_details))

                team = TeamCalendarV1View()
                team.request = request
                with patch.object(team, "team", return_value=SimpleNamespace(pk=5)):
                    context = team.context(bounded=True)
                self.assertEqual((context.consumer, context.include_details),
                                 (expected_consumer, expected_details))

                employee = EmployeeCalendarV1View()
                employee.request = request
                employee.kwargs = {"pk": 7}
                with patch.object(employee, "get_employee", return_value=SimpleNamespace(pk=7)), \
                     patch("staff.api_v1.produce_leave_calendar_events", return_value=[]), \
                     patch("staff.api_v1.CalendarService.get_events", return_value=[]) as get_events:
                    employee.get(request)
                context = get_events.call_args.args[0]
                self.assertEqual((context.consumer, context.include_details),
                                 (expected_consumer, expected_details))

                employee_filters = EmployeeCalendarFilterV1View()
                employee_filters.request = request
                employee_filters.kwargs = {"pk": 7}
                with patch.object(employee_filters, "get_employee", return_value=SimpleNamespace(pk=7)), \
                     patch("staff.api_v1.CalendarService.get_filters", return_value=[]) as get_filters:
                    employee_filters.get(request)
                context = get_filters.call_args.args[0]
                self.assertEqual((context.consumer, context.include_details),
                                 (expected_consumer, expected_details))

    def test_legacy_http_adapter_preserves_consumer_and_details(self):
        request = RequestFactory().get("/calendar_plugin/", {
            "consumer": "ical", "include_details": "1",
        })
        request.user = object()
        context = legacy_calendar_context(request)
        self.assertEqual(context.consumer, "ical")
        self.assertTrue(context.include_details)

    def test_provider_can_opt_out_of_ics_without_affecting_react(self):
        event = LabsManagerCalendarEvent(id="sample:1", title="Visible in app", start=date(2026, 10, 1))

        class AppOnlyProvider:
            @classmethod
            def get_calendar_events(cls, context):
                if context.consumer != "labsmanager":
                    return []
                return [event]

        service = CalendarService(plugins=[AppOnlyProvider])
        self.assertEqual(service.get_plugin_events(CalendarContext(CalendarType.MAIN, user=object())), [event])
        self.assertEqual(service.get_plugin_events(CalendarContext(CalendarType.MAIN, user=object(), consumer="ical")), [])
