"""HTTP adapter for the historical calendar plugin facade."""

import json
from datetime import datetime

from common.calendar import CalendarContext, CalendarType
from labsmanager.utils import get_data_from_request


def _date_time(value):
    if not value:
        return None
    raw = value[0] if isinstance(value, list) else value
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def legacy_calendar_context(request):
    """Translate a legacy GET/POST calendar request into CalendarContext."""
    if hasattr(request, "data"):
        filters = get_data_from_request(request)
    else:
        filters = request.GET.copy()
        filters.update(request.POST)
    settings_value = filters.get("settings", "{}") if filters else "{}"
    try:
        settings = json.loads(settings_value) if isinstance(settings_value, str) else settings_value
    except (TypeError, json.JSONDecodeError):
        settings = {}
    return CalendarContext(
        calendar_type=CalendarType.from_value(settings.get("cal_type")),
        user=request.user,
        start=_date_time(filters.get("start")),
        end=_date_time(filters.get("end")),
        filters=filters,
    )
