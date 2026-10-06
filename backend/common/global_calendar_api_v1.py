"""Read-only global calendars built from the existing Calendar and Planning scopes."""

from datetime import date, datetime

from django.db.models import Q
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from common.calendar import CalendarContext, CalendarService, CalendarType
from endpoints.models import Milestones
from endpoints.planning_serializers_v1 import PLANNING_DISPLAY_STATES, PlanningMilestoneV1Serializer
from endpoints.planning_v1 import planning_serializer_context, preload_planning_items
from leave.calendar import produce_leave_calendar_events
from project.api_v1 import ProjectListV1Filter
from project.models import Project
from staff.filters_v1 import EmployeeListV1Filter
from staff.models import Employee


def _range(request):
    try:
        start = date.fromisoformat(request.query_params.get("from", ""))
        end = date.fromisoformat(request.query_params.get("to", ""))
    except ValueError as exc:
        raise ValidationError({"from": "Expected ISO from and to dates."}) from exc
    if start > end:
        raise ValidationError({"to": "Must be on or after from."})
    return start, end


def _within_range(event, context):
    start = event.start.date() if isinstance(event.start, datetime) else event.start
    end = event.end.date() if isinstance(event.end, datetime) else event.end or start
    return start <= context.end and end >= context.start


def _filtered_employees(request):
    visible = Employee.get_instances_for_user("view", request.user, Employee.objects.all())
    filtered = EmployeeListV1Filter(request.query_params, queryset=visible, request=request)
    if not filtered.is_valid():
        raise ValidationError(filtered.errors)
    employees = filtered.qs
    selected = request.query_params.get("employee")
    if selected:
        if not selected.isdecimal():
            raise ValidationError({"employee": "Expected Employee id."})
        employees = employees.filter(pk=int(selected))
    return employees


def _filtered_projects(request):
    visible = Project.get_instances_for_user("view", request.user, Project.objects.all())
    filtered = ProjectListV1Filter(request.query_params, queryset=visible, request=request)
    if not filtered.is_valid():
        raise ValidationError(filtered.errors)
    projects = filtered.qs
    selected = request.query_params.get("project")
    if selected:
        if not selected.isdecimal():
            raise ValidationError({"project": "Expected Project id."})
        projects = projects.filter(pk=int(selected))
    return projects.distinct()


class GlobalCalendarBase(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    calendar_type = None

    def context(self, request, *, bounded=False):
        start, end = _range(request) if bounded else (None, None)
        return CalendarContext(
            calendar_type=self.calendar_type, user=request.user,
            start=start, end=end, filters=request.query_params,
        )


class GlobalEmployeeCalendar(GlobalCalendarBase):
    calendar_type = CalendarType.MAIN

    def get(self, request):
        context = self.context(request, bounded=True)
        service = CalendarService()
        employees = _filtered_employees(request)
        core = produce_leave_calendar_events(context, service, employees)
        visible_ids = {str(pk) for pk in employees.values_list("pk", flat=True)}
        events = [event for event in service.get_events(context, core)
                  if _within_range(event, context) and (
                      event.metadata.get("employee_id") is None
                      or str(event.metadata.get("employee_id")) in visible_ids
                  )]
        # The same filtered, visible queryset supplies both event labels and all
        # Resource rows, including Employees without Leave in this date range.
        resources = [
            {"id": str(pk), "title": f"{first} {last}".strip()}
            for pk, first, last in employees.order_by("first_name", "last_name", "pk")
            .values_list("pk", "first_name", "last_name")
        ]
        employee_names = {item["id"]: item["title"] for item in resources}
        return Response({"events": [event.as_dict() for event in events], "employee_names": employee_names,
                         "resources": resources})


class GlobalProjectPlanning(GlobalCalendarBase):
    calendar_type = CalendarType.PROJECT_ALL

    def get(self, request):
        context = self.context(request, bounded=True)
        projects = _filtered_projects(request).filter(
            Q(start_date__lte=context.end) | Q(start_date__isnull=True),
            Q(end_date__gte=context.start) | Q(end_date__isnull=True),
        )
        project_ids = projects.values("pk")
        # Open-ended work still intersects the selected window. Milestones use
        # their end date as the only dated point, as in the Project Gantt.
        scoped = Milestones.objects.filter(project_id__in=project_ids).filter(
            Q(start_date__lte=context.end) | Q(start_date__isnull=True),
            Q(end_date__gte=context.start) | Q(end_date__isnull=True),
        )
        serializer_context = planning_serializer_context(request.user, scoped)
        items = PlanningMilestoneV1Serializer(
            preload_planning_items(scoped), many=True, context=serializer_context,
        ).data
        status = request.query_params.get("milestone_status")
        if status:
            if status not in PLANNING_DISPLAY_STATES:
                raise ValidationError({"milestone_status": "Unknown Planning status."})
            items = [item for item in items if item["display_state"] == status]
        visible_ids = {str(pk) for pk in projects.values_list("pk", flat=True)}
        service = CalendarService()
        plugin_events = [event for event in service.get_plugin_events(context)
                         if _within_range(event, context) and (
                             event.metadata.get("project_id") is None
                             or str(event.metadata.get("project_id")) in visible_ids
                         )]
        return Response({
            "projects": list(projects.order_by("name", "pk").values("id", "name", "start_date", "end_date")),
            "items": items,
            "events": [event.as_dict() for event in plugin_events],
            "milestone_statuses": PLANNING_DISPLAY_STATES,
        })


class GlobalCalendarFilters(GlobalCalendarBase):
    def get(self, request, scope):
        if scope not in ("employees", "projects"):
            raise ValidationError({"scope": "Unknown calendar scope."})
        self.calendar_type = CalendarType.MAIN if scope == "employees" else CalendarType.PROJECT_ALL
        return Response([item.as_dict() for item in CalendarService().get_filters(self.context(request))])
