from datetime import date

from django.test import SimpleTestCase

from common.calendar import (
    CalendarContext,
    CalendarService,
    CalendarType,
    LabsManagerCalendarEvent,
    LabsManagerCalendarFilter,
)
from plugin.base.CalendarEventMixin import CalendarEventMixin


class CalendarServiceTests(SimpleTestCase):
    def test_filters_and_collects_normalized_events(self):
        event = LabsManagerCalendarEvent(
            id="plugin:1", title="Plugin", start=date(2026, 9, 1), source="sample"
        )

        class Plugin:
            slug = "sample"

            @classmethod
            def filter_calendar_queryset(cls, queryset, context):
                return queryset + [context.employee_id]

            @classmethod
            def get_calendar_events(cls, context):
                return [event]

        context = CalendarContext(
            CalendarType.EMPLOYEE, user=object(), employee_id=42
        )
        service = CalendarService(plugins=[Plugin])

        self.assertEqual(service.filter_calendar_queryset([1], context), [1, 42])
        self.assertEqual(service.get_events(context), [event])
        self.assertEqual(event.as_dict()["source"], "sample")

    def test_collects_filters_and_ignores_plugins_without_filters(self):
        calendar_filter = LabsManagerCalendarFilter(
            id="sample-kind",
            title="Kind",
            type="input-text",
            source="sample",
        )

        class FilterPlugin:
            @classmethod
            def get_calendar_filters(cls, context):
                return [calendar_filter]

        class EmptyPlugin:
            @classmethod
            def get_calendar_filters(cls, context):
                return []

        context = CalendarContext(CalendarType.EMPLOYEE, user=object())
        self.assertEqual(
            CalendarService(plugins=[FilterPlugin, EmptyPlugin]).get_filters(context),
            [calendar_filter],
        )

    def test_mixin_normalizes_static_and_dynamic_filter_definitions(self):
        class Plugin(CalendarEventMixin):
            SLUG = "sample"
            FILTERS = {
                "STATIC": {
                    "title": "Static",
                    "type": "radio",
                    "choices": {"one": "One"},
                    "default": "one",
                },
                "DYNAMIC": {
                    "title": "Dynamic",
                    "type": "checkbox",
                    "choices": "dynamic_choices",
                    "default": "dynamic_default",
                },
            }

            @classmethod
            def dynamic_choices(cls, context):
                return {context.calendar_type.value: "Current context"}

            @classmethod
            def dynamic_default(cls):
                return "employee"

        filters = Plugin.get_calendar_filters(
            CalendarContext(CalendarType.EMPLOYEE, user=object())
        )

        self.assertEqual([item.id for item in filters], ["sample-static", "sample-dynamic"])
        self.assertEqual(filters[0].as_dict()["choices"], [{"value": "one", "label": "One"}])
        self.assertEqual(filters[1].default, ["employee"])
        self.assertEqual(filters[1].choices[0].value, "employee")

    def test_plugin_failure_is_logged_and_does_not_hide_other_events(self):
        class Broken:
            slug = "broken"

            @classmethod
            def get_calendar_events(cls, context):
                raise RuntimeError("broken plugin")

        event = LabsManagerCalendarEvent(
            id="core:1", title="Core", start=date(2026, 9, 1)
        )
        with self.assertLogs("labsmanager", level="ERROR"):
            events = CalendarService(plugins=[Broken]).get_events(
                CalendarContext(CalendarType.MAIN, user=object()), [event]
            )
        self.assertEqual(events, [event])
