"""Absolute destinations for HTML email, with the legacy site as fallback."""

from urllib.parse import urljoin, urlsplit

from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse

from .react_urls import react_public_url


def django_email_url(path=""):
    domain = Site.objects.get_current().domain.strip().rstrip("/")
    public = urlsplit(settings.REACT_PUBLIC_URL.strip())
    origin = domain if "://" in domain else f"{public.scheme or 'http'}://{domain}"
    return urljoin(f"{origin}/", path.lstrip("/"))


def react_email_url(path, legacy_path):
    public = urlsplit(settings.REACT_PUBLIC_URL.strip())
    if public.scheme and public.netloc:
        return react_public_url(path)
    return django_email_url(legacy_path)


def email_logo_url():
    path = f"{settings.STATIC_URL.lstrip('/')}img/labsmanager/labsmanager-logo.png"
    public = urlsplit(settings.REACT_PUBLIC_URL.strip())
    if public.scheme and public.netloc:
        return urljoin(f"{public.scheme}://{public.netloc}/", path)
    return django_email_url(path)


def notification_destination(kind, pk=None):
    """Link email cards to an existing React page, retaining a legacy fallback."""
    if kind == "project":
        return react_email_url(f"projects/{pk}/", reverse("project_single", kwargs={"pk": pk}))
    if kind == "planning":
        return react_email_url(f"projects/{pk}/tasks", reverse("project_single", kwargs={"pk": pk}))
    if kind == "funding":
        return react_email_url(f"projects/{pk}/funding", reverse("project_single", kwargs={"pk": pk}))
    if kind == "employee":
        return react_email_url(f"employees/{pk}/", reverse("employee", kwargs={"pk": pk}))
    if kind == "team":
        return react_email_url(f"teams/{pk}", reverse("team_single", kwargs={"pk": pk}))
    if kind == "calendar":
        return react_email_url("calendars", reverse("calendar_main"))
    if kind == "settings":
        return react_email_url("settings/notifications", reverse("settings"))
    raise ValueError(f"Unknown email destination: {kind}")
