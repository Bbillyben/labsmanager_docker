"""Opt-in contract for independently owned calendars published by a plugin."""


class PublishedCalendarMixin:
    """Publish user-visible calendars through the shared provider registry.

    Implement the two lookup methods and the event iterator in a plugin class.
    Return ``PublishedCalendar`` instances from the listing method; the core
    validates their identifiers and option names before exposing them. The
    provider remains responsible for object-level visibility in each method.
    """

    class MixinMeta:
        MIXIN_NAME = "Published calendars"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_mixin("publishedcalendar", True, __class__)

    def list_published_calendars(self, user):
        """List calendar metadata visible to ``user`` without loading events.

        Returns:
            An iterable of ``PublishedCalendar`` objects. The default is empty.
        """
        return ()

    def get_published_calendar(self, user, calendar_id):
        """Return one visible calendar by local ID, or raise ``Http404``.

        The caller uses this lookup for both authenticated discovery and
        subscription requests, so implementations must check visibility here.
        """
        raise NotImplementedError

    def get_published_events(self, user, calendar_id, start, end, *, options=None):
        """Return events overlapping the aware interval ``[start, end)``.

        Args:
            user: Calendar owner whose permissions govern the query.
            calendar_id: Provider-local calendar identifier.
            start: Inclusive timezone-aware lower bound.
            end: Exclusive timezone-aware upper bound.
            options: Validated boolean filters declared by the calendar.

        Returns:
            An iterable of ``LabsManagerCalendarEvent`` objects.
        """
        raise NotImplementedError
