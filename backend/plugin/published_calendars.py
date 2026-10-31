"""Registry-backed access to calendars owned by independent plugins."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime

from django.http import Http404
from django.utils import timezone

from common.calendar import LabsManagerCalendarEvent
from plugin.registry import registry

logger = logging.getLogger(__name__)
IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class PublishedCalendar:
    """Validated public metadata for one provider-local calendar.

    ``id`` is unique within its provider, not across plugins. ``options``
    lists boolean filters a consumer may pass to the provider; an empty tuple
    advertises no filters. ``incarnation`` is optional provider metadata.
    """

    id: str
    name: str
    description: str = ""
    timezone: str | None = None
    color: str | None = None
    incarnation: str | None = None
    options: tuple[str, ...] = ()


def _valid(calendar):
    """Check the wire-safe shape of provider-supplied calendar metadata."""
    return (isinstance(calendar, PublishedCalendar)
            and isinstance(calendar.id, str) and IDENTIFIER.fullmatch(calendar.id)
            and isinstance(calendar.name, str) and bool(calendar.name.strip())
            and isinstance(calendar.description, str)
            and (calendar.timezone is None or isinstance(calendar.timezone, str))
            and (calendar.color is None or isinstance(calendar.color, str))
            and (calendar.incarnation is None or isinstance(calendar.incarnation, str))
            and isinstance(calendar.options, tuple)
            and all(isinstance(option, str) and IDENTIFIER.fullmatch(option) for option in calendar.options))


def providers():
    """Return active plugins implementing the published-calendar mixin."""
    return registry.with_mixin("publishedcalendar", active=True)


def list_calendars(user):
    """Collect metadata visible to ``user`` from active providers.

    A provider with an invalid or duplicated local calendar ID contributes
    nothing; its error is logged without hiding other providers' calendars.

    Returns:
        ``(provider_slug, PublishedCalendar)`` pairs.
    """
    results = []
    for provider in providers():
        try:
            items = provider.list_published_calendars(user)
            seen = set()
            provider_results = []
            for calendar in items:
                if not _valid(calendar) or calendar.id in seen:
                    raise ValueError("Invalid or duplicate published calendar id")
                seen.add(calendar.id)
                provider_results.append((provider.slug, calendar))
            results.extend(provider_results)
        except Exception:
            logger.exception("Published calendar listing failed for %s", provider.slug)
    return results


def get_calendar(user, provider_slug, calendar_id):
    """Resolve a visible calendar through its active provider.

    Raises:
        Http404: The identifier, provider, or returned calendar is invalid.
    """
    if not isinstance(calendar_id, str) or not IDENTIFIER.fullmatch(calendar_id):
        raise Http404
    provider = next((item for item in providers() if item.slug == provider_slug), None)
    if provider is None:
        raise Http404
    calendar = provider.get_published_calendar(user, calendar_id)
    if not _valid(calendar) or calendar.id != calendar_id:
        raise Http404
    return provider, calendar


def get_events(user, provider_slug, calendar_id, start, end, *, options=None):
    """Yield validated events for a visible published calendar.

    Args:
        user: Owner whose visibility the provider must enforce.
        provider_slug: Active provider identity.
        calendar_id: Provider-local calendar identity.
        start: Inclusive timezone-aware start.
        end: Exclusive timezone-aware end.
        options: Boolean filters advertised in the calendar metadata.

    Yields:
        ``LabsManagerCalendarEvent`` instances with nonempty IDs.

    Raises:
        Http404: The calendar cannot be resolved for this user.
        ValueError: The range, options, or provider events are invalid.
    """
    if (not isinstance(start, datetime) or not isinstance(end, datetime)
            or timezone.is_naive(start) or timezone.is_naive(end) or end <= start):
        raise ValueError("An increasing aware datetime interval is required")
    provider, calendar = get_calendar(user, provider_slug, calendar_id)
    options = options or {}
    if set(options) - set(calendar.options) or any(type(value) is not bool for value in options.values()):
        raise ValueError("Unsupported published calendar option")
    events = (provider.get_published_events(user, calendar_id, start, end, options=options) if options
              else provider.get_published_events(user, calendar_id, start, end))
    for event in events:
        if not isinstance(event, LabsManagerCalendarEvent) or not event.id:
            raise ValueError("Provider returned an invalid event")
        yield event


def subscription_consumer(format_name):
    """Return the sole available active consumer of a subscription format.

    Returns ``None`` when there are zero or multiple matching consumers;
    consumer failures are logged and do not stop discovery.
    """
    consumers = []
    for plugin in registry.with_mixin("calendarsubscription", active=True):
        try:
            if plugin.subscription_format == format_name and plugin.subscription_available():
                consumers.append(plugin)
        except Exception:
            logger.exception("Calendar subscription capability failed for %s", plugin.slug)
    return consumers[0] if len(consumers) == 1 else None
