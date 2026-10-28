"""Session authenticated API for declarative React plugin contributions."""

import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from plugin.ui_contributions import (
    DETAIL_ENTITIES, SLOTS, action_result, declared_contributions, handler_context,
    is_visible, public_data, resolve_context, section_result,
    resolve_calendar_context, resolve_user_plugin_context,
)
from plugin.ui_assets import module_assets
from plugin.published_calendars import get_calendar

logger = logging.getLogger(__name__)


class UIBase(APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)


class UISlots(UIBase):
    def get(self, request):
        """Describe server slots; React only renders the slots it integrates."""
        return Response({"slots": [{"id": key, "type": slot.kind, "entity": slot.entity}
                                   for key, slot in SLOTS.items()]})


class UIContributions(UIBase):

    def get(self, request, entity, object_id):
        """Discover visible contributions only after resolving the object scope."""
        if entity not in DETAIL_ENTITIES:
            raise Http404
        context = resolve_context(entity, request, object_id)
        items = [public_data(item) for plugin, item in declared_contributions()
                 if SLOTS[item["slot"]].entity == entity and is_visible(plugin, item, request, context)]
        return Response({"contributions": items}, headers={"Cache-Control": "no-store"})


class UIPages(UIBase):
    def get(self, request):
        pages = [public_data(item) for plugin, item in declared_contributions()
                 if item["type"] == "page" and is_visible(plugin, item, request, {})]
        return Response({"contributions": pages}, headers={"Cache-Control": "no-store"})


class UIPageDetail(UIBase):
    def get(self, request, plugin_slug, page_id):
        for plugin, item in declared_contributions():
            if (item["type"] == "page" and item["plugin_slug"] == plugin_slug
                    and item["local_id"] == page_id and is_visible(plugin, item, request, {})):
                try:
                    assets = module_assets(plugin, item["module"])
                except (OSError, ValueError):
                    logger.exception("Plugin page assets unavailable: %s", item["id"])
                    return Response({"detail": "Plugin page unavailable."}, status=502)
                return Response({**public_data(item), **assets, "context": {}}, headers={"Cache-Control": "no-store"})
        raise Http404


def scoped_contributions(request, slot, context, plugin_key=None):
    return [public_data(item) for plugin, item in declared_contributions()
            if item["slot"] == slot and (plugin_key is None or plugin.slug == plugin_key)
            and is_visible(plugin, item, request, context)]


def scoped_action(request, slot, context, identity, plugin_key=None):
    for plugin, item in declared_contributions():
        if (item["id"] == identity and item["slot"] == slot
                and (plugin_key is None or plugin.slug == plugin_key)):
            if is_visible(plugin, item, request, context):
                return execute_action(request, plugin, item, context)
            break
    raise Http404


def module_action(request, slot, context, identity, module_context, plugin_key=None):
    for plugin, item in declared_contributions():
        if (item["id"] == identity and item["slot"] == slot and item["behavior"] == "module"
                and (plugin_key is None or plugin.slug == plugin_key)
                and is_visible(plugin, item, request, context)):
            try:
                assets = module_assets(plugin, item["module"])
            except (OSError, ValueError):
                logger.exception("Plugin action assets unavailable: %s", identity)
                return Response({"detail": "Plugin action unavailable."}, status=502)
            return Response({**public_data(item), "module": item["module"],
                             "component": item["component"], "api_version": item["api_version"], **assets,
                             "context": {**module_context, "name": module_context.get("name") or item["label"],
                                         "actionUrl": request.path}}, headers={"Cache-Control": "no-store"})
    raise Http404


def execute_action(request, plugin, item, context):
    try:
        result = getattr(plugin, item["handler"])(request, handler_context(context, item))
        # A copy_url action may reveal a one-time credential. Never cache it.
        return Response(action_result(item, result), headers={"Cache-Control": "no-store"})
    except (PermissionDenied, DjangoPermissionDenied, Http404, ValidationError):
        raise
    except Exception:
        logger.exception("UI contribution action failed: %s", item["id"])
        return Response({"detail": "Plugin action failed."}, status=502)


class UICalendarActions(UIBase):
    slot = "calendar.toolbar.actions"

    def get(self, request, calendar_type, object_id, identity=None):
        context = resolve_calendar_context(calendar_type, object_id, request)
        if identity is not None:
            obj = context.get("project") or context.get("employee") or context.get("team")
            return module_action(request, self.slot, context, identity,
                                 {"calendarType": calendar_type, "objectId": object_id,
                                  "name": str(obj) if obj else ""})
        return Response({"contributions": scoped_contributions(request, self.slot, context)})

    def post(self, request, calendar_type, object_id, identity):
        context = resolve_calendar_context(calendar_type, object_id, request)
        return scoped_action(request, self.slot, context, identity)


class UIUserPluginActions(UIBase):
    slot = "user.plugin.settings.actions"

    def get(self, request, plugin_key, identity=None):
        context = resolve_user_plugin_context(plugin_key, request)
        if identity is not None:
            return module_action(request, self.slot, context, identity, {"pluginKey": plugin_key}, plugin_key)
        return Response({"contributions": scoped_contributions(request, self.slot, context, plugin_key)})

    def post(self, request, plugin_key, identity):
        context = resolve_user_plugin_context(plugin_key, request)
        return scoped_action(request, self.slot, context, identity, plugin_key)


class UIUserPluginPanels(UIBase):
    slot = "user.plugin.settings.panels"

    def get(self, request, plugin_key, panel_id=None):
        context = resolve_user_plugin_context(plugin_key, request)
        matches = [(plugin, item) for plugin, item in declared_contributions()
                   if item["slot"] == self.slot and plugin.slug == plugin_key
                   and is_visible(plugin, item, request, context)]
        if panel_id is None:
            return Response({"contributions": [public_data(item) for _, item in matches]},
                            headers={"Cache-Control": "no-store"})
        for plugin, item in matches:
            if item["local_id"] == panel_id:
                try:
                    assets = module_assets(plugin, item["module"])
                except (OSError, ValueError):
                    logger.exception("Plugin settings assets unavailable: %s", item["id"])
                    return Response({"detail": "Plugin settings unavailable."}, status=502)
                return Response({**public_data(item), **assets, "context": {"pluginKey": plugin_key}},
                                headers={"Cache-Control": "no-store"})
        raise Http404


class UIPublishedCalendarActions(UIBase):
    slot = "published-calendar.actions"

    def _context(self, request, provider_slug, calendar_id):
        provider, calendar = get_calendar(request.user, provider_slug, calendar_id)
        return {"provider": provider, "calendar": calendar}

    def get(self, request, provider_slug, calendar_id, identity=None):
        context = self._context(request, provider_slug, calendar_id)
        if identity is not None:
            calendar = context["calendar"]
            return module_action(request, self.slot, context, identity,
                                 {"providerSlug": provider_slug, "calendarId": calendar_id,
                                  "name": calendar.name, "options": list(calendar.options)})
        return Response({"contributions": scoped_contributions(request, self.slot, context)})

    def post(self, request, provider_slug, calendar_id, identity):
        return scoped_action(request, self.slot,
                             self._context(request, provider_slug, calendar_id), identity)


class UIContributionDetail(UIBase):

    def _resolve(self, request, entity, object_id, identity, kind):
        if entity not in DETAIL_ENTITIES:
            raise Http404
        context = resolve_context(entity, request, object_id)
        for plugin, item in declared_contributions():
            if item["id"] == identity and item["type"] == kind and SLOTS[item["slot"]].entity == entity:
                if is_visible(plugin, item, request, context):
                    return plugin, item, context
                break
        raise Http404

    def get(self, request, entity, object_id, identity):
        """Load one section; failures stay local to that section."""
        for plugin, item in declared_contributions():
            if (item["id"] == identity and item["type"] == "action" and item["behavior"] == "module"
                    and item["slot"] == f"{entity}.detail.actions"):
                context = resolve_context(entity, request, object_id)
                return module_action(request, item["slot"], context, identity,
                                     {"entity": entity, "objectId": object_id,
                                      "name": str(context[entity])})
        for plugin, item in declared_contributions():
            if (item["id"] == identity and item["type"] == "tab"
                    and SLOTS[item["slot"]].entity == entity):
                if entity not in DETAIL_ENTITIES:
                    raise Http404
                context = resolve_context(entity, request, object_id)
                if not is_visible(plugin, item, request, context):
                    raise Http404
                try:
                    assets = module_assets(plugin, item["module"])
                except (OSError, ValueError):
                    logger.exception("Plugin tab assets unavailable: %s", item["id"])
                    return Response({"detail": "Plugin tab unavailable."}, status=502)
                return Response({**public_data(item), **assets,
                                 "context": {"entity": entity, "objectId": object_id}},
                                headers={"Cache-Control": "no-store"})
        plugin, item, context = self._resolve(request, entity, object_id, identity, "section")
        try:
            result = getattr(plugin, item["handler"])(request, handler_context(context, item))
            return Response(section_result(result))
        except (PermissionDenied, DjangoPermissionDenied, Http404, ValidationError):
            raise
        except Exception:
            logger.exception("UI contribution section failed: %s", identity)
            return Response({"detail": "Plugin section unavailable."}, status=502)

    def post(self, request, entity, object_id, identity):
        """Recheck object and contribution visibility before invoking an action."""
        plugin, item, context = self._resolve(request, entity, object_id, identity, "action")
        return execute_action(request, plugin, item, context)
