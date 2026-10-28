"""Opt-in contract for independently owned calendars published by a plugin."""


class PublishedCalendarMixin:
    class MixinMeta:
        MIXIN_NAME = "Published calendars"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_mixin("publishedcalendar", True, __class__)

    def list_published_calendars(self, user):
        """Return calendars visible to user, without fetching their events."""
        return ()

    def get_published_calendar(self, user, calendar_id):
        """Return one visible calendar or raise Http404."""
        raise NotImplementedError

    def get_published_events(self, user, calendar_id, start, end, *, options=None):
        """Return events overlapping [start, end); apply only declared options."""
        raise NotImplementedError
