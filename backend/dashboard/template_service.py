"""Create a personal dashboard from the shared registry without an HTTP request."""

from django.db import transaction
from django.db.models import Max
from django.contrib.auth import get_user_model

from .context_service import context_lookup
from .models import Dashboard, WidgetInstance
from .registry import DashboardContext, TEMPLATES, available_definitions, definition_for_template


def _template_size(item, definition):
    width = item.width if type(item.width) is int else definition.default_size[0]
    height = item.height if type(item.height) is int else definition.default_size[1]
    width = min(max(width, definition.min_size[0]), definition.max_size[0], 12)
    height = min(max(height, definition.min_size[1]), definition.max_size[1])
    return width, height


def _fits_position(x, y, width, height, occupied):
    if type(x) is not int or type(y) is not int or x < 0 or y < 0 or x + width > 12:
        return False
    return all(x + width <= ox or ox + ow <= x or y + height <= oy or oy + oh <= y
               for ox, oy, ow, oh in occupied)


def _find_free_position(width, height, occupied):
    y = 0
    while True:
        for x in range(13 - width):
            if _fits_position(x, y, width, height, occupied):
                return x, y
        y += 1


def _template_config(item, context):
    config = dict(item.config)
    if item.source_key == "core.employee-workload" and config.get("scope") == "single":
        from staff.models import Employee
        employee = Employee.get_instances_for_user(
            "view", context.user, Employee.objects.filter(user=context.user)
        ).first()
        if employee is None:
            return None
        config["employee_id"] = employee.pk
    return config


def create_template_dashboard(user, template, name, context_object=None):
    if template not in TEMPLATES:
        raise ValueError(f"Unknown dashboard template: {template}")
    # The same pure validator is used by the API; no view or HTTP call is involved.
    from .api_v1 import validated_config

    context = DashboardContext.for_object(user, context_object) if context_object is not None else DashboardContext.personal(user)
    sources, definitions = available_definitions(context)
    occupied = []
    logical_order = 0
    with transaction.atomic():
        current = Dashboard.objects.filter(owner=user, scope="user")
        position = (current.aggregate(Max("position"))["position__max"] or 0) + 1 if context_object is None else 0
        dashboard = Dashboard.objects.create(
            owner=user, scope=context.context_type, name=name, position=position,
            is_default=not current.exists() if context_object is None else False,
            **(context_lookup(context_object) if context_object is not None else {}),
        )
        for item in TEMPLATES[template]:
            definition = definition_for_template(definitions, item)
            if definition is None:
                continue
            source = sources[item.source_key]
            if item.renderer_key not in source.compatible_renderers:
                continue
            config = _template_config(item, context)
            if config is None:
                continue
            width, height = _template_size(item, definition)
            x, y = ((item.x, item.y) if item.x is not None and item.y is not None
                    and _fits_position(item.x, item.y, width, height, occupied)
                    else _find_free_position(width, height, occupied))
            WidgetInstance.objects.create(
                dashboard=dashboard, definition_key=definition.key,
                source_key=source.key, renderer_key=item.renderer_key,
                config=validated_config(config, source, definition, item.renderer_key, context),
                title=item.title, x=x, y=y,
                width=width, height=height,
                logical_order=logical_order,
            )
            occupied.append((x, y, width, height))
            logical_order += 1
    return dashboard


def get_or_create_dashboard_for_context(owner, context_object, template, name):
    """Serialize first creation per owner; preserve a context's existing widgets."""
    lookup = context_lookup(context_object)
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=owner.pk)
        dashboard = Dashboard.objects.filter(owner=owner, **lookup).first()
        return dashboard or create_template_dashboard(owner, template, name, context_object=context_object)
