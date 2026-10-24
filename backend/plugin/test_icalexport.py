"""Focused contract tests for the bundled iCalendar sample."""

from datetime import date, datetime, timedelta, timezone as datetime_timezone
from hashlib import sha256
from importlib.util import find_spec
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.utils import timezone
from django.utils.translation import override

from common.calendar import LabsManagerCalendarEvent
from endpoints.models import Milestones
from leave.models import Leave, Leave_Type
from plugin.helpers import get_plugins
from plugin.models import PluginAccessToken, PluginConfig
from plugin.plugin import LabManagerPlugin
from plugin.registry import registry
from project.models import Participant, Project
from staff.models import Employee, Team, TeamMate

ICALENDAR_AVAILABLE = find_spec("icalendar") is not None
if ICALENDAR_AVAILABLE:
    from icalendar import Calendar
    from plugin.samples.ICalExport.ICalExport import ICalExport, _records, _scoped_events, build_ical, ics_feed


@skipUnless(ICALENDAR_AVAILABLE, "Install the sample's requirements.txt to run iCalendar tests")
class ICalExportTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.user = get_user_model().objects.create_user("ics-user")
        self.other = get_user_model().objects.create_user("ics-other")
        self.employee = Employee.objects.create(first_name="Ada", last_name="Reader", user=self.user)
        self.other_employee = Employee.objects.create(first_name="Other", last_name="Reader", user=self.other)
        self.project = Project.objects.create(name="Visible", start_date=self.today - timedelta(days=10),
                                              end_date=self.today + timedelta(days=30))
        self.hidden_project = Project.objects.create(name="Hidden")
        Participant.objects.create(employee=self.employee, project=self.project, status="l")
        Participant.objects.create(employee=self.other_employee, project=self.hidden_project, status="l")
        self.team = Team.objects.create(name="Visible team", leader=self.employee)
        TeamMate.objects.create(team=self.team, employee=self.employee)
        self.milestone = Milestones.objects.create(project=self.project, name="Échéance, test", end_date=self.today)
        self.period = Milestones.objects.create(project=self.project, name="Période", start_date=self.today,
                                                 end_date=self.today + timedelta(days=2))
        Milestones.objects.create(project=self.hidden_project, name="Secret", end_date=self.today)
        self.leave_type = Leave_Type.objects.create(short_name="ICS", name="Congé")
        Leave.objects.create(employee=self.employee, type=self.leave_type,
                             start_date=self.today, end_date=self.today + timedelta(days=1))
        Leave.objects.create(employee=self.other_employee, type=self.leave_type,
                             start_date=self.today, end_date=self.today)
        self.plugin = ICalExport()
        self.config = PluginConfig.objects.create(key="icalexport", name="iCalendar Export")
        self.discovered_inactive = not self.config.active
        PluginConfig.objects.filter(pk=self.config.pk).update(active=True)
        self.config.active = True
        self.patches = [
            patch.object(registry, "get_plugin", side_effect=lambda slug, active=None:
                         self.plugin if slug == "icalexport" and self.config.active else None),
            patch.object(registry, "get_plugin_config", return_value=self.config),
        ]
        for scoped_patch in self.patches:
            scoped_patch.start()
            self.addCleanup(scoped_patch.stop)

    def _subscription(self, calendar, object_id=0):
        request = RequestFactory().post("/api/v1/ui-contributions/")
        request.user = self.user
        context = {"slot": "user.plugin.settings.actions", "contribution": {"local_id": calendar}}
        if calendar not in ("planning", "absences"):
            entity = calendar.split("-")[0]
            context["slot"] = f"{entity}.detail.actions"
            context[entity] = {"project": self.project, "employee": self.employee, "team": self.team}[entity]
        return self.plugin.create_subscription(request, context)["url"]

    def _feed(self, url):
        parts = urlsplit(url)
        calendar, object_id = parts.path.rstrip("/").split("/")[-2:]
        request = RequestFactory().get(parts.path + "?" + parts.query)
        return ics_feed(request, calendar, int(object_id))

    def test_discovered_sample_is_not_automatically_active(self):
        from plugin import samples
        discovered = get_plugins(samples, LabManagerPlugin)
        self.assertIn("ICalExport", {plugin.NAME for plugin in discovered})
        self.assertEqual(self.plugin.slug, "icalexport")
        self.assertTrue(self.discovered_inactive)

    def test_planning_milestone_period_and_scoped_projects(self):
        items, events = _records("planning", 0, self.user)
        self.assertEqual({item["name"] for item in items}, {"Échéance, test", "Période"})
        parsed = Calendar.from_ical(build_ical(items, events))
        entries = {event.get("SUMMARY"): event for event in parsed.walk("VEVENT")}
        self.assertEqual(entries["Échéance, test"].decoded("DTSTART"), self.today)
        self.assertEqual(entries["Échéance, test"].decoded("DTEND"), self.today + timedelta(days=1))
        self.assertEqual(entries["Période"].decoded("DTEND"), self.today + timedelta(days=3))
        self.assertNotIn("Secret", entries)
        for kind, object_id in (("project", self.project.pk), ("employee-projects", self.employee.pk),
                                ("team-projects", self.team.pk)):
            scoped, _ = _records(kind, object_id, self.user)
            self.assertEqual({row["name"] for row in scoped}, {"Échéance, test", "Période"})
        with self.assertRaises(Http404):
            _records("project", self.hidden_project.pk, self.user)

    def test_plugin_events_and_ical_format(self):
        event = LabsManagerCalendarEvent(id="accent", title="Réunion, équipe; planning", start=self.today,
                                         end=self.today + timedelta(days=1), source="third-party",
                                         description="Ligne 1\nLigne 2", metadata={"project_id": self.project.pk,
                                                                                      "detailed_title": "Réunion détaillée"})
        with patch("common.calendar.service.CalendarService.get_plugin_events", return_value=[event]) as plugin_events:
            items, events = _records("planning", 0, self.user)
            self.assertTrue(plugin_events.call_args.args[0].include_details)
            self.assertEqual(plugin_events.call_args.args[0].consumer, "ical")
            self.assertEqual([row["id"] for row in events], ["accent"])
            parsed = Calendar.from_ical(build_ical(items, events + events))
            entries = parsed.walk("VEVENT")
            self.assertEqual(len(entries), 3)
            self.assertEqual(len({str(entry.get("UID")) for entry in entries}), 3)
            self.assertIn("Ligne 2", str(entries[-1].get("DESCRIPTION")))
            self.assertEqual(str(entries[-1].get("SUMMARY")), "Réunion détaillée")
        raw = build_ical([], [{"id": "tz", "source": "third-party", "title": "É" * 90,
                                  "start": datetime(2026, 10, 24, 14, tzinfo=datetime_timezone.utc),
                                  "end": datetime(2026, 10, 24, 15, tzinfo=datetime_timezone.utc),
                                  "all_day": False}])
        self.assertIn(b"\r\n", raw)
        self.assertIn(b"\r\n ", raw)
        parsed = Calendar.from_ical(raw).walk("VEVENT")[0]
        self.assertEqual(parsed.decoded("DTSTART"), datetime(2026, 10, 24, 14, tzinfo=datetime_timezone.utc))
        self.assertEqual(str(parsed.get("SUMMARY")), "É" * 90)

    def test_app_only_provider_is_absent_from_ics_but_present_in_app(self):
        from common.global_calendar_api_v1 import GlobalProjectPlanning

        class AppOnlyProvider:
            @classmethod
            def get_calendar_events(cls, context):
                if context.consumer != "labsmanager":
                    return []
                return [LabsManagerCalendarEvent(
                    id="app-only", title="App only", start=self.today,
                    metadata={"project_id": self.project.pk},
                )]

        with patch("common.calendar.service.CalendarService.plugins", return_value=[AppOnlyProvider]):
            _, exported_events = _records("planning", 0, self.user)
            request = RequestFactory().get("/api/v1/calendars/projects/", {
                "from": str(self.today), "to": str(self.today),
            })
            request.user = self.user
            app_response = GlobalProjectPlanning.as_view()(request)

        self.assertEqual(exported_events, [])
        self.assertEqual(app_response.status_code, 200)
        self.assertIn("app-only", {event["id"] for event in app_response.data["events"]})

    def test_empty_detailed_title_falls_back_to_ordinary_title(self):
        events = [{"id": "empty", "title": "Ordinary", "start": self.today,
                   "metadata": {"detailed_title": ""}},
                  {"id": "missing", "title": "Fallback", "start": self.today}]
        parsed = Calendar.from_ical(build_ical([], events)).walk("VEVENT")
        self.assertEqual([str(event.get("SUMMARY")) for event in parsed], ["Ordinary", "Fallback"])

    def test_absence_scopes_and_permission_recheck(self):
        for kind, object_id in (("absences", 0), ("employee-absences", self.employee.pk),
                                ("team-absences", self.team.pk)):
            _, events = _records(kind, object_id, self.user)
            self.assertEqual(len([row for row in events if row["kind"] == "leave"]), 1)
            parsed = Calendar.from_ical(build_ical([], events)).walk("VEVENT")
            self.assertEqual(len([event for event in parsed if event.get("SUMMARY") == "Ada READER - Congé"]), 1)
            self.assertEqual(events[0]["title"], "Congé")
            self.assertEqual(events[0]["metadata"]["detailed_title"], "Ada READER - Congé")
            uid = f"event:core:{events[0]['id']}"
            self.assertEqual(str(parsed[0].get("UID")), f"{sha256(uid.encode()).hexdigest()}@labsmanager")
            self.assertEqual(parsed[0].decoded("DTSTART"), self.today)
            self.assertEqual(parsed[0].decoded("DTEND"), self.today + timedelta(days=2))
        with self.assertRaises(Http404):
            _records("employee-absences", self.other_employee.pk, self.user)

    def test_declared_foreign_event_scope_is_excluded(self):
        events = [
            {"id": "right", "metadata": {"project_id": self.project.pk, "employee_id": self.employee.pk}},
            {"id": "wrong-project", "metadata": {"project_id": self.hidden_project.pk}},
            {"id": "wrong-employee", "metadata": {"employee_id": self.other_employee.pk}},
        ]
        self.assertEqual([row["id"] for row in _scoped_events(
            events, project_id=self.project.pk, employee_ids={self.employee.pk}
        )], ["right"])

    def test_subscription_is_bound_revocable_and_rechecks_owner(self):
        url = self._subscription("project", self.project.pk)
        self.assertEqual(self._feed(url).status_code, 200)
        parsed = urlsplit(url)
        params = parse_qs(parsed.query)
        self.assertEqual(PluginAccessToken.objects.count(), 1)
        self.assertNotIn(params["token"][0], PluginAccessToken.objects.get().secret_hash)
        wrong_scope = parsed._replace(path=parsed.path.replace("/project/", "/employee-projects/")).geturl()
        with self.assertRaises(Http404):
            self._feed(wrong_scope)
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        with self.assertRaises(Http404):
            self._feed(url)
        self.user.is_active = True
        self.user.save(update_fields=["is_active"])
        token = PluginAccessToken.objects.get()
        token.revoked_at = timezone.now()
        token.save(update_fields=["revoked_at"])
        with self.assertRaises(Http404):
            self._feed(url)
        self.config.active = False
        with self.assertRaises(Http404):
            self._feed(url)

    def test_actions_cover_all_contexts_in_two_languages(self):
        with override("fr"):
            french = self.plugin.UI_CONTRIBUTIONS
        with override("en"):
            english = self.plugin.UI_CONTRIBUTIONS
        self.assertEqual(len(french), 8)
        self.assertEqual({row["slot"] for row in french}, {
            "user.plugin.settings.actions", "calendar.toolbar.actions", "project.detail.actions",
            "employee.detail.actions", "team.detail.actions",
        })
        self.assertNotEqual(french[0]["label"], english[0]["label"])
        request = RequestFactory().post("/")
        request.user = self.user
        for calendar_type, object_id, expected in (("project_all", 0, "/planning/0/"),
                                                    ("main", 0, "/absences/0/"),
                                                    ("project", self.project.pk, f"/project/{self.project.pk}/"),
                                                    ("employee", self.employee.pk, f"/employee-absences/{self.employee.pk}/"),
                                                    ("team", self.team.pk, f"/team-absences/{self.team.pk}/")):
            context = {"slot": "calendar.toolbar.actions", "contribution": {"local_id": "current"},
                       "calendar_type": SimpleNamespace(value=calendar_type), "calendar_id": object_id}
            self.assertIn(expected, self.plugin.create_subscription(request, context)["url"])
