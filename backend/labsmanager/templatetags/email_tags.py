from django import template

from labsmanager.email_urls import email_logo_url, notification_destination


register = template.Library()


@register.simple_tag
def labsmanager_email_logo():
    return email_logo_url()


@register.simple_tag
def notification_email_link(kind, pk=None):
    if kind not in ("settings", "calendar") and not pk:
        return ""
    return notification_destination(kind, pk)


@register.simple_tag
def project_reported_funds(fund_rows, project_id):
    """Select this Project's rows from the Funds already included in the email."""
    return [row for row in fund_rows if row["object"].project_id == project_id]


@register.filter
def leave_calendar_weeks(days):
    """Split the existing reporting dates into compact seven-day views."""
    return [days[index:index + 7] for index in range(0, len(days), 7)]


@register.simple_tag
def leave_calendar_day(day, leaves):
    """Return the covered half-days for display, using the Leave date bounds."""
    morning = afternoon = False
    for leave in leaves:
        if leave.start_date <= day <= leave.end_date:
            morning |= day > leave.start_date or getattr(leave, "start_period", "ST") == "ST"
            afternoon |= day < leave.end_date or getattr(leave, "end_period", "EN") == "EN"
    if morning and afternoon:
        return "full"
    if morning:
        return "am"
    if afternoon:
        return "pm"
    return ""
