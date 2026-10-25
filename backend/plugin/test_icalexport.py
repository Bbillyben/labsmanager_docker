"""Focused contract tests for the bundled iCalendar plugin."""

from datetime import date, datetime, timedelta, timezone as datetime_timezone
from hashlib import sha256
from importlib.util import find_spec
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings
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
    from plugin.builtin.ICalExport.ICalExport import ICalExport, _records, _scoped_events, build_ical, ics_feed


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
        self.milestone.employee.add(self.employee)
        self.period.employee.add(self.employee)
        Milestones.objects.create(project=self.hidden_project, name="Secret", end_date=self.today)
        self.leave_type = Leave_Type.objects.create(short_name="ICS", name="Congé")
        Leave.objects.create(employee=self.employee, type=self.leave_type,
                             start_date=self.today, end_date=self.today + timedelta(days=1))
        Leave.objects.create(employee=self.other_employee, type=self.leave_type,
                             start_date=self.today, end_date=self.today)
        self.plugin = ICalExport()
        self.config = PluginConfig.objects.create(key="icalexport", name="iCalendar Export")
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

    def test_discovered_builtin_is_classified_and_active(self):
        from plugin import builtin
        discovered = get_plugins(builtin, LabManagerPlugin)
        self.assertIn("ICalExport", {plugin.NAME for plugin in discovered})
        self.assertEqual(self.plugin.slug, "icalexport")
        self.assertTrue(self.plugin.is_builtin)
        self.assertTrue(self.config.active)

    def test_planning_milestone_period_and_scoped_projects(self):
        items, events = _records("planning", 0, self.user)
        self.assertEqual({item["name"] for item in items}, {"Échéance, test", "Période"})
        parsed = Calendar.from_ical(build_ical(items, events))
        entries = {event.get("SUMMARY"): event for event in parsed.walk("VEVENT")}
        self.assertEqual(entries["Échéance, test"].decoded("DTSTART"), self.today)
        self.assertEqual(entries["Échéance, test"].decoded("DTEND"), self.today + timedelta(days=1))
        self.assertEqual(entries["Période"].decoded("DTEND"), self.today + timedelta(days=3))
        self.assertNotIn("Secret", entries)
        for kind, object_id in (("project", self.project.pk), ("employee-projects", self.employee.pk)):
            scoped, _ = _records(kind, object_id, self.user)
            self.assertEqual({row["name"] for row in scoped}, {"Échéance, test", "Période"})
        team_items, _ = _records("team-projects", self.team.pk, self.user)
        self.assertEqual({row["id"] for row in team_items}, {self.milestone.pk, self.period.pk})
        self.assertEqual({row["name"] for row in team_items},
                         {"Échéance, test", "Période"})
        self.assertEqual(next(row["ical_assignees"] for row in team_items
                              if row["id"] == self.milestone.pk), ["Ada READER"])
        with self.assertRaises(Http404):
            _records("project", self.hidden_project.pk, self.user)

    def test_employee_projects_exports_only_assigned_work_from_employee_endpoint(self):
        from staff.api_v1 import EmployeeMilestoneV1View

        other_task = Milestones.objects.create(project=self.project, name="Other task",
                                               start_date=self.today, end_date=self.today + timedelta(days=1))
        other_task.employee.add(self.other_employee)
        Milestones.objects.create(project=self.project, name="Unassigned milestone", end_date=self.today)
        second_project = Project.objects.create(name="Second", start_date=self.today,
                                                end_date=self.today + timedelta(days=10))
        Participant.objects.create(employee=self.employee, project=second_project, status="l")
        second_task = Milestones.objects.create(project=second_project, name="Second task",
                                               start_date=self.today, end_date=self.today + timedelta(days=2))
        second_task.employee.add(self.employee, self.other_employee)
        without_participation = Milestones.objects.create(project=self.hidden_project, name="Not assigned",
                                                          end_date=self.today)

        request = RequestFactory().get(f"/api/v1/employees/{self.employee.pk}/milestones/")
        request.user = self.user
        response = EmployeeMilestoneV1View.as_view()(request, pk=self.employee.pk)
        self.assertEqual(response.status_code, 200)
        expected = {row["id"] for row in response.data}
        items, events = _records("employee-projects", self.employee.pk, self.user)
        self.assertEqual({item["id"] for item in items}, expected)
        self.assertEqual({item["id"] for item in items},
                         {self.milestone.pk, self.period.pk, second_task.pk})
        self.assertNotIn(other_task.pk, expected)
        self.assertNotIn(without_participation.pk, expected)
        self.assertEqual(events, [])
        entries = {str(event.get("SUMMARY")): event for event in Calendar.from_ical(build_ical(items, events)).walk("VEVENT")}
        self.assertEqual(entries["Période"].decoded("DTEND"), self.today + timedelta(days=3))
        self.assertEqual(str(entries["Échéance, test"].get("UID")),
                         f"{sha256(f'planning:{self.milestone.pk}'.encode()).hexdigest()}@labsmanager")
        with patch("plugin.builtin.ICalExport.ICalExport._dates",
                   return_value=(self.today + timedelta(days=1), self.today + timedelta(days=2))):
            narrowed, _ = _records("employee-projects", self.employee.pk, self.user)
        self.assertEqual({item["id"] for item in narrowed}, {self.period.pk, second_task.pk})

        empty_items, _ = _records("employee-projects", self.other_employee.pk, self.other)
        self.assertEqual({item["id"] for item in empty_items}, {other_task.pk, second_task.pk})
        with self.assertRaises(Http404):
            _records("employee-projects", self.other_employee.pk, self.user)

    def test_employee_projects_uses_employee_gantt_plugin_context(self):
        from common.calendar import CalendarType

        event = LabsManagerCalendarEvent(id="assigned", title="Plugin item", start=self.today,
                                         end=self.today + timedelta(days=1), source="third-party",
                                         metadata={"detailed_title": "Employee detail"})

        class EmployeeProvider:
            @classmethod
            def get_calendar_events(cls, context):
                if (context.calendar_type == CalendarType.EMPLOYEE_GANTT
                        and context.employee_id == self.employee.pk and context.consumer == "ical"
                        and context.include_details):
                    return [event]
                return []

        with patch("common.calendar.service.CalendarService.plugins", return_value=[EmployeeProvider]):
            items, events = _records("employee-projects", self.employee.pk, self.user)
        self.assertEqual({item["id"] for item in items}, {self.milestone.pk, self.period.pk})
        self.assertEqual([row["id"] for row in events], ["assigned"])
        self.assertEqual(str(Calendar.from_ical(build_ical(items, events)).walk("VEVENT")[-1].get("SUMMARY")),
                         "Employee detail")

    def test_team_projects_exports_distinct_assignments_and_respects_visibility(self):
        from django.contrib.auth.models import Permission

        mate = Employee.objects.create(first_name="Mina", last_name="Member")
        TeamMate.objects.create(team=self.team, employee=mate)
        second_project = Project.objects.create(name="Second project", start_date=self.today,
                                                end_date=self.today + timedelta(days=10))
        Participant.objects.create(employee=self.employee, project=second_project, status="l")
        Participant.objects.create(employee=mate, project=second_project, status="l")
        mate_task = Milestones.objects.create(project=second_project, name="Mate task",
                                              start_date=self.today, end_date=self.today + timedelta(days=2))
        mate_task.employee.add(mate)
        shared = Milestones.objects.create(project=self.project, name="Shared milestone", end_date=self.today)
        shared.employee.add(self.employee, mate)
        outsider = Milestones.objects.create(project=self.project, name="Outsider task",
                                             start_date=self.today, end_date=self.today)
        outsider.employee.add(self.other_employee)
        Milestones.objects.create(project=self.project, name="Unassigned", end_date=self.today)
        hidden_assigned = Milestones.objects.create(project=self.hidden_project, name="Hidden assigned",
                                                    end_date=self.today)
        hidden_assigned.employee.add(self.employee)

        items, _ = _records("team-projects", self.team.pk, self.user)
        self.assertEqual({item["id"] for item in items},
                         {self.milestone.pk, self.period.pk, mate_task.pk, shared.pk})
        self.assertEqual(len(items), 4)
        self.assertEqual(next(item["name"] for item in items if item["id"] == shared.pk),
                         "Shared milestone")
        self.assertEqual(next(item["name"] for item in items if item["id"] == mate_task.pk),
                         "Mate task")
        self.assertNotIn(outsider.pk, {item["id"] for item in items})
        self.assertNotIn(hidden_assigned.pk, {item["id"] for item in items})

        permission = Permission.objects.get(content_type__app_label="staff", codename="view_employee")
        self.user.user_permissions.add(permission)
        self.user = get_user_model().objects.get(pk=self.user.pk)
        visible_items, _ = _records("team-projects", self.team.pk, self.user)
        self.assertEqual(next(item["ical_assignees"] for item in visible_items if item["id"] == shared.pk),
                         ["Ada READER", "Mina MEMBER"])
        self.assertEqual(next(item["ical_assignees"] for item in visible_items if item["id"] == mate_task.pk),
                         ["Mina MEMBER"])
        rendered = Calendar.from_ical(build_ical(visible_items, [], calendar="team-projects"))
        summaries = {str(event.get("SUMMARY")) for event in rendered.walk("VEVENT")}
        self.assertIn("Visible - Shared milestone (Ada READER, Mina MEMBER)", summaries)
        self.assertIn("Second project - Mate task (Mina MEMBER)", summaries)

        with patch("plugin.builtin.ICalExport.ICalExport._dates",
                   return_value=(self.today + timedelta(days=1), self.today + timedelta(days=2))):
            narrowed, _ = _records("team-projects", self.team.pk, self.user)
        self.assertEqual({item["id"] for item in narrowed}, {self.period.pk, mate_task.pk})
        with self.assertRaises(Http404):
            _records("team-projects", self.team.pk, self.other)

    def test_team_projects_uses_team_plugin_context(self):
        from common.calendar import CalendarType

        event = LabsManagerCalendarEvent(id="team-event", title="Team event", start=self.today,
                                         end=self.today + timedelta(days=1), source="third-party",
                                         metadata={"detailed_title": "Detailed team event"})

        class TeamProvider:
            @classmethod
            def filter_calendar_queryset(cls, queryset, context):
                return queryset

            @classmethod
            def get_calendar_events(cls, context):
                if (context.calendar_type == CalendarType.TEAM and context.team_id == self.team.pk
                        and context.consumer == "ical" and context.include_details):
                    return [event]
                return []

        with patch("common.calendar.service.CalendarService.plugins", return_value=[TeamProvider]):
            items, events = _records("team-projects", self.team.pk, self.user)
        self.assertEqual({item["id"] for item in items}, {self.milestone.pk, self.period.pk})
        self.assertEqual([row["id"] for row in events], ["team-event"])
        self.assertEqual(str(Calendar.from_ical(build_ical(items, events)).walk("VEVENT")[-1].get("SUMMARY")),
                         "Detailed team event")

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

    @override_settings(REACT_PUBLIC_URL="https://labs.example.org/app")
    def test_seven_feed_names_follow_current_model_names(self):
        expected = {
            "planning": "LabsManager - Planning général",
            "absences": "LabsManager - Absences générales",
            "project": "LabsManager - Projet : Visible",
            "employee-projects": "LabsManager - Projets : Ada READER",
            "employee-absences": "LabsManager - Absences : Ada READER",
            "team-projects": "LabsManager - Projets : Visible team",
            "team-absences": "LabsManager - Absences : Visible team",
        }
        urls = {kind: self._subscription(kind) for kind in expected}
        for kind, url in urls.items():
            with self.subTest(kind=kind):
                feed = Calendar.from_ical(self._feed(url).content)
                self.assertEqual(str(feed.get("NAME")), expected[kind])
                self.assertEqual(str(feed.get("X-WR-CALNAME")), expected[kind])
        self.project.name = "Renommé, été"
        self.project.save(update_fields=["name"])
        self.assertEqual(str(Calendar.from_ical(self._feed(urls["project"]).content).get("NAME")),
                         "LabsManager - Projet : Renommé, été")

    @override_settings(REACT_PUBLIC_URL="https://labs.example.org/app")
    def test_planning_titles_and_public_links_preserve_content_and_uids(self):
        self.milestone.desc = "Détails, été; réunion\nLigne 2"
        self.milestone.save(update_fields=["desc"])
        expected_uid = f"{sha256(f'planning:{self.milestone.pk}'.encode()).hexdigest()}@labsmanager"
        for kind in ("planning", "project", "employee-projects", "team-projects"):
            with self.subTest(kind=kind):
                feed = Calendar.from_ical(self._feed(self._subscription(kind)).content)
                entry = next(event for event in feed.walk("VEVENT") if str(event.get("UID")) == expected_uid)
                title = "Échéance, test" if kind == "project" else "Visible - Échéance, test"
                if kind == "team-projects":
                    title += " (Ada READER)"
                self.assertEqual(str(entry.get("SUMMARY")), title)
                self.assertEqual(str(entry.get("URL")),
                                 f"https://labs.example.org/app/projects/{self.project.pk}/tasks")
                self.assertEqual(str(entry.get("DESCRIPTION")),
                                 f"Détails, été; réunion\nLigne 2\n\nOuvrir dans LabsManager :\n"
                                 f"https://labs.example.org/app/projects/{self.project.pk}/tasks")
                self.assertEqual(entry.decoded("DTSTART"), self.today)

    @override_settings(REACT_PUBLIC_URL="https://labs.example.org/app")
    def test_leave_links_require_employee_visibility_and_plugins_keep_their_description(self):
        core = {"id": "leave:1", "source": "core", "kind": "leave", "title": "Congé",
                "start": self.today, "description": "À vérifier", "metadata": {"employee_id": self.employee.pk}}
        plugin = {"id": "external", "source": "other-plugin", "title": "Ordinary",
                  "start": self.today, "description": "Message, été", "metadata": {
                      "project_id": self.project.pk, "admin_url": "/admin/leave/1/",
                      "detailed_title": "Titre détaillé",
                  }}
        parsed = Calendar.from_ical(build_ical([], [core, plugin], user=self.user)).walk("VEVENT")
        self.assertEqual(str(parsed[0].get("URL")),
                         f"https://labs.example.org/app/employees/{self.employee.pk}/leaves")
        self.assertIn("À vérifier\n\nOuvrir dans LabsManager :", str(parsed[0].get("DESCRIPTION")))
        self.assertEqual(str(parsed[1].get("SUMMARY")), "Titre détaillé")
        self.assertEqual(str(parsed[1].get("DESCRIPTION")), "Message, été")
        self.assertIsNone(parsed[1].get("URL"))
        hidden = dict(core, metadata={"employee_id": self.other_employee.pk})
        entry = Calendar.from_ical(build_ical([], [hidden], user=self.user)).walk("VEVENT")[0]
        self.assertIsNone(entry.get("URL"))
        self.assertEqual(str(entry.get("DESCRIPTION")), "À vérifier")

    @override_settings(REACT_PUBLIC_URL="")
    def test_missing_public_url_does_not_use_request_host_or_invent_a_link(self):
        feed = Calendar.from_ical(self._feed(self._subscription("project")).content)
        entry = next(event for event in feed.walk("VEVENT") if str(event.get("SUMMARY")) == "Échéance, test")
        self.assertIsNone(entry.get("URL"))
        self.assertIsNone(entry.get("DESCRIPTION"))

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

    @override_settings(REACT_PUBLIC_URL="https://labs.example.org/app")
    def test_project_feeds_exclude_core_and_plugin_leaves_but_leave_feeds_keep_them(self):
        plugin_leave = LabsManagerCalendarEvent(
            id="plugin-leave", title="RTT", start=self.today,
            source="other-plugin", kind="leave",
            metadata={"project_id": self.project.pk, "team_id": self.team.pk,
                      "employee_id": self.employee.pk},
        )
        other_event = LabsManagerCalendarEvent(
            id="plugin-event", title="Réunion, été", start=self.today,
            source="other-plugin", kind="event", description="Détails",
            metadata={"project_id": self.project.pk, "team_id": self.team.pk,
                      "employee_id": self.employee.pk, "detailed_title": "Événement détaillé"},
        )
        core_leave = Leave.objects.get(employee=self.employee)
        uid = lambda value: f"{sha256(value.encode()).hexdigest()}@labsmanager"
        core_uid = uid(f"event:core:leave:{core_leave.pk}")
        plugin_leave_uid = uid("event:other-plugin:plugin-leave")
        other_uid = uid("event:other-plugin:plugin-event")
        milestone_uid = uid(f"planning:{self.milestone.pk}")

        with patch("common.calendar.service.CalendarService.get_plugin_events",
                   return_value=[plugin_leave, other_event]):
            for kind in ("project", "employee-projects", "team-projects"):
                with self.subTest(kind=kind):
                    items, events = _records(kind, {
                        "project": self.project.pk, "employee-projects": self.employee.pk,
                        "team-projects": self.team.pk,
                    }[kind], self.user)
                    self.assertIn(self.milestone.pk, {item["id"] for item in items})
                    self.assertEqual({event["kind"] for event in events}, {"event"})
                    parsed = Calendar.from_ical(self._feed(self._subscription(kind)).content)
                    entries = {str(event.get("UID")): event for event in parsed.walk("VEVENT")}
                    self.assertNotIn(core_uid, entries)
                    self.assertNotIn(plugin_leave_uid, entries)
                    self.assertIn(milestone_uid, entries)
                    self.assertIn(other_uid, entries)
                    self.assertEqual(str(entries[other_uid].get("SUMMARY")), "Événement détaillé")
                    self.assertEqual(str(entries[other_uid].get("DESCRIPTION")), "Détails")
                    self.assertEqual(entries[milestone_uid].decoded("DTSTART"), self.today)
                    self.assertIn("/tasks", str(entries[milestone_uid].get("URL")))

            for kind in ("absences", "employee-absences", "team-absences"):
                with self.subTest(kind=kind):
                    parsed = Calendar.from_ical(self._feed(self._subscription(kind)).content)
                    entries = {str(event.get("UID")): event for event in parsed.walk("VEVENT")}
                    self.assertIn(core_uid, entries)
                    self.assertIn(plugin_leave_uid, entries)

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
        self.assertIn("tâches et jalons", next(row["label"] for row in french
                                               if row["id"] == "employee_projects"))
        self.assertIn("tasks and milestones", next(row["label"] for row in english
                                                    if row["id"] == "employee_projects"))
        self.assertIn("tâches et jalons", next(row["label"] for row in french
                                               if row["id"] == "team_projects"))
        self.assertIn("tasks and milestones", next(row["label"] for row in english
                                                    if row["id"] == "team_projects"))
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
