from common.calendar import CalendarService
from plugin.calendar_adapter import legacy_calendar_context

class CalendarPlulginMixin():
    def filter_queryset(self, queryset):
        context = legacy_calendar_context(self.request)
        return CalendarService().filter_calendar_queryset(queryset, context)
