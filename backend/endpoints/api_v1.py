"""Minimal v1 planning dependency and candidate APIs."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from project.models import Project
from project.models import Participant
from project.api_v1 import project_capabilities
from staff.models import Employee

from .models import MilestoneDependency, Milestones
from .planning_serializers_v1 import PlanningMilestoneV1Serializer, PlanningMilestoneWriteV1Serializer
from .planning_v1 import filter_planning_items, planning_serializer_context, preload_planning_items


class ProjectPlanningScopeV1Mixin:
    """Authorize Project first, then scope every Planning operation to it."""

    def get_project(self, request, pk):
        return get_object_or_404(
            Project.get_instances_for_user("view", request.user, Project.objects.all()), pk=pk,
        )

    def can_change(self, request, project):
        return project_capabilities(request.user, project)["can_change"]

    def serialize_item(self, request, project, item):
        scoped = Milestones.objects.filter(project=project)
        loaded = preload_planning_items(scoped.filter(pk=item.pk)).get()
        return PlanningMilestoneV1Serializer(
            loaded, context=planning_serializer_context(request.user, scoped),
        ).data


class ProjectPlanningV1View(ProjectPlanningScopeV1Mixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        project = self.get_project(request, pk)
        scoped = filter_planning_items(Milestones.objects.filter(project=project), request.query_params)
        items = PlanningMilestoneV1Serializer(
            preload_planning_items(scoped), many=True,
            context=planning_serializer_context(request.user, scoped),
        ).data
        participants = Participant.objects.filter(project=project).select_related("employee").order_by(
            "employee__last_name", "employee__first_name", "employee_id",
        )
        unique_participants = {}
        for relation in participants:
            unique_participants[relation.employee_id] = {
                "id": relation.employee_id,
                "first_name": relation.employee.first_name,
                "last_name": relation.employee.last_name,
            }
        can_change = self.can_change(request, project)
        return Response({
            "capabilities": {"can_add": can_change, "can_change": can_change, "can_delete": can_change},
            "participants": list(unique_participants.values()),
            "items": items,
        })

    @transaction.atomic
    def post(self, request, pk):
        project = self.get_project(request, pk)
        if not self.can_change(request, project):
            raise PermissionDenied()
        serializer = PlanningMilestoneWriteV1Serializer(
            data=request.data, context={"project": project},
        )
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        return Response(self.serialize_item(request, project, item), status=201)


class ProjectPlanningItemV1View(ProjectPlanningScopeV1Mixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @transaction.atomic
    def patch(self, request, pk, item_id):
        project = self.get_project(request, pk)
        item = get_object_or_404(Milestones.objects.filter(project=project), pk=item_id)
        if not self.can_change(request, project):
            raise PermissionDenied()
        serializer = PlanningMilestoneWriteV1Serializer(
            item, data=request.data, partial=True, context={"project": project},
        )
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        return Response(self.serialize_item(request, project, item))

    @transaction.atomic
    def delete(self, request, pk, item_id):
        project = self.get_project(request, pk)
        item = get_object_or_404(Milestones.objects.filter(project=project), pk=item_id)
        if not self.can_change(request, project):
            raise PermissionDenied()
        item.delete()
        return Response(status=204)


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


def successor_dependency_dict(dependency):
    return {
        "id": dependency.pk,
        "successor": item_dict(dependency.successor),
        "predecessor_id": dependency.predecessor_id,
        "temporally_inconsistent": dependency.temporally_inconsistent,
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
        successors = MilestoneDependency.objects.filter(
            predecessor=successor, successor__in=readable,
        ).select_related("successor__project", "predecessor").order_by("pk")
        return Response({
            "can_add": successor.project_id in editable_ids,
            "predecessors": [dependency_dict(
                relation,
                can_delete=successor.project_id in editable_ids
                and relation.predecessor.project_id in editable_ids,
            ) for relation in relations],
            "successors": [successor_dependency_dict(relation) for relation in successors],
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
