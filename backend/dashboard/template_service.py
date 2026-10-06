"""Create a personal dashboard from the shared registry without an HTTP request."""

from django.db import transaction
from django.db.models import Max
from django.contrib.auth import get_user_model

from .context_service import context_lookup
from .models import Dashboard, WidgetInstance
from .registry import DashboardContext, TEMPLATES, available_definitions, definition_for_template


def create_template_dashboard(user, template, name, context_object=None):
    if template not in TEMPLATES:
        raise ValueError(f"Unknown dashboard template: {template}")
    # The same pure validator is used by the API; no view or HTTP call is involved.
    from .api_v1 import validated_config

    context = DashboardContext.for_object(user, context_object) if context_object is not None else DashboardContext.personal(user)
    sources, definitions = available_definitions(context)
    row_x = row_y = row_height = 0
    with transaction.atomic():
        current = Dashboard.objects.filter(owner=user, scope="user")
        position = (current.aggregate(Max("position"))["position__max"] or 0) + 1 if context_object is None else 0
        dashboard = Dashboard.objects.create(
            owner=user, scope=context.context_type, name=name, position=position,
            is_default=not current.exists() if context_object is None else False,
            **(context_lookup(context_object) if context_object is not None else {}),
        )
        for index, item in enumerate(TEMPLATES[template]):
            definition = definition_for_template(definitions, item)
            if definition is None:
                continue
            source = sources[item.source_key]
            if item.renderer_key not in source.compatible_renderers:
                continue
            if context_object is not None:
                if row_x + definition.default_size[0] > 12:
                    row_y += row_height
                    row_x = row_height = 0
                x, y = row_x, row_y
                row_x += definition.default_size[0]
                row_height = max(row_height, definition.default_size[1])
            else:
                x, y = (index % 3) * 4, (index // 3) * 3
            WidgetInstance.objects.create(
                dashboard=dashboard, definition_key=definition.key,
                source_key=source.key, renderer_key=item.renderer_key,
                config=validated_config(item.config, source, definition, item.renderer_key, context),
                title=item.title, x=x, y=y,
                width=definition.default_size[0], height=definition.default_size[1],
                logical_order=index,
            )
    return dashboard


def get_or_create_dashboard_for_context(owner, context_object, template, name):
    """Serialize first creation per owner; preserve a context's existing widgets."""
    lookup = context_lookup(context_object)
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=owner.pk)
        dashboard = Dashboard.objects.filter(owner=owner, **lookup).first()
        return dashboard or create_template_dashboard(owner, template, name, context_object=context_object)
