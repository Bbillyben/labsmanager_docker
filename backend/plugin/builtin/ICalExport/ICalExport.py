"""Personal, read-only subscriptions to the existing calendar and Planning views."""

from datetime import date, datetime, timedelta, timezone as datetime_timezone
from hashlib import sha256
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.core import signing
from django.http import Http404, HttpRequest, HttpResponse, QueryDict
from django.urls import path
from django.utils import timezone
from django.utils.translation import get_language
from icalendar import Calendar, Event

from labsmanager.email_urls import django_email_url
from labsmanager.react_urls import react_public_url
from plugin import LabManagerPlugin, registry
from plugin.mixins import TokenMixin, UIContributionMixin, UrlsMixin
from plugin.tokens import TokenError


CALENDARS = frozenset({
    "planning", "absences", "project", "employee-projects", "employee-absences",
    "team-projects", "team-absences",
})
PROJECT_CALENDARS = frozenset({"project", "employee-projects", "team-projects"})
SCOPED = frozenset({"project", "employee-projects", "employee-absences", "team-projects", "team-absences"})
SIGNING_SALT = "plugin.icalexport.subscription"


def _invoke(view, user, start, end, *, include_details=False, context=None, **kwargs):
    """Read the same authorized and serialized provider used by the React page."""
    request = HttpRequest()
    request.method = "GET"
    request.path = "/"
    request.GET = QueryDict(mutable=True)
    request.GET.update({"from": start.isoformat(), "to": end.isoformat(), "consumer": "ical"})
    if context is not None:
        request.GET["context"] = context
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
    from common.calendar import CalendarType
    from common.global_calendar_api_v1 import GlobalEmployeeCalendar, GlobalProjectPlanning
    from endpoints.api_v1 import ProjectPlanningV1View
    from project.calendar_api_v1 import ProjectCalendarV1View
    from staff.api_v1 import EmployeeCalendarV1View, EmployeeMilestoneV1View
    from staff.team_api_v1 import TeamCalendarV1View

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
        items = [item for item in _invoke(EmployeeMilestoneV1View, user, start, end, pk=object_id)
                 if _item_in_window(item, start, end)]
        events = _invoke(
            EmployeeCalendarV1View, user, start, end, pk=object_id,
            context=CalendarType.EMPLOYEE_GANTT.value, include_details=True,
        )
    elif calendar == "team-projects":
        from django.db.models import Q
        from django.shortcuts import get_object_or_404
        from endpoints.models import Milestones
        from endpoints.planning_serializers_v1 import PlanningMilestoneV1Serializer
        from endpoints.planning_v1 import planning_serializer_context, preload_planning_items
        from project.models import Project
        from staff.team_api_v1 import team_members, team_queryset

        team = get_object_or_404(team_queryset(user), pk=object_id)
        member_ids = set(team_members(team).values_list("pk", flat=True))
        visible_projects = Project.get_instances_for_user("view", user, Project.objects.all())
        assigned = Milestones.objects.filter(
            employee__pk__in=member_ids, project__in=visible_projects,
        ).filter(
            Q(start_date__lte=end) | Q(start_date__isnull=True),
            Q(end_date__gte=start) | Q(end_date__isnull=True),
        ).distinct()
        serialized = PlanningMilestoneV1Serializer(
            preload_planning_items(assigned), many=True,
            context=planning_serializer_context(user, assigned),
        ).data
        for row in serialized:
            if not _item_in_window(row, start, end):
                continue
            item = dict(row)
            assignees = [employee for employee in item["employees"] if employee["id"] in member_ids]
            if assignees and all(employee["can_view"] for employee in assignees):
                names = [f"{employee['first_name']} {employee['last_name']}".strip()
                         for employee in assignees]
                if all(names):
                    item["ical_assignees"] = names
            items.append(item)
        team_events = _invoke(TeamCalendarV1View, user, start, end,
                              team_id=object_id, include_details=True)
        events = _scoped_events(team_events, team_id=object_id)
    else:
        raise Http404
    return items, [event for event in events if _event_in_window(event, start, end)
                   and (calendar not in PROJECT_CALENDARS or event.get("kind") != "leave")]


def _event_in_window(event, start, end):
    event_start = _date(event.get("start"))
    event_end = _date(event.get("end")) or event_start
    if event_start is None:
        return False
    event_start = event_start.date() if isinstance(event_start, datetime) else event_start
    event_end = event_end.date() if isinstance(event_end, datetime) else event_end
    return event_start <= end and event_end >= start


def _item_in_window(item, start, end):
    item_start = _date(item.get("start_date") or item.get("end_date"))
    item_end = _date(item.get("end_date")) or item_start
    return item_start is not None and item_start <= end and item_end >= start


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


def _add_event(ical, uid, title, start, end, description="", all_day=True, url=None):
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
    if url:
        event.add("url", url)
    ical.add_component(event)


def _calendar_name(calendar, object_id):
    if calendar == "planning":
        return "LabsManager - Planning général"
    if calendar == "absences":
        return "LabsManager - Absences générales"
    if calendar == "project":
        from project.models import Project
        return f"LabsManager - Projet : {Project.objects.get(pk=object_id).name}"
    if calendar.startswith("employee-"):
        from staff.models import Employee
        employee = Employee.objects.get(pk=object_id)
        subject = employee.user_name
    else:
        from staff.models import Team
        subject = Team.objects.get(pk=object_id).name
    category = "Projets" if calendar.endswith("projects") else "Absences"
    return f"LabsManager - {category} : {subject}"


def _public_react_url(path):
    public = urlsplit(settings.REACT_PUBLIC_URL.strip())
    if public.scheme not in ("http", "https") or not public.netloc:
        return None
    return react_public_url(path)


def _description_with_link(description, url):
    if not url:
        return description
    return f"{description}\n\nOuvrir dans LabsManager :\n{url}" if description else f"Ouvrir dans LabsManager :\n{url}"


def build_ical(items, events, name="LabsManager", *, calendar=None, object_id=0, user=None):
    ical = Calendar()
    ical.add("prodid", "-//LabsManager//ICalExport//EN")
    ical.add("version", "2.0")
    ical.add("calscale", "GREGORIAN")
    ical.add("name", name)
    ical.add("x-wr-calname", name)
    visible_employee_ids = set()
    if user is not None:
        from staff.models import Employee
        leave_employee_ids = {(event.get("metadata") or {}).get("employee_id") for event in events
                              if event.get("source", "core") == "core" and event.get("kind") == "leave"}
        if leave_employee_ids:
            visible_employee_ids = set(Employee.get_instances_for_user(
                "view", user, Employee.objects.filter(pk__in=leave_employee_ids)
            ).values_list("pk", flat=True))
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
        project = item.get("project") or {}
        title = item.get("name") or ""
        if calendar in ("planning", "employee-projects", "team-projects") and project.get("name"):
            title = f"{project['name']} - {title}"
        if calendar == "team-projects" and item.get("ical_assignees"):
            title = f"{title} ({', '.join(item['ical_assignees'])})"
        url = None
        if project.get("can_view") and project.get("id"):
            url = _public_react_url(f"projects/{project['id']}/tasks")
        elif calendar == "employee-projects":
            url = _public_react_url(f"employees/{object_id}/projects")
        description = _description_with_link(item.get("desc") or "", url)
        _add_event(ical, uid, title, start, end, description, url=url)
    for source in events:
        uid = f"event:{source.get('source', 'core')}:{source['id']}"
        if uid in seen:
            continue
        seen.add(uid)
        start = _date(source.get("start"))
        end = _date(source.get("end"))
        # The calendar domain already expresses all-day ends as exclusive.
        summary = (source.get("metadata") or {}).get("detailed_title") or source.get("title")
        metadata = source.get("metadata") or {}
        url = None
        if source.get("source", "core") == "core" and source.get("kind") == "leave":
            employee_id = metadata.get("employee_id")
            if employee_id in visible_employee_ids:
                url = _public_react_url(f"employees/{employee_id}/leaves")
        _add_event(ical, uid, summary, start, end,
                   _description_with_link(source.get("description") or "", url),
                   source.get("all_day", True), url=url)
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
    name = _calendar_name(calendar, object_id)
    response = HttpResponse(build_ical(items, events, name, calendar=calendar,
                                       object_id=object_id, user=owner.user),
                            content_type="text/calendar; charset=utf-8")
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
            "employee-projects": ("S’abonner aux tâches et jalons de l’employé", "Subscribe to employee tasks and milestones"),
            "employee-absences": ("S’abonner aux absences de l’employé", "Subscribe to employee absences"),
            "team-projects": ("S’abonner aux tâches et jalons de l’équipe", "Subscribe to team tasks and milestones"),
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
        return {"url": django_email_url(f"{path_url}?{urlencode({'token': secret, 'scope': signature})}")}
