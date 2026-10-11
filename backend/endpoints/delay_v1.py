"""Preview and apply a Project Planning delay over the existing dependency DAG."""

import hashlib
import json
from collections import defaultdict
from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection, transaction
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .api_v1 import ProjectPlanningScopeV1Mixin, editable_projects, visible_projects
from .models import MilestoneDependency, Milestones


def _ids(value, field, *, required=False):
    if not isinstance(value, list) or (required and not value):
        raise ValidationError({field: "A non-empty list is required." if required else "A list is required."})
    if any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in value):
        raise ValidationError({field: "Positive integer IDs are required."})
    if len(value) != len(set(value)):
        raise ValidationError({field: "Duplicate IDs are not allowed."})
    return value


def _intent(data):
    if not isinstance(data, dict):
        raise ValidationError({"detail": "An object is required."})
    roots = _ids(data.get("root_ids"), "root_ids", required=True)
    cuts = _ids(data.get("blocked_dependency_ids", []), "blocked_dependency_ids")
    days = data.get("days")
    if isinstance(days, bool) or not isinstance(days, int) or days <= 0:
        raise ValidationError({"days": "Enter a positive whole number of days."})
    return roots, cuts, days


def _graph(root_ids, *, lock=False):
    """Read the true graph, including cross-Project paths; never use a filtered UI list."""
    seen = set(root_ids)
    frontier = set(root_ids)
    relations = {}
    while frontier:
        rows = MilestoneDependency.objects.filter(predecessor_id__in=frontier).values_list(
            "pk", "predecessor_id", "successor_id"
        )
        next_frontier = set()
        for edge_id, parent_id, child_id in rows:
            relations[edge_id] = (parent_id, child_id)
            if child_id not in seen:
                seen.add(child_id)
                next_frontier.add(child_id)
        frontier = next_frontier
    queryset = Milestones.objects.filter(pk__in=seen).select_related("project").order_by("pk")
    if lock:
        queryset = queryset.select_for_update()
    return {item.pk: item for item in queryset}, relations


def _preview(user, project, data, *, lock=False):
    roots, cuts, days = _intent(data)
    root_items = {item.pk: item for item in Milestones.objects.filter(pk__in=roots, project=project)}
    if len(root_items) != len(roots):
        raise ValidationError({"root_ids": "A selected item no longer belongs to this Project."})
    items, relations = _graph(roots, lock=lock)
    if any(item_id not in items for item_id in roots):
        raise ValidationError({"root_ids": "A selected item no longer exists."})
    if any(edge_id not in relations for edge_id in cuts):
        raise ValidationError({"blocked_dependency_ids": "A selected dependency has changed. Reload the preview."})

    project_ids = {item.project_id for item in items.values()}
    visible = set(visible_projects(user).filter(pk__in=project_ids).values_list("pk", flat=True))
    editable = set(editable_projects(user).filter(pk__in=project_ids).values_list("pk", flat=True))
    def unavailable(item):
        if item.project_id not in visible:
            return "hidden"
        if item.project_id not in editable:
            return "read_only"
        if item.status:
            return "completed"
        if item.end_date is None:
            return "no_end_date"
        return None

    root_errors = {item_id: unavailable(root_items[item_id]) for item_id in roots if unavailable(root_items[item_id])}
    if root_errors:
        raise ValidationError({"root_ids": "Selected items must be editable, unfinished and have an end date."})

    successors = defaultdict(list)
    for edge_id, (parent_id, child_id) in relations.items():
        successors[parent_id].append((edge_id, child_id))
    affected = set(roots)
    pending = list(roots)
    blocked = set(cuts)
    while pending:
        parent_id = pending.pop()
        for edge_id, child_id in successors[parent_id]:
            child = items.get(child_id)
            if edge_id in blocked or child_id in affected or child is None or unavailable(child):
                continue
            affected.add(child_id)
            pending.append(child_id)

    public = {item_id: item for item_id, item in items.items() if item.project_id in visible}
    exposed_edges = [
        {"id": edge_id, "predecessor_id": parent_id, "successor_id": child_id}
        for edge_id, (parent_id, child_id) in sorted(relations.items())
        if parent_id in public and child_id in public
    ]
    nodes = [{
        "id": item_id, "name": item.name, "project": {"id": item.project_id, "name": item.project.name},
        "work_kind": "task" if item.start_date else "milestone",
        "end_date": item.end_date.isoformat() if item.end_date else None,
        "eligible": unavailable(item) is None,
        "unavailable_reason": unavailable(item),
        "affected": item_id in affected,
    } for item_id, item in sorted(public.items())]
    affected_rows = []
    for item_id in sorted(affected):
        item = items[item_id]
        try:
            new_date = item.end_date + timedelta(days=days)
        except OverflowError as error:
            raise ValidationError({"days": "The resulting date is out of range."}) from error
        affected_rows.append({"id": item_id, "old_end_date": item.end_date.isoformat(), "new_end_date": new_date.isoformat()})

    snapshot = {
        "roots": roots, "cuts": sorted(cuts), "days": days,
        "affected": sorted(affected), "visible": sorted(visible), "editable": sorted(editable),
        "nodes": [(item.pk, item.project_id, item.start_date.isoformat() if item.start_date else None,
                   item.end_date.isoformat() if item.end_date else None, item.status)
                  for item in items.values()],
        "edges": sorted((edge_id, *pair) for edge_id, pair in relations.items()),
    }
    revision = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    return {
        "root_ids": roots, "blocked_dependency_ids": cuts, "days": days,
        "nodes": nodes, "edges": exposed_edges, "affected": affected_rows,
        "excluded_ids": [item_id for item_id in public if item_id not in affected],
        "revision": revision,
    }, items


class ProjectPlanningDelayV1View(ProjectPlanningScopeV1Mixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk, action):
        project = self.get_project(request, pk)
        if not self.can_change(request, project):
            raise PermissionDenied()
        if action == "preview":
            preview, _ = _preview(request.user, project, request.data)
            return Response(preview)
        if action != "apply":
            raise ValidationError({"action": "Unknown delay action."})
        with transaction.atomic():
            if connection.vendor == "postgresql":
                # Share the lock used by dependency writes to stabilize traversal.
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_xact_lock(%s)", [291009])
            preview, items = _preview(request.user, project, request.data, lock=True)
            if request.data.get("revision") != preview["revision"]:
                return Response({"detail": "Planning changed. Reload the delay preview."}, status=409)
            for row in preview["affected"]:
                item = items[row["id"]]
                item.end_date = item.end_date + timedelta(days=preview["days"])
                try:
                    item.full_clean()
                except DjangoValidationError as error:
                    raise ValidationError(getattr(error, "message_dict", None) or error.messages) from error
                item.save()
            return Response({"affected_ids": [row["id"] for row in preview["affected"]]})
