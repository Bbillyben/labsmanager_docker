"""Single orchestration point for CalendarEvent plugins."""

import logging

from .events import LabsManagerCalendarEvent
from .filters import LabsManagerCalendarFilter

logger = logging.getLogger("labsmanager")


class CalendarService:
    """Apply plugin filters and aggregate normalized plugin events."""

    def __init__(self, plugins=None):
        self._plugins = plugins

    def plugins(self):
        if self._plugins is not None:
            return self._plugins
        from plugin import registry

        return registry.with_mixin("calendarevent", active=True)

    def filter_calendar_queryset(self, queryset, context):
        """Apply every active plugin filter without hiding plugin failures."""
        for plugin in self.plugins():
            try:
                queryset = plugin.filter_calendar_queryset(queryset, context)
            except Exception:
                logger.exception(
                    "Calendar plugin %s failed while filtering events",
                    getattr(plugin, "slug", getattr(plugin, "name", plugin.__class__.__name__)),
                )
        return queryset

    def get_plugin_events(self, context):
        """Collect validated events from all active calendar plugins."""
        events = []
        for plugin in self.plugins():
            try:
                plugin_events = plugin.get_calendar_events(context) or []
                invalid = [event for event in plugin_events if not isinstance(event, LabsManagerCalendarEvent)]
                if invalid:
                    raise TypeError("get_calendar_events() must return LabsManagerCalendarEvent instances")
                events.extend(plugin_events)
            except Exception:
                logger.exception(
                    "Calendar plugin %s failed while producing events",
                    getattr(plugin, "slug", getattr(plugin, "name", plugin.__class__.__name__)),
                )
        return events

    def get_filters(self, context):
        """Collect validated filters from all active calendar plugins."""
        filters = []
        for plugin in self.plugins():
            try:
                plugin_filters = plugin.get_calendar_filters(context) or []
                if any(
                    not isinstance(item, LabsManagerCalendarFilter)
                    for item in plugin_filters
                ):
                    raise TypeError(
                        "get_calendar_filters() must return "
                        "LabsManagerCalendarFilter instances"
                    )
                filters.extend(plugin_filters)
            except Exception:
                logger.exception(
                    "Calendar plugin %s failed while producing filters",
                    getattr(
                        plugin,
                        "slug",
                        getattr(plugin, "name", plugin.__class__.__name__),
                    ),
                )
        return filters

    def get_events(self, context, core_events=()):
        """Return domain events followed by plugin-provided events."""
        return [*core_events, *self.get_plugin_events(context)]
