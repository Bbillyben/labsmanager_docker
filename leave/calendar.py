"""Leave-domain conversion to the shared calendar contract."""

from datetime import datetime, time, timedelta
from django.db.models import Q

from common.calendar import LabsManagerCalendarEvent
from common.calendar.context import CalendarType
from leave.models import Leave
from labsmanager.admin_links_v1 import get_admin_change_url
from project.models import Participant
from staff.models import Team, TeamMate
from rest_framework.exceptions import ValidationError


def leave_to_calendar_event(leave, user=None):
    """Convert one Leave while preserving its half-day domain markers."""
    start = datetime.combine(leave.start_date, time.min)
    if leave.start_period == "MI":
        start += timedelta(hours=12)

    end = datetime.combine(leave.end_date, time.min)
    if leave.end_period == "MI":
        end += timedelta(hours=12)
    else:
        end += timedelta(days=1)

    return LabsManagerCalendarEvent(
        id=f"leave:{leave.pk}",
        title=leave.type.name,
        start=start,
        end=end,
        source="core",
        kind="leave",
        all_day=leave.start_period == "ST" and leave.end_period == "EN",
        color=str(leave.type.color),
        description=leave.comment,
        metadata={
            "leave_id": leave.pk,
            "admin_url": get_admin_change_url(user, leave),
            "employee_id": leave.employee_id,
            "leave_type_id": leave.type_id,
            "leave_type_short_name": leave.type.short_name,
            "leave_type_color": str(leave.type.color),
            "start_date": leave.start_date.isoformat(),
            "end_date": leave.end_date.isoformat(),
            "start_period": leave.start_period,
            "end_period": leave.end_period,
            "day_count": leave.dayCount,
        },
    )


def produce_leave_calendar_events(context, service):
    """Produce bounded Leave core events for Employee, Project or Team calendars."""
    if context.calendar_type == CalendarType.EMPLOYEE:
        queryset = Leave.objects.filter(employee_id=context.employee_id)
    elif context.calendar_type == CalendarType.PROJECT:
        participants = Participant.objects.filter(project_id=context.project_id).values("employee_id")
        queryset = Leave.objects.filter(employee_id__in=participants)
    elif context.calendar_type == CalendarType.TEAM:
        members = TeamMate.objects.filter(team_id=context.team_id).values("employee_id")
        leader = Team.objects.filter(pk=context.team_id).values("leader_id")
        queryset = Leave.objects.filter(Q(employee_id__in=members) | Q(employee_id__in=leader))
    else:
        return []
    queryset = queryset.select_related("type")
    if context.start:
        queryset = queryset.filter(end_date__gte=context.start)
    if context.end:
        queryset = queryset.filter(start_date__lte=context.end)
    leave_type = context.filters.get("type")
    if leave_type:
        try:
            queryset = queryset.filter(type_id=int(leave_type))
        except (TypeError, ValueError) as exc:
            raise ValidationError({"type": "Expected a Leave type id."}) from exc
    queryset = service.filter_calendar_queryset(queryset, context)
    return [leave_to_calendar_event(leave, context.user) for leave in queryset.order_by("start_date", "start_period", "end_date", "pk")]
