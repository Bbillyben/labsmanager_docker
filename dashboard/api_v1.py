"""Owner-scoped personal and Project dashboards with backend-resolved context."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Dashboard, WidgetInstance
from .context_service import resolve_context, visible_project
from .registry import CORE_RENDERERS, DashboardContext, TEMPLATES, available_definitions, definition_for_template


def context_for(request, dashboard=None):
    return resolve_context(request.user, dashboard) if dashboard is not None else DashboardContext.personal(request.user)


def owned(request, pk):
    dashboard = get_object_or_404(Dashboard.objects.filter(owner=request.user), pk=pk)
    context_for(request, dashboard)
    return dashboard


def definition_data(item):
    return {
        "key": item.key, "title": item.title, "category": item.category,
        "renderer_key": item.renderer_key, "source_key": item.source_key,
        "supported_scopes": item.supported_scopes, "default_size": item.default_size,
        "min_size": item.min_size, "max_size": item.max_size,
        "allow_multiple": item.allow_multiple, "printable": item.printable,
        "icon": item.icon, "config_fields": item.config_fields,
    }


def widget_data(widget, definitions, sources, context):
    definition = definitions.get(widget.definition_key)
    source_key = widget.source_key or (definition.source_key if definition else "")
    source = sources.get(source_key) if definition else None
    data = None
    error = False
    if source and widget.renderer_key in source.compatible_renderers:
        try:
            data = source.provider(context, widget.config)
            if isinstance(data, dict) and "__renderers__" in data:
                data = data["__renderers__"][widget.renderer_key]
        except Exception:
            error = True
    return {
        "id": str(widget.pk), "definition_key": widget.definition_key,
        "source_key": source_key, "renderer_key": widget.renderer_key, "title": widget.title,
        "config": widget.config, "x": widget.x, "y": widget.y,
        "width": widget.width, "height": widget.height,
        "logical_order": widget.logical_order,
        "available": bool(definition and source and widget.renderer_key in source.compatible_renderers), "data": data, "error": error,
    }


def dashboard_data(dashboard, definitions=None, sources=None, context=None):
    data = {
        "id": dashboard.pk, "name": dashboard.name, "icon": dashboard.icon,
        "is_default": dashboard.is_default, "position": dashboard.position,
        "scope": dashboard.scope, "project_id": dashboard.context_object_id if dashboard.scope == "project" else None,
    }
    if definitions is not None:
        data["widgets"] = [widget_data(widget, definitions, sources, context) for widget in dashboard.widgets.all()]
    return data


def validated_name(value):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 120:
        raise ValidationError({"name": "A name of 1–120 characters is required."})
    return value.strip()


def config_schema(source, definition, renderer_key):
    schema = dict(source.config_fields)
    # Legacy plugin definitions may still declare string fields on the widget.
    for key, field in definition.config_fields.items():
        if key not in schema:
            schema[key] = field
    for key, field in CORE_RENDERERS.get(renderer_key, {}).get("config_fields", {}).items():
        if key in schema:
            raise ValidationError({"config": "Conflicting configuration field."})
        schema[key] = field
    return schema


def validated_config(value, source, definition, renderer_key, context=None):
    schema = config_schema(source, definition, renderer_key)
    if not isinstance(value, dict) or set(value) - set(schema):
        raise ValidationError({"config": "Unsupported configuration field."})
    result = {}
    for key, raw_field in schema.items():
        field = {"type": raw_field, "max_length": 500} if isinstance(raw_field, str) else raw_field
        if key not in value:
            if field.get("required") and "default" not in field:
                raise ValidationError({"config": f"{key} is required."})
            if "default" in field:
                result[key] = field["default"]
            continue
        item = value[key]
        kind = field.get("type")
        valid = (kind == "string" and isinstance(item, str) and len(item) <= field.get("max_length", 500)
                 or kind == "boolean" and type(item) is bool
                 or kind == "integer" and type(item) is int and field.get("min", 0) <= item <= field.get("max", 1000000)
                 or kind == "project" and type(item) is int and item > 0
                 or kind == "choice" and item in field.get("choices", ()))
        if not valid or (field.get("required") and item == ""):
            raise ValidationError({"config": f"Invalid value for {key}."})
        result[key] = item
    if "project_scope" in schema:
        has_project_context = context is not None and context.context_type == "project" and context.context_object is not None
        scope = result.get("project_scope", "context" if has_project_context else "all_visible")
        if scope == "context" and context is not None and not has_project_context:
            raise ValidationError({"project_scope": "Project context unavailable."})
        if scope == "specific_project":
            project_id = result.get("project_id")
            if not project_id:
                raise ValidationError({"project_id": "A visible Project is required."})
            if context is not None:
                from project.models import Project
                if not Project.get_instances_for_user("view", context.user, Project.objects.all()).filter(pk=project_id).exists():
                    raise ValidationError({"project_id": "A visible Project is required."})
        elif "project_id" in result:
            raise ValidationError({"project_id": "Only available for a specific Project."})
    return result


def validated_size(definition, x, y, width, height):
    if any(type(value) is not int for value in (x, y, width, height)):
        raise ValidationError({"layout": "Integer coordinates and size required."})
    if x < 0 or y < 0 or width < definition.min_size[0] or height < definition.min_size[1]:
        raise ValidationError({"layout": "Position or size below minimum."})
    if width > definition.max_size[0] or height > definition.max_size[1] or x + width > 12:
        raise ValidationError({"layout": "Size exceeds grid bounds."})


class DashboardCollection(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            dashboards = list(Dashboard.objects.filter(owner=request.user, scope="user"))
            if dashboards and not any(item.is_default for item in dashboards):
                dashboards[0].is_default = True
                dashboards[0].save(update_fields=("is_default", "updated_at"))
        return Response([dashboard_data(item) for item in dashboards])

    def post(self, request):
        if not isinstance(request.data, dict) or set(request.data) - {"name", "template"}:
            raise ValidationError("Expected name and template.")
        name = validated_name(request.data.get("name"))
        template = request.data.get("template")
        if template not in TEMPLATES or template == "project":
            raise ValidationError({"template": "Unknown template."})
        context = context_for(request)
        sources, definitions = available_definitions(context)
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            current = Dashboard.objects.filter(owner=request.user, scope="user")
            position = (current.aggregate(Max("position"))["position__max"] or 0) + 1
            dashboard = Dashboard.objects.create(owner=request.user, name=name, position=position, is_default=not current.exists())
            for index, item in enumerate(TEMPLATES[template]):
                definition = definition_for_template(definitions, item)
                if definition is None:
                    continue
                source = sources[item.source_key]
                if item.renderer_key not in source.compatible_renderers:
                    continue
                WidgetInstance.objects.create(
                    dashboard=dashboard, definition_key=definition.key, source_key=source.key, renderer_key=item.renderer_key,
                    config=validated_config(item.config, source, definition, item.renderer_key, context), title=item.title,
                    x=(index % 3) * 4, y=(index // 3) * 3,
                    width=definition.default_size[0], height=definition.default_size[1], logical_order=index,
                )
        return Response(dashboard_data(dashboard), status=status.HTTP_201_CREATED)


class DashboardDetail(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        dashboard = owned(request, pk)
        context = context_for(request, dashboard)
        sources, definitions = available_definitions(context)
        return Response(dashboard_data(dashboard, definitions, sources, context))

    def patch(self, request, pk):
        if not isinstance(request.data, dict) or set(request.data) != {"name"}:
            raise ValidationError("Only name can be changed here.")
        dashboard = owned(request, pk)
        dashboard.name = validated_name(request.data["name"])
        dashboard.save(update_fields=("name", "updated_at"))
        return Response(dashboard_data(dashboard))

    def delete(self, request, pk):
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            dashboard = owned(request, pk)
            if dashboard.scope != "user":
                raise ValidationError({"scope": "Project dashboards cannot be deleted."})
            was_default = dashboard.is_default
            dashboard.delete()
            if was_default:
                successor = Dashboard.objects.filter(owner=request.user, scope="user").first()
                if successor:
                    successor.is_default = True
                    successor.save(update_fields=("is_default", "updated_at"))
        return Response(status=status.HTTP_204_NO_CONTENT)


class DashboardDefault(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            dashboard = owned(request, pk)
            if dashboard.scope != "user":
                raise ValidationError({"scope": "Only personal dashboards have a default."})
            previous = Dashboard.objects.filter(owner=request.user, scope="user", is_default=True).exclude(pk=pk).first()
            if previous:
                previous.is_default = False
                previous.save(update_fields=("is_default", "updated_at"))
            if not dashboard.is_default:
                dashboard.is_default = True
                dashboard.save(update_fields=("is_default", "updated_at"))
        return Response(dashboard_data(dashboard))


class DashboardDuplicate(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            source = owned(request, pk)
            current = Dashboard.objects.filter(owner=request.user, scope="user")
            position = (current.aggregate(Max("position"))["position__max"] or 0) + 1
            if source.scope != "user":
                raise ValidationError({"scope": "Project dashboards cannot be duplicated."})
            copied = Dashboard.objects.create(owner=request.user, name=f"{source.name} (copy)", icon=source.icon, position=position)
            for item in source.widgets.all():
                WidgetInstance.objects.create(
                    dashboard=copied, definition_key=item.definition_key, source_key=item.source_key, renderer_key=item.renderer_key,
                    title=item.title, config=item.config, x=item.x, y=item.y,
                    width=item.width, height=item.height, logical_order=item.logical_order,
                )
        return Response(dashboard_data(copied), status=status.HTTP_201_CREATED)


class DashboardReorder(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def patch(self, request):
        ids = request.data.get("ids") if isinstance(request.data, dict) else None
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            dashboards = list(Dashboard.objects.filter(owner=request.user, scope="user"))
            if not isinstance(ids, list) or any(type(value) is not int for value in ids) or sorted(ids) != sorted(item.pk for item in dashboards):
                raise ValidationError({"ids": "Provide each owned dashboard exactly once."})
            by_id = {item.pk: item for item in dashboards}
            for position, pk in enumerate(ids):
                item = by_id[pk]
                item.position = position
                item.save(update_fields=("position", "updated_at"))
        return Response([dashboard_data(by_id[pk]) for pk in ids])


class DashboardCatalog(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        context = context_for(request)
        sources, definitions = available_definitions(context)
        return Response(catalog_data(context, sources, definitions))


def catalog_data(context, sources, definitions):
    from project.models import Project
    used_source_keys = {item.source_key for item in definitions.values()}
    project_options = list(Project.get_instances_for_user(
        "view", context.user, Project.objects.all()
    ).order_by("name").values("id", "name"))
    return {"scope": context.scope,
                         "project_options": project_options,
                         "sources": [{"key": item.key, "label": item.label, "description": item.description, "category": item.category,
                                      "supported_scopes": item.supported_scopes, "compatible_renderers": item.compatible_renderers,
                                      "default_renderer": item.default_renderer or item.compatible_renderers[0],
                                      "allow_multiple": item.allow_multiple or any(definition.allow_multiple for definition in definitions.values() if definition.source_key == item.key),
                                      "config_fields": item.config_fields}
                                     for item in sources.values() if item.key in used_source_keys],
                         "definitions": [definition_data(item) for item in definitions.values()],
                         "renderers": CORE_RENDERERS}


class ProjectDashboard(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, project_id):
        project = visible_project(request.user, project_id)
        from .template_service import get_or_create_dashboard_for_context
        dashboard = get_or_create_dashboard_for_context(request.user, project, "project", "Project overview")
        context = DashboardContext.for_object(request.user, project)
        sources, definitions = available_definitions(context)
        return Response(dashboard_data(dashboard, definitions, sources, context))


class ProjectDashboardCatalog(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, project_id):
        project = visible_project(request.user, project_id)
        context = DashboardContext.for_object(request.user, project)
        sources, definitions = available_definitions(context)
        return Response(catalog_data(context, sources, definitions))


class DashboardWidgets(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        dashboard = owned(request, pk)
        if not isinstance(request.data, dict) or set(request.data) - {"definition_key", "source_key", "renderer_key", "title", "config"}:
            raise ValidationError("Invalid widget fields.")
        key = request.data.get("definition_key")
        context = context_for(request, dashboard)
        sources, definitions = available_definitions(context)
        source_key = request.data.get("source_key")
        if not key and isinstance(source_key, str):
            definition = next((item for item in definitions.values() if item.source_key == source_key), None)
            key = definition.key if definition else None
        else:
            definition = definitions.get(key)
        if definition is None:
            raise ValidationError({"definition_key": "Widget unavailable."})
        source = sources[definition.source_key]
        if source_key and source_key != source.key:
            raise ValidationError({"source_key": "Source does not match definition."})
        renderer_key = request.data.get("renderer_key", source.default_renderer or definition.renderer_key)
        if renderer_key not in source.compatible_renderers or (renderer_key not in CORE_RENDERERS and renderer_key != definition.renderer_key):
            raise ValidationError({"renderer_key": "Renderer unavailable for this source."})
        title = request.data.get("title", "")
        if not isinstance(title, str) or len(title) > 160:
            raise ValidationError({"title": "Invalid title."})
        config = validated_config(request.data.get("config", {}), source, definition, renderer_key, context)
        with transaction.atomic():
            Dashboard.objects.select_for_update().get(pk=dashboard.pk)
            if not (source.allow_multiple or definition.allow_multiple) and dashboard.widgets.filter(
                    Q(source_key=source.key) | Q(source_key="", definition_key=key)).exists():
                raise ValidationError({"definition_key": "Only one instance is allowed."})
            next_order = (dashboard.widgets.aggregate(Max("logical_order"))["logical_order__max"] or 0) + 1
            next_y = max((item.y + item.height for item in dashboard.widgets.all()), default=0)
            widget = WidgetInstance.objects.create(
                dashboard=dashboard, definition_key=key, source_key=source.key, renderer_key=renderer_key,
                title=title, config=config, x=0, y=next_y,
                width=definition.default_size[0], height=definition.default_size[1], logical_order=next_order,
            )
        return Response(widget_data(widget, definitions, sources, context), status=status.HTTP_201_CREATED)


class DashboardWidgetDetail(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def patch(self, request, pk, widget_id):
        dashboard = owned(request, pk)
        widget = get_object_or_404(dashboard.widgets, pk=widget_id)
        if not isinstance(request.data, dict) or not request.data or set(request.data) - {"title", "config", "renderer_key"}:
            raise ValidationError("Only title, config and renderer can be changed.")
        context = context_for(request, dashboard)
        sources, definitions = available_definitions(context)
        definition = definitions.get(widget.definition_key)
        if definition is None:
            raise ValidationError({"definition_key": "Widget unavailable; remove it if needed."})
        source = sources.get(widget.source_key or definition.source_key)
        if source is None:
            raise ValidationError({"source_key": "Source unavailable."})
        renderer_key = request.data.get("renderer_key", widget.renderer_key)
        if renderer_key not in source.compatible_renderers or (renderer_key not in CORE_RENDERERS and renderer_key != definition.renderer_key):
            raise ValidationError({"renderer_key": "Renderer unavailable for this source."})
        if "title" in request.data:
            title = request.data["title"]
            if not isinstance(title, str) or len(title) > 160:
                raise ValidationError({"title": "Invalid title."})
            widget.title = title
        if "config" in request.data or "renderer_key" in request.data:
            widget.config = validated_config(request.data.get("config", widget.config), source, definition, renderer_key, context)
        widget.source_key = source.key
        widget.renderer_key = renderer_key
        widget.save()
        return Response(widget_data(widget, definitions, sources, context))

    def delete(self, request, pk, widget_id):
        dashboard = owned(request, pk)
        get_object_or_404(dashboard.widgets, pk=widget_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DashboardLayout(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def patch(self, request, pk):
        dashboard = owned(request, pk)
        rows = request.data.get("widgets") if isinstance(request.data, dict) else None
        if not isinstance(rows, list):
            raise ValidationError({"widgets": "Expected a list."})
        _, definitions = available_definitions(context_for(request, dashboard))
        with transaction.atomic():
            Dashboard.objects.select_for_update().get(pk=dashboard.pk)
            widgets = {str(item.pk): item for item in dashboard.widgets.all()}
            seen = set()
            for row in rows:
                if not isinstance(row, dict) or set(row) != {"id", "x", "y", "width", "height", "logical_order"}:
                    raise ValidationError({"widgets": "Invalid layout item."})
                widget_id = row["id"]
                if widget_id not in widgets or widget_id in seen:
                    raise ValidationError({"widgets": "Unknown or duplicate widget."})
                seen.add(widget_id)
                widget = widgets[widget_id]
                definition = definitions.get(widget.definition_key)
                if definition is None:
                    # Missing definitions remain movable/removable within conservative grid bounds.
                    min_size, max_size = (1, 1), (12, 8)
                    definition = type("MissingDefinition", (), {"min_size": min_size, "max_size": max_size})()
                validated_size(definition, row["x"], row["y"], row["width"], row["height"])
                if type(row["logical_order"]) is not int or row["logical_order"] < 0:
                    raise ValidationError({"logical_order": "Non-negative integer required."})
                for field in ("x", "y", "width", "height", "logical_order"):
                    setattr(widget, field, row[field])
                widget.save()
        return Response({"widgets": rows})
