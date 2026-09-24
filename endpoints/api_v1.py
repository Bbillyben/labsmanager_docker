"""Minimal v1 planning dependency and candidate APIs."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from project.models import Project
from staff.models import Employee

from .models import MilestoneDependency, Milestones


def editable_projects(user):
    return Project.get_instances_for_user("change", user, Project.objects.all()).distinct()


def visible_projects(user):
    viewed = Project.get_instances_for_user("view", user, Project.objects.all())
    return Project.objects.filter(
        Q(pk__in=viewed.values("pk")) | Q(pk__in=editable_projects(user).values("pk"))
    )


def readable_items(user):
    """Match Project visibility and the existing contextual Employee milestone list."""
    employees = Employee.get_instances_for_user("view", user, Employee.objects.all())
    return Milestones.objects.filter(
        Q(project__in=visible_projects(user)) | Q(employee__in=employees)
    ).distinct()


def item_dict(item):
    return {
        "id": item.pk,
        "name": item.name,
        "work_kind": "milestone" if item.is_milestone else "task",
        "start_date": item.start_date,
        "end_date": item.end_date,
        "project": {"id": item.project_id, "name": item.project.name},
    }


def dependency_dict(dependency, *, can_delete):
    return {
        "id": dependency.pk,
        "predecessor": item_dict(dependency.predecessor),
        "successor_id": dependency.successor_id,
        "temporally_inconsistent": dependency.temporally_inconsistent,
        "can_delete": can_delete,
    }


class EditableProjectCandidatesV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        projects = editable_projects(request.user)
        search = request.query_params.get("search", "").strip()
        if search:
            projects = projects.filter(name__icontains=search)
        preferred = request.query_params.get("preferred")
        if preferred and preferred.isdecimal():
            projects = projects.annotate(
                preferred_order=Case(
                    When(pk=int(preferred), then=Value(0)),
                    default=Value(1), output_field=IntegerField(),
                )
            ).order_by("preferred_order", "name", "pk")
        else:
            projects = projects.order_by("name", "pk")
        return Response([{"id": item.pk, "name": item.name} for item in projects[:30]])


class ProjectPlanningItemsV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, project_id):
        project = get_object_or_404(editable_projects(request.user), pk=project_id)
        items = Milestones.objects.filter(project=project).select_related("project")
        search = request.query_params.get("search", "").strip()
        if search:
            items = items.filter(name__icontains=search)
        exclude = request.query_params.get("exclude")
        if exclude and exclude.isdecimal():
            items = items.exclude(pk=int(exclude))
        return Response([item_dict(item) for item in items.order_by("name", "pk")[:30]])


class MilestoneDependenciesV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, successor_id):
        readable = readable_items(request.user)
        successor = get_object_or_404(
            readable.select_related("project"), pk=successor_id,
        )
        editable_ids = set(editable_projects(request.user).values_list("pk", flat=True))
        relations = MilestoneDependency.objects.filter(
            successor=successor, predecessor__in=readable
        ).select_related("predecessor__project", "successor").order_by("pk")
        return Response({
            "can_add": successor.project_id in editable_ids,
            "predecessors": [dependency_dict(
                relation,
                can_delete=successor.project_id in editable_ids
                and relation.predecessor.project_id in editable_ids,
            ) for relation in relations],
        })

    def post(self, request, successor_id):
        successor = get_object_or_404(
            Milestones.objects.select_related("project"), pk=successor_id
        )
        editable_ids = set(editable_projects(request.user).values_list("pk", flat=True))
        if successor.project_id not in editable_ids:
            raise PermissionDenied("Change permission is required on the successor Project.")
        raw_id = request.data.get("predecessor_id")
        try:
            predecessor_id = int(raw_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError({"predecessor_id": "Expected a planning item id."}) from exc
        predecessor = get_object_or_404(
            Milestones.objects.select_related("project"), pk=predecessor_id
        )
        if predecessor.project_id not in editable_ids:
            raise PermissionDenied("Change permission is required on the predecessor Project.")
        relation = MilestoneDependency(predecessor=predecessor, successor=successor)
        try:
            relation.save()
        except DjangoValidationError as exc:
            payload = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            errors = getattr(exc, "error_dict", {})
            if "predecessor" in errors:
                payload["code"] = errors["predecessor"][0].code
            raise ValidationError(payload) from exc
        return Response(dependency_dict(relation, can_delete=True), status=201)


class MilestoneDependencyDetailV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def delete(self, request, successor_id, dependency_id):
        relation = get_object_or_404(
            MilestoneDependency.objects.select_related("predecessor__project", "successor__project"),
            pk=dependency_id, successor_id=successor_id,
        )
        editable_ids = set(editable_projects(request.user).values_list("pk", flat=True))
        if (relation.predecessor.project_id not in editable_ids
                or relation.successor.project_id not in editable_ids):
            raise PermissionDenied("Change permission is required on both Projects.")
        relation.delete()
        return Response(status=204)
