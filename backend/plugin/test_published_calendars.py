"""Focused tests for the plugin-independent published calendar contract."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.http import Http404
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate

from common.calendar import LabsManagerCalendarEvent
from plugin.published_calendar_api_v1 import PublishedCalendarSubscriptions
from plugin.published_calendars import PublishedCalendar, get_calendar, get_events, list_calendars, subscription_consumer


class Provider:
    def __init__(self, slug, allowed=True):
        self.slug = slug
        self.allowed = allowed
        self.calls = []

    def list_published_calendars(self, user):
        self.calls.append("list")
        return [PublishedCalendar("1", self.slug)] if self.allowed else []

    def get_published_calendar(self, user, calendar_id):
        self.calls.append(("get", calendar_id))
        if not self.allowed:
            raise Http404
        return PublishedCalendar(calendar_id, self.slug)

    def get_published_events(self, user, calendar_id, start, end):
        self.calls.append(("events", calendar_id, start, end))
        return [LabsManagerCalendarEvent(id="event-1", title=self.slug, start=start, end=end)]


class PublishedCalendarTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(is_authenticated=True)
        self.start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.end = self.start + timedelta(days=1)

    def test_two_providers_may_use_same_local_id_without_loading_events(self):
        a, b = Provider("alpha"), Provider("beta")
        a.list_published_calendars = lambda user: [PublishedCalendar("1", "First", description="Visible"),
                                                    PublishedCalendar("2", "Second")]
        with patch("plugin.published_calendars.providers", return_value=[a, b]):
            self.assertEqual([(slug, item.id) for slug, item in list_calendars(self.user)],
                             [("alpha", "1"), ("alpha", "2"), ("beta", "1")])
            self.assertEqual(get_calendar(self.user, "beta", "1")[0], b)
            self.assertEqual([event.title for event in get_events(self.user, "alpha", "1", self.start, self.end)],
                             ["alpha"])
        self.assertEqual([call for call in b.calls if isinstance(call, tuple) and call[0] == "events"], [])

    def test_access_revocation_and_disabled_provider(self):
        provider = Provider("alpha")
        with patch("plugin.published_calendars.providers", return_value=[provider]):
            provider.allowed = False
            with self.assertRaises(Http404):
                list(get_events(self.user, "alpha", "1", self.start, self.end))
        with patch("plugin.published_calendars.providers", return_value=[]):
            with self.assertRaises(Http404):
                get_calendar(self.user, "alpha", "1")

    def test_bad_provider_does_not_hide_other_provider(self):
        invalid, valid = Provider("bad"), Provider("good")
        invalid.list_published_calendars = lambda user: [PublishedCalendar("1", "one"),
                                                          PublishedCalendar("1", "duplicate")]
        with patch("plugin.published_calendars.providers", return_value=[invalid, valid]):
            self.assertEqual([(slug, item.id) for slug, item in list_calendars(self.user)], [("good", "1")])

    def test_half_open_interval_and_event_contract(self):
        provider = Provider("alpha")
        with patch("plugin.published_calendars.providers", return_value=[provider]):
            with self.assertRaises(ValueError):
                list(get_events(self.user, "alpha", "1", self.end, self.start))
            with self.assertRaises(ValueError):
                list(get_events(self.user, "alpha", "1", self.start.replace(tzinfo=None), self.end))
            provider.get_published_events = lambda *args: [object()]
            with self.assertRaises(ValueError):
                list(get_events(self.user, "alpha", "1", self.start, self.end))

    def test_capability_and_subscription_api_are_consumer_independent(self):
        self.assertEqual(reverse("api_v1:published-calendar-subscriptions"),
                         "/api/v1/published-calendars/subscriptions/")
        provider = Provider("alpha")
        consumer = SimpleNamespace(subscription_format="ics", subscription_available=lambda: True,
                                   create_published_subscription=lambda *args: {"url": "https://example.test/ics"})
        def mixins(name, active=True):
            return [provider] if name == "publishedcalendar" else [consumer]
        with patch("plugin.published_calendars.registry.with_mixin", side_effect=mixins):
            self.assertIs(subscription_consumer("ics"), consumer)
            request = APIRequestFactory().get("/api/v1/published-calendars/subscriptions/")
            force_authenticate(request, user=self.user)
            response = PublishedCalendarSubscriptions.as_view()(request)
            self.assertEqual(response.data, {"formats": ["ics"]})
            request = APIRequestFactory().post("/api/v1/published-calendars/alpha/1/subscriptions/")
            force_authenticate(request, user=self.user)
            response = PublishedCalendarSubscriptions.as_view()(request, provider_slug="alpha", calendar_id="1")
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.data["url"], "https://example.test/ics")
            consumer.subscription_available = lambda: False
            request = APIRequestFactory().get("/api/v1/published-calendars/subscriptions/")
            force_authenticate(request, user=self.user)
            self.assertEqual(PublishedCalendarSubscriptions.as_view()(request).data, {"formats": []})
        with patch("plugin.published_calendars.registry.with_mixin", return_value=[]):
            request = APIRequestFactory().get("/api/v1/published-calendars/subscriptions/")
            force_authenticate(request, user=self.user)
            self.assertEqual(PublishedCalendarSubscriptions.as_view()(request).data, {"formats": []})
