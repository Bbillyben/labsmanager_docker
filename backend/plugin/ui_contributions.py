"""Validated declarations for the React slots of active plugins."""

import logging
import re
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlsplit

from django.shortcuts import get_object_or_404
from django.http import Http404
from common.calendar import CalendarContext, CalendarType
from project.models import Project
from staff.models import Employee
from staff.team_api_v1 import team_queryset
from plugin.registry import registry

logger = logging.getLogger(__name__)
IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]+$")
ICONS = frozenset({"calendar", "copy", "external-link", "link", "info", "play"})
BEHAVIORS = frozenset({"copy_url", "open_url", "action"})
FORMATS = frozenset({"text", "properties", "items", "links"})


@dataclass(frozen=True)
class Slot:
    entity: str
    kind: str
    resolver: Callable | None


def resolve_project(request, object_id):
    return get_object_or_404(Project.get_instances_for_user(
        "view", request.user, Project.objects.filter(pk=object_id)), pk=object_id)


def resolve_employee(request, object_id):
    return get_object_or_404(Employee.get_instances_for_user(
        "view", request.user, Employee.objects.filter(pk=object_id)), pk=object_id)


def resolve_team(request, object_id):
    return get_object_or_404(team_queryset(request.user), pk=object_id)


# A new React extension point is declared here, independently of the mixin.
SLOTS = {
    "project.detail.actions": Slot("project", "action", resolve_project),
    "project.detail.sections": Slot("project", "section", resolve_project),
    "employee.detail.actions": Slot("employee", "action", resolve_employee),
    "employee.detail.sections": Slot("employee", "section", resolve_employee),
    "team.detail.actions": Slot("team", "action", resolve_team),
    "team.detail.sections": Slot("team", "section", resolve_team),
    "calendar.toolbar.actions": Slot("calendar", "action", None),
    "user.plugin.settings.actions": Slot("user-plugin", "action", None),
}
DETAIL_ENTITIES = frozenset({"project", "employee", "team"})


CALENDAR_SCOPES = {
    CalendarType.MAIN: (None, None),
    CalendarType.PROJECT_ALL: (None, None),
    CalendarType.PROJECT: ("project", resolve_project),
    CalendarType.EMPLOYEE: ("employee", resolve_employee),
    CalendarType.TEAM: ("team", resolve_team),
}


def resolve_calendar_context(calendar_type, object_id, request):
    """Use the normalized calendar context after authorizing its root object."""
    try:
        calendar_type = CalendarType(calendar_type)
    except ValueError as exc:
        raise Http404 from exc
    if calendar_type not in CALENDAR_SCOPES:
        raise Http404
    entity, resolver = CALENDAR_SCOPES[calendar_type]
    if (resolver is None and object_id != 0) or (resolver is not None and object_id <= 0):
        raise Http404
    obj = resolver(request, object_id) if resolver else None
    context = CalendarContext(calendar_type=calendar_type, user=request.user,
                              **({f"{entity}_id": obj.pk} if obj else {}))
    return {"calendar_context": context, "calendar_type": calendar_type,
            "calendar_id": obj.pk if obj else None, **({entity: obj} if obj else {})}


def resolve_user_plugin_context(plugin_key, request):
    """Bind personal actions to the active plugin named by the page."""
    plugin = registry.get_plugin(plugin_key, active=True)
    if plugin is None:
        raise Http404
    return {"plugin": plugin, "plugin_key": plugin_key}


def resolve_context(entity, request, object_id):
    """Resolve a page object through the view boundary declared by its slot."""
    slot = next((slot for slot in SLOTS.values() if slot.entity == entity and slot.resolver is not None), None)
    if slot is None:
        raise ValueError("Unknown contribution entity")
    return {entity: slot.resolver(request, object_id)}


def _definition(plugin, raw):
    if not isinstance(raw, dict):
        raise ValueError("Contribution must be a dictionary")
    local_id = raw.get("id")
    slot = raw.get("slot")
    kind = raw.get("type")
    handler = raw.get("handler")
    label = raw.get("label")
    if not isinstance(local_id, str) or not IDENTIFIER.fullmatch(local_id):
        raise ValueError("Invalid contribution id")
    if slot not in SLOTS or kind != SLOTS[slot].kind:
        raise ValueError("Unknown slot or invalid contribution type")
    if not isinstance(label, str) or not label.strip() or len(label) > 150:
        raise ValueError("Invalid contribution label")
    if not isinstance(handler, str) or not IDENTIFIER.fullmatch(handler) or handler.startswith("_") or not callable(getattr(plugin, handler, None)):
        raise ValueError("Invalid contribution handler")
    visible = raw.get("visible")
    if visible is not None and (not isinstance(visible, str) or not IDENTIFIER.fullmatch(visible) or visible.startswith("_") or not callable(getattr(plugin, visible, None))):
        raise ValueError("Invalid visibility handler")
    priority = raw.get("priority", 0)
    if type(priority) is not int or not -1000 <= priority <= 1000:
        raise ValueError("Invalid contribution priority")
    icon = raw.get("icon")
    if icon is not None and icon not in ICONS:
        raise ValueError("Unknown icon")
    behavior = raw.get("behavior", "action") if kind == "action" else None
    if kind == "action" and behavior not in BEHAVIORS:
        raise ValueError("Unknown action behavior")
    confirm = raw.get("confirm", False)
    if type(confirm) is not bool:
        raise ValueError("Invalid confirmation flag")
    if kind == "section" and ("behavior" in raw or confirm or icon):
        raise ValueError("Unsupported section option")
    return {
        "id": f"plugin:{plugin.slug}:{local_id}", "plugin_slug": plugin.slug,
        "local_id": local_id, "slot": slot, "type": kind,
        "label": label.strip(), "icon": icon, "behavior": behavior,
        "confirm": confirm, "priority": priority,
        "handler": handler, "visible": visible,
    }


def declared_contributions():
    """Validate each declaration without allowing one faulty plugin to hide others."""
    found = []
    for plugin in registry.with_mixin("uicontribution", active=True):
        seen = set()
        try:
            declarations = getattr(plugin, "UI_CONTRIBUTIONS", ())
        except Exception:
            logger.exception("Unable to read UI contributions from plugin %s", plugin.slug)
            continue
        if not isinstance(declarations, (list, tuple)):
            logger.warning("Invalid UI contributions for plugin %s", plugin.slug)
            continue
        for raw in declarations[:100]:
            try:
                item = _definition(plugin, raw)
                if item["local_id"] in seen:
                    raise ValueError("Duplicate contribution id")
                seen.add(item["local_id"])
                found.append((plugin, item))
            except Exception:
                logger.exception("Invalid UI contribution in plugin %s", plugin.slug)
    return sorted(found, key=lambda pair: (pair[1]["priority"], pair[1]["plugin_slug"], pair[1]["local_id"]))


def handler_context(context, item):
    return {**context, "slot": item["slot"], "contribution": {
        "id": item["id"], "plugin_slug": item["plugin_slug"], "local_id": item["local_id"]}}


def is_visible(plugin, item, request, context):
    if not item["visible"]:
        return True
    try:
        return getattr(plugin, item["visible"])(request, handler_context(context, item)) is True
    except Exception:
        logger.exception("UI contribution visibility failed: %s", item["id"])
        return False


def public_data(item):
    return {key: value for key, value in item.items() if key not in ("handler", "visible", "local_id")}


def safe_url(value):
    if not isinstance(value, str) or not value or len(value) > 2048 or any(ord(char) < 32 or char == "\\" for char in value):
        raise ValueError("Invalid URL")
    parts = urlsplit(value)
    if parts.scheme in ("http", "https") and parts.netloc and not parts.username and not parts.password:
        return value
    if value.startswith("/") and not value.startswith("//") and not parts.scheme and not parts.netloc:
        return value
    raise ValueError("Unsupported URL")


def action_result(item, result):
    if not isinstance(result, dict):
        raise ValueError("Action result must be a dictionary")
    if item["behavior"] in ("copy_url", "open_url"):
        return {"url": safe_url(result.get("url"))}
    message = result.get("message", "")
    if not isinstance(message, str) or len(message) > 500:
        raise ValueError("Invalid action message")
    return {"message": message}


def section_result(result):
    if not isinstance(result, dict) or result.get("format") not in FORMATS:
        raise ValueError("Invalid section format")
    format_name = result["format"]
    if format_name == "text":
        text = result.get("text")
        if not isinstance(text, str) or len(text) > 5000:
            raise ValueError("Invalid section text")
        return {"format": format_name, "text": text}
    items = result.get("items")
    if not isinstance(items, list) or len(items) > 50:
        raise ValueError("Invalid section items")
    rows = []
    for row in items:
        if not isinstance(row, dict) or not isinstance(row.get("label"), str) or len(row["label"]) > 300:
            raise ValueError("Invalid section item")
        clean = {"label": row["label"]}
        if format_name == "properties":
            value = row.get("value")
            if not isinstance(value, (str, int, float, bool)) or len(str(value)) > 1000:
                raise ValueError("Invalid property value")
            clean["value"] = str(value)
        elif format_name == "links":
            clean["url"] = safe_url(row.get("url"))
        elif format_name == "items":
            description = row.get("description", "")
            if not isinstance(description, str) or len(description) > 1000:
                raise ValueError("Invalid item description")
            clean["description"] = description
            if "url" in row:
                clean["url"] = safe_url(row["url"])
        rows.append(clean)
    return {"format": format_name, "items": rows}
