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
