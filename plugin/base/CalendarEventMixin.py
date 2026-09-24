"""Plugin mixin for normalized Calendar events and filters."""

import copy
import inspect
import logging
from collections.abc import Mapping

from django.conf import settings
from django.utils.text import slugify
from settings.accessor import get_global_setting

from common.calendar import CalendarContext, CalendarType, LabsManagerCalendarFilter

logger = logging.getLogger("labsmanager")


class CalendarEventMixin:
    """Add normalized events and optional declarative filters to a plugin."""

    FILTERS = {}
    authorized_type = [
        "select",
        "checkbox",
        "radio",
        "input-text",
        "input-color",
    ]
    type_with_choices = ["select", "checkbox", "radio"]

    class MixinMeta:
        """Meta options for this mixin."""

        MIXIN_NAME = "CalendarEvent"

    def __init__(self):
        """Register mixin."""
        super().__init__()
        self.add_mixin("calendarevent", True, __class__)

    @classmethod
    def get_calendar_events(cls, context):
        """Return normalized events for a :class:`CalendarContext`."""
        return []

    @classmethod
    def filter_calendar_queryset(cls, queryset, context):
        """Optionally filter a domain queryset for the calendar context."""
        return queryset

    @classmethod
    def get_calendar_filters(cls, context):
        """Resolve declarative plugin filters for one calendar context."""
        source = getattr(cls, "SLUG", getattr(cls, "slug", cls.__name__.lower()))
        filters = []
        for key, raw_definition in cls.FILTERS.items():
            definition = copy.deepcopy(raw_definition)
            filter_type = definition.get("type")
            if filter_type not in cls.authorized_type:
                logger.warning("Unsupported calendar filter '%s' in %s", key, cls)
                continue
            for field in ("choices", "default"):
                definition[field] = cls._resolve_filter_value(
                    definition.get(field), context
                )
            if filter_type in cls.type_with_choices and not definition["choices"]:
                logger.warning("Calendar filter '%s' in %s has no choices", key, cls)
                continue
            if filter_type == "checkbox" and isinstance(
                definition["default"], str
            ):
                definition["default"] = [
                    item for item in definition["default"].split(",") if item
                ]
            elif filter_type == "checkbox" and definition["default"] is None:
                choices = definition["choices"]
                definition["default"] = list(choices) if isinstance(
                    choices, Mapping
                ) else [value for value, _label in choices]
            try:
                filters.append(
                    LabsManagerCalendarFilter.from_definition(
                        filter_id=f"{source}-{slugify(key)}",
                        source=source,
                        definition=definition,
                    )
                )
            except (KeyError, ValueError) as exc:
                logger.warning("Invalid calendar filter '%s' in %s: %s", key, cls, exc)
        return filters

    @classmethod
    def _resolve_filter_value(cls, value, context):
        if not isinstance(value, str) or not hasattr(cls, value):
            return value
        method = getattr(cls, value)
        if not callable(method):
            return value
        parameters = inspect.signature(method).parameters
        return method() if not parameters else method(context)

    @classmethod
    def get_filters(cls, request, calendar_type, *args, **kwargs):
        """Adapt normalized filters for the historical Django templates."""
        request_filters = request.GET.copy()
        request_filters.update(request.POST)
        context = CalendarContext(
            calendar_type=CalendarType.from_value(calendar_type),
            user=request.user,
            filters=request_filters,
        )
        normalized = {item.id: item for item in cls.get_calendar_filters(context)}
        source = getattr(cls, "SLUG", getattr(cls, "slug", cls.__name__.lower()))
        result = {}
        for key in cls.FILTERS:
            item = normalized.get(f"{source}-{slugify(key)}")
            if item is None:
                continue
            result[key] = {
                "title": item.title,
                "type": item.type,
                "choices": {
                    choice.value: choice.label for choice in item.choices
                },
                "default": item.default,
            }
        return result

    @classmethod
    def build_filters(cls):
        """Compatibility helper for callers without an HTTP request."""
        context = CalendarContext(CalendarType.MAIN, user=None)
        normalized = {item.id: item for item in cls.get_calendar_filters(context)}
        source = getattr(cls, "SLUG", getattr(cls, "slug", cls.__name__.lower()))
        result = {}
        for key in cls.FILTERS:
            item = normalized.get(f"{source}-{slugify(key)}")
            if item is not None:
                result[key] = {
                    "title": item.title,
                    "type": item.type,
                    "choices": {
                        choice.value: choice.label for choice in item.choices
                    },
                    "default": item.default,
                }
        return result

    def activate(self):
        """Prepare plugin calendar data when the mixin is activated."""

    def deactivate(self):
        """Remove plugin calendar data when the mixin is deactivated."""

    @classmethod
    def _activate_mixin(cls, registry, plugins, *args, **kwargs):
        """Activate CalendarEvent on active registered plugins."""
        logger.debug("Activating plugin calendarevent")
        if settings.PLUGIN_TESTING or get_global_setting("ENABLE_PLUGINS_CALENDAR"):
            for _key, plugin in plugins:
                if plugin.mixin_enabled("calendarevent") and plugin.is_active():
                    plugin.activate()

    @classmethod
    def _deactivate_mixin(cls, registry, **kwargs):
        """Deactivate CalendarEvent on registered plugins."""
        logger.debug("Deactivating plugin calendarevent")
        for _key, plugin in registry.plugins.items():
            if plugin.mixin_enabled("calendarevent"):
                plugin.deactivate()
