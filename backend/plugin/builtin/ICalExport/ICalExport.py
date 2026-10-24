"""Personal, read-only subscriptions to the existing calendar and Planning views."""

from datetime import date, datetime, timedelta, timezone as datetime_timezone
from hashlib import sha256
from urllib.parse import urlencode

from django.core import signing
from django.http import Http404, HttpRequest, HttpResponse, QueryDict
from django.urls import path
from django.utils import timezone
from django.utils.translation import get_language
from icalendar import Calendar, Event

from plugin import LabManagerPlugin, registry
from plugin.mixins import TokenMixin, UIContributionMixin, UrlsMixin
from plugin.tokens import TokenError


CALENDARS = frozenset({
    "planning", "absences", "project", "employee-projects", "employee-absences",
    "team-projects", "team-absences",
})
SCOPED = frozenset({"project", "employee-projects", "employee-absences", "team-projects", "team-absences"})
SIGNING_SALT = "plugin.icalexport.subscription"


def _invoke(view, user, start, end, *, include_details=False, **kwargs):
    """Read the same authorized and serialized provider used by the React page."""
    request = HttpRequest()
    request.method = "GET"
    request.path = "/"
    request.GET = QueryDict(mutable=True)
    request.GET.update({"from": start.isoformat(), "to": end.isoformat(), "consumer": "ical"})
    if include_details:
        request.GET["include_details"] = "1"
    request.user = user
    response = view.as_view()(request, **kwargs)
    if response.status_code != 200:
        raise Http404
    return response.data


def _dates():
    today = timezone.localdate()
    return date(today.year - 2, 1, 1), date(today.year + 5, 12, 31)


def _records(calendar, object_id, user):
    from common.global_calendar_api_v1 import GlobalEmployeeCalendar, GlobalProjectPlanning
    from endpoints.api_v1 import ProjectPlanningV1View
    from project.calendar_api_v1 import ProjectCalendarV1View
    from staff.api_v1 import EmployeeCalendarV1View, EmployeeProjectParticipationV1View
    from staff.team_api_v1 import TeamCalendarV1View, TeamProjectsV1View

    start, end = _dates()
    items, events = [], []
    if calendar == "planning":
        data = _invoke(GlobalProjectPlanning, user, start, end, include_details=True)
        items, events = data["items"], data["events"]
    elif calendar == "absences":
        events = _invoke(GlobalEmployeeCalendar, user, start, end, include_details=True)["events"]
    elif calendar == "project":
        items = _invoke(ProjectPlanningV1View, user, start, end, pk=object_id)["items"]
        events = _invoke(ProjectCalendarV1View, user, start, end, project_id=object_id, include_details=True)
        from project.models import Participant
        employee_ids = set(Participant.objects.filter(project_id=object_id).values_list("employee_id", flat=True))
        events = _scoped_events(events, project_id=object_id, employee_ids=employee_ids)
    elif calendar == "employee-absences":
        events = _invoke(EmployeeCalendarV1View, user, start, end, pk=object_id, include_details=True)
        events = _scoped_events(events, employee_ids={object_id})
    elif calendar == "team-absences":
        events = _invoke(TeamCalendarV1View, user, start, end, team_id=object_id, include_details=True)
        from staff.team_api_v1 import team_members
        from staff.models import Team
        employee_ids = set(team_members(Team.objects.get(pk=object_id)).values_list("pk", flat=True))
        events = _scoped_events(events, team_id=object_id, employee_ids=employee_ids)
    elif calendar == "employee-projects":
        participations = _invoke(EmployeeProjectParticipationV1View, user, start, end, pk=object_id)
        ids = {row["project"]["id"] for row in participations if row["project"]["can_view"]}
        for project_id in sorted(ids):
            items.extend(_invoke(ProjectPlanningV1View, user, start, end, pk=project_id)["items"])
            project_events = _invoke(ProjectCalendarV1View, user, start, end, project_id=project_id, include_details=True)
            events.extend(event for event in _scoped_events(project_events, project_id=project_id)
                          if event.get("kind") != "leave")
    elif calendar == "team-projects":
        projects = _invoke(TeamProjectsV1View, user, start, end, team_id=object_id)
        for project_id in sorted({row["id"] for row in projects}):
            items.extend(_invoke(ProjectPlanningV1View, user, start, end, pk=project_id)["items"])
            project_events = _invoke(ProjectCalendarV1View, user, start, end, project_id=project_id, include_details=True)
            events.extend(event for event in _scoped_events(project_events, project_id=project_id)
                          if event.get("kind") != "leave")
    else:
        raise Http404
    return items, [event for event in events if _event_in_window(event, start, end)]


def _event_in_window(event, start, end):
    event_start = _date(event.get("start"))
    event_end = _date(event.get("end")) or event_start
    if event_start is None:
        return False
    event_start = event_start.date() if isinstance(event_start, datetime) else event_start
    event_end = event_end.date() if isinstance(event_end, datetime) else event_end
    return event_start <= end and event_end >= start


def _scoped_events(events, *, project_id=None, team_id=None, employee_ids=None):
    """Do not allow an event's declared entity identifiers to escape the selected scope."""
    allowed_employees = {str(pk) for pk in employee_ids} if employee_ids is not None else None

    def matches(event):
        metadata = event.get("metadata") or {}
        for key, expected in (("project_id", project_id), ("team_id", team_id)):
            if expected is not None and metadata.get(key) is not None and str(metadata[key]) != str(expected):
                return False
        if allowed_employees is not None and metadata.get("employee_id") is not None:
            return str(metadata["employee_id"]) in allowed_employees
        return True
    return [event for event in events if matches(event)]


def _date(value):
    if isinstance(value, (date, datetime)):
        return value
    if not value:
        return None
    return datetime.fromisoformat(value) if "T" in value else date.fromisoformat(value)


def _add_event(ical, uid, title, start, end, description="", all_day=True):
    if start is None:
        return
    event = Event()
    event.add("uid", f"{sha256(uid.encode('utf-8')).hexdigest()}@labsmanager")
    event.add("summary", str(title or ""))
    event.add("dtstamp", timezone.now())
    start, end = _date(start), _date(end)
    if all_day:
        start = start.date() if isinstance(start, datetime) else start
        end = end.date() if isinstance(end, datetime) else end
        # Source calendar events already use exclusive ends. Gantt callers pass inclusive ends.
        event.add("dtstart", start)
        event.add("dtend", end if end and end > start else start + timedelta(days=1))
    else:
        local_zone = timezone.get_current_timezone()
        start = datetime.combine(start, datetime.min.time()) if isinstance(start, date) and not isinstance(start, datetime) else start
        end = datetime.combine(end, datetime.min.time()) if isinstance(end, date) and not isinstance(end, datetime) else end
        start = timezone.make_aware(start, local_zone) if timezone.is_naive(start) else start
        if end is not None and timezone.is_naive(end):
            end = timezone.make_aware(end, local_zone)
        if end is None or end <= start:
            end = start + timedelta(hours=1)
        event.add("dtstart", start.astimezone(datetime_timezone.utc))
        event.add("dtend", end.astimezone(datetime_timezone.utc))
    if description:
        event.add("description", str(description))
    ical.add_component(event)


def build_ical(items, events, name="LabsManager"):
    ical = Calendar()
    ical.add("prodid", "-//LabsManager//ICalExport//EN")
    ical.add("version", "2.0")
    ical.add("calscale", "GREGORIAN")
    ical.add("x-wr-calname", name)
    seen = set()
    for item in items:
        uid = f"planning:{item['id']}"
        if uid in seen:
            continue
        seen.add(uid)
        start = item.get("start_date") or item.get("end_date")
        end = item.get("end_date")
        if not start:
            continue
        end = _date(end) + timedelta(days=1) if end else _date(start) + timedelta(days=1)
        _add_event(ical, uid, item.get("name"), start, end, item.get("desc") or "")
    for source in events:
        uid = f"event:{source.get('source', 'core')}:{source['id']}"
        if uid in seen:
            continue
        seen.add(uid)
        start = _date(source.get("start"))
        end = _date(source.get("end"))
        # The calendar domain already expresses all-day ends as exclusive.
        summary = (source.get("metadata") or {}).get("detailed_title") or source.get("title")
        _add_event(ical, uid, summary, start, end,
                   source.get("description") or "", source.get("all_day", True))
    return ical.to_ical()


def ics_feed(request, calendar, object_id):
    if calendar not in CALENDARS or (calendar in SCOPED) != (object_id > 0):
        raise Http404
    plugin = registry.get_plugin("icalexport", active=True)
    if plugin is None:
        raise Http404
    token = request.GET.get("token", "")
    signature = request.GET.get("scope", "")
    try:
        owner = plugin.validate_token(token, kind="user", required_scopes=["ics"])
        expected = f"{owner.public_id}:{calendar}:{object_id}"
        if signing.Signer(salt=SIGNING_SALT).unsign(signature) != expected:
            raise Http404
    except (TokenError, signing.BadSignature):
        raise Http404 from None
    items, events = _records(calendar, object_id, owner.user)
    response = HttpResponse(build_ical(items, events), content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="labsmanager.ics"'
    response["Cache-Control"] = "private, no-store"
    return response


class ICalExport(UrlsMixin, TokenMixin, UIContributionMixin, LabManagerPlugin):
    NAME = "ICalExport"
    SLUG = "icalexport"
    TITLE = "iCalendar Export"
    AUTHOR = "LabsManager contributors"
    DESCRIPTION = "Read-only personal iCalendar subscriptions"
    VERSION = "1.0.0"
    URLS = [path("ics/<str:calendar>/<int:object_id>/", ics_feed, name="icalexport-feed")]
    TOKEN_CONFIG = {"plugin": False, "user": True, "scopes": {
        "ics": {"user": True, "label": "iCalendar subscription", "description": "Read-only calendar feed"},
    }}

    @property
    def UI_CONTRIBUTIONS(self):
        french = (get_language() or "").startswith("fr")
        labels = {
            "planning": ("S’abonner au Planning général", "Subscribe to general Planning"),
            "absences": ("S’abonner aux absences générales", "Subscribe to general absences"),
            "project": ("S’abonner aux échéances du projet", "Subscribe to project deadlines"),
            "employee-projects": ("S’abonner aux projets de l’employé", "Subscribe to employee projects"),
            "employee-absences": ("S’abonner aux absences de l’employé", "Subscribe to employee absences"),
            "team-projects": ("S’abonner aux projets de l’équipe", "Subscribe to team projects"),
            "team-absences": ("S’abonner aux absences de l’équipe", "Subscribe to team absences"),
            "current": ("S’abonner à ce calendrier", "Subscribe to this calendar"),
        }
        declarations = []
        slots = {
            "user.plugin.settings.actions": ["planning", "absences"],
            "project.detail.actions": ["project"],
            "employee.detail.actions": ["employee-projects", "employee-absences"],
            "team.detail.actions": ["team-projects", "team-absences"],
            "calendar.toolbar.actions": ["current"],
        }
        for slot, calendars in slots.items():
            for calendar in calendars:
                declarations.append({
                    "id": calendar.replace("-", "_"), "slot": slot, "type": "action",
                    "label": labels[calendar][0 if french else 1], "icon": "copy",
                    "behavior": "copy_url", "handler": "create_subscription",
                })
        return declarations

    def create_subscription(self, request, context):
        slot = context["slot"]
        selected = context["contribution"]["local_id"].replace("_", "-")
        if selected == "current":
            selected = {
                "project_all": "planning", "main": "absences", "project": "project",
                "employee": "employee-absences", "team": "team-absences",
            }.get(context["calendar_type"].value)
        object_id = 0
        if slot in ("project.detail.actions", "employee.detail.actions", "team.detail.actions"):
            entity = slot.split(".")[0]
            object_id = context[entity].pk
        elif slot == "calendar.toolbar.actions":
            object_id = context["calendar_id"] or 0
        if selected not in CALENDARS or (selected in SCOPED) != (object_id > 0):
            raise Http404
        token, secret = self.create_token(kind="user", name=f"{selected} #{object_id}",
                                          user=request.user, scopes=["ics"])
        signature = signing.Signer(salt=SIGNING_SALT).sign(f"{token.public_id}:{selected}:{object_id}")
        path_url = f"/{self.base_url}ics/{selected}/{object_id}/"
        return {"url": request.build_absolute_uri(f"{path_url}?{urlencode({'token': secret, 'scope': signature})}")}
