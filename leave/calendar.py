"""Leave-domain conversion to the shared calendar contract."""

from datetime import datetime, time, timedelta

from common.calendar import LabsManagerCalendarEvent


def leave_to_calendar_event(leave):
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
