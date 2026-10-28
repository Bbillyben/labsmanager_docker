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
    id: str
    name: str
    description: str = ""
    timezone: str | None = None
    color: str | None = None
    incarnation: str | None = None
    options: tuple[str, ...] = ()


def _valid(calendar):
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
    """The existing registry is the only source of active providers."""
    return registry.with_mixin("publishedcalendar", active=True)


def list_calendars(user):
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
    consumers = []
    for plugin in registry.with_mixin("calendarsubscription", active=True):
        try:
            if plugin.subscription_format == format_name and plugin.subscription_available():
                consumers.append(plugin)
        except Exception:
            logger.exception("Calendar subscription capability failed for %s", plugin.slug)
    return consumers[0] if len(consumers) == 1 else None
