import json
from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from common.calendar import CalendarContext, CalendarType, LabsManagerCalendarEvent
from plugin.samples.FrenchHollidayPlugin.FrenchHollidayPlugin import FrenchHollidayPlugin

class FrenchHolidayCalendarTests(SimpleTestCase):
    @patch.object(FrenchHollidayPlugin, "get_setting")
    @patch.object(FrenchHollidayPlugin, "load_json_file")
    def test_returns_typed_bounded_events(self, load_json, get_setting):
        load_json.side_effect = [
            [{"zones": "Zone B", "start_date": "2026-10-17T00:00:00+00:00", "end_date": "2026-11-02T00:00:00+00:00", "description": "Vacances d'Été"}],
            {"2026-11-01": "Fête d'Automne"},
        ]
        get_setting.side_effect = lambda _instance, key: {"FHP_VACATION_ZONE": "Zone B", "FHP_COLOR": "#abcdef", "FHP_TITLE": True}[key]
        context = CalendarContext(CalendarType.EMPLOYEE, user=object(), start=date(2026, 10, 1), end=date(2026, 11, 30), filters={})

        events = FrenchHollidayPlugin.get_calendar_events(context)

        self.assertEqual(len(events), 2)
        self.assertTrue(all(isinstance(event, LabsManagerCalendarEvent) for event in events))
        self.assertEqual(events[0].metadata["zone"], "Zone B")
        self.assertEqual(events[0].description, "Vacances d'Été")
        self.assertEqual(events[1].description, "Fête d'Automne")
        self.assertNotIn("&#x27;", events[0].description)

    def test_excludes_project_calendars(self):
        context = CalendarContext(CalendarType.PROJECT, user=object())
        self.assertEqual(FrenchHollidayPlugin.get_calendar_events(context), [])

    @patch.object(FrenchHollidayPlugin, "get_vacation_events", return_value=[])
    def test_employee_gantt_is_an_applicable_event_context(self, get_events):
        context = CalendarContext(CalendarType.EMPLOYEE_GANTT, user=object())
        self.assertEqual(FrenchHollidayPlugin.get_calendar_events(context), [])
        get_events.assert_called_once_with(context)

    @patch.object(FrenchHollidayPlugin, "get_default_zone", return_value="Zone B")
    @patch.object(
        FrenchHollidayPlugin,
        "get_vacation_zones_object",
        return_value={"Zone A": "Zone A", "Zone B": "Zone B"},
    )
    def test_exposes_dynamic_zone_filter_for_supported_calendars(
        self, _choices, _default
    ):
        filters = FrenchHollidayPlugin.get_calendar_filters(
            CalendarContext(CalendarType.EMPLOYEE, user=object())
        )

        self.assertEqual(len(filters), 1)
        self.assertEqual(filters[0].id, "frenchholliday-zone")
        self.assertEqual(filters[0].default, "Zone B")
        self.assertEqual(
            [choice.value for choice in filters[0].choices], ["Zone A", "Zone B"]
        )
        self.assertEqual(
            FrenchHollidayPlugin.get_calendar_filters(
                CalendarContext(CalendarType.PROJECT, user=object())
            ),
            [],
        )
        gantt_filters = FrenchHollidayPlugin.get_calendar_filters(
            CalendarContext(CalendarType.EMPLOYEE_GANTT, user=object())
        )
        self.assertEqual([item.id for item in gantt_filters], ["frenchholliday-zone"])

    @patch.object(FrenchHollidayPlugin, "get_setting")
    @patch.object(FrenchHollidayPlugin, "load_json_file")
    def test_selected_zone_from_context_filters_controls_events(
        self, load_json, get_setting
    ):
        load_json.side_effect = [
            [
                {"zones": "Zone A", "start_date": "2026-10-01T00:00:00+00:00", "end_date": "2026-10-02T00:00:00+00:00", "description": "A"},
                {"zones": "Zone B", "start_date": "2026-10-03T00:00:00+00:00", "end_date": "2026-10-04T00:00:00+00:00", "description": "B"},
            ],
            {},
        ]
        get_setting.side_effect = lambda _instance, key: {
            "FHP_COLOR": "#abcdef",
            "FHP_TITLE": True,
        }[key]
        context = CalendarContext(
            CalendarType.EMPLOYEE,
            user=object(),
            start=date(2026, 10, 1),
            end=date(2026, 10, 31),
            filters={"frenchholliday-zone": "Zone A"},
        )

        events = FrenchHollidayPlugin.get_calendar_events(context)

        self.assertEqual([event.description for event in events], ["A"])


class LegacyCalendarFacadeTests(TestCase):
    @patch("common.calendar.service.CalendarService.get_events")
    def test_serializes_service_events_as_fullcalendar_json(self, get_events):
        get_events.return_value = [LabsManagerCalendarEvent(id="plugin:1", title="Holiday", start=date(2026, 11, 1), source="sample", kind="holiday", description="Day off")]
        response = self.client.post(
            reverse("api-plugin-calendarevent"),
            {"settings": json.dumps({"cal_type": "employee"}), "start": "2026-11-01T00:00:00Z", "end": "2026-12-01T00:00:00Z"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["start"], "2026-11-01")
        self.assertEqual(response.json()[0]["extendedProps"]["source"], "sample")
