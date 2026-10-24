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
        return Response({"contributions": items})


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

    def get(self, request, calendar_type, object_id):
        context = resolve_calendar_context(calendar_type, object_id, request)
        return Response({"contributions": scoped_contributions(request, self.slot, context)})

    def post(self, request, calendar_type, object_id, identity):
        context = resolve_calendar_context(calendar_type, object_id, request)
        return scoped_action(request, self.slot, context, identity)


class UIUserPluginActions(UIBase):
    slot = "user.plugin.settings.actions"

    def get(self, request, plugin_key):
        context = resolve_user_plugin_context(plugin_key, request)
        return Response({"contributions": scoped_contributions(request, self.slot, context, plugin_key)})

    def post(self, request, plugin_key, identity):
        context = resolve_user_plugin_context(plugin_key, request)
        return scoped_action(request, self.slot, context, identity, plugin_key)


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
