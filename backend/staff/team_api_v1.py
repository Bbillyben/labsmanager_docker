"""Team v1: object-scoped composition and contextual read-only collections."""

from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import filters, generics, permissions, serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from common.calendar import CalendarContext, CalendarService, CalendarType
from fund.budget_api_v1 import budget_data
from labsmanager.admin_links_v1 import get_admin_change_url
from fund.models import Budget, Fund
from labsmanager.list_export_v1 import ListExportContentNegotiation, export_list_queryset
from labsmanager.pagination import LabPagination
from leave.calendar import produce_leave_calendar_events
from leave.models import Leave
from project.models import Participant, Project
from staff.permissions_v1 import leave_capabilities
from staff.ressources import TeamResource
from staff.serializers_v1 import EmployeeLeaveV1Serializer, EmployeeLeaveWriteV1Serializer

from .models import Employee, Team, TeamMate


def visible_teams(user, queryset=None):
    """SQL equivalent of the existing view_team leader/member predicate."""
    queryset = queryset if queryset is not None else Team.objects.all()
    if user.has_perm("staff.view_team"):
        return queryset
    member_teams = TeamMate.objects.filter(employee__user=user).values("team_id")
    return queryset.filter(Q(leader__user=user) | Q(pk__in=member_teams))


def can_change_team(user, team):
    return bool(user.has_perm("staff.change_team") or user.has_perm("staff.change_team", team))


def team_create_capabilities(user):
    own = Employee.objects.filter(user=user).first()
    can_choose_leader = user.has_perm("staff.change_team")
    return {
        "can_add": bool(user.has_perm("staff.add_team") and (can_choose_leader or own)),
        "can_choose_leader": can_choose_leader,
        "default_leader": {"id": own.pk, "name": str(own)} if own else None,
    }


def validated_employee(value, field="employee_id", active=False):
    try:
        employee = Employee.objects.get(pk=value)
    except (Employee.DoesNotExist, ValueError, TypeError):
        raise ValidationError({field: "Unknown Employee."})
    if active and not employee.is_active:
        raise ValidationError({field: "Employee must be active."})
    return employee


def validated_date(value, field):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError({field: "Expected an ISO date."})


def validate_model(instance):
    if isinstance(instance, TeamMate) and instance.start_date and instance.end_date and instance.end_date < instance.start_date:
        raise ValidationError({"end_date": "Must be on or after start_date."})
    try:
        instance.full_clean()
    except DjangoValidationError as error:
        raise ValidationError(getattr(error, "message_dict", None) or error.messages) from error


def team_members(team):
    return Employee.objects.filter(
        Q(pk=team.leader_id) | Q(pk__in=TeamMate.objects.filter(team=team).values("employee_id"))
    ).distinct()


def employee_data(employee, visible_ids):
    return {
        "id": employee.pk, "name": str(employee),
        "can_view": employee.pk in visible_ids,
    }


def team_queryset(user):
    return visible_teams(user, Team.objects.select_related("leader").prefetch_related(
        Prefetch("teammate_set", queryset=TeamMate.objects.select_related("employee").order_by(
            "employee__last_name", "employee__first_name", "pk"
        ), to_attr="loaded_mates")
    ))


def team_data(team, user, visible_ids, can_view=True):
    can_change = can_change_team(user, team)
    return {
        "id": team.pk, "admin_url": get_admin_change_url(user, team), "name": team.name,
        "leader": employee_data(team.leader, visible_ids),
        "mates": [
            {"id": relation.pk, "admin_url": get_admin_change_url(user, relation), "employee": employee_data(relation.employee, visible_ids),
             "start_date": relation.start_date, "end_date": relation.end_date,
             "is_active": relation.is_active,
             "capabilities": {"can_change": can_change, "can_delete": can_change}}
            for relation in team.loaded_mates
        ],
        "capabilities": {"can_view": can_view, "can_change": can_change,
                         "can_manage_composition": can_change},
    }


def visible_employee_ids(user, teams):
    employee_ids = {team.leader_id for team in teams}
    employee_ids.update(mate.employee_id for team in teams for mate in team.loaded_mates)
    return set(Employee.get_instances_for_user("view", user, Employee.objects.filter(
        pk__in=employee_ids
    )).values_list("pk", flat=True))


class TeamListV1View(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = LabPagination
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("name", "leader__last_name", "leader__first_name")
    ordering = ("name", "pk")

    def get_queryset(self):
        query = team_queryset(self.request.user)
        params = self.request.query_params
        if params.get("name"):
            query = query.filter(name__icontains=params["name"])
        for field in ("leader", "mate"):
            if params.get(field) and (not params[field].isdecimal() or int(params[field]) <= 0):
                raise ValidationError({field: "Expected a positive Employee id."})
        if params.get("leader"):
            query = query.filter(leader_id=int(params["leader"]))
        if params.get("mate"):
            query = query.filter(pk__in=TeamMate.objects.filter(
                employee_id=int(params["mate"])
            ).values("team_id"))
        return query

    def list(self, request, *args, **kwargs):
        query = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(query)
        teams = list(page if page is not None else query)
        visible_ids = visible_employee_ids(request.user, teams)
        result = [team_data(team, request.user, visible_ids) for team in teams]
        response = self.get_paginated_response(result) if page is not None else Response({"results": result})
        response.data["capabilities"] = team_create_capabilities(request.user)
        return response

    def post(self, request, *args, **kwargs):
        capability = team_create_capabilities(request.user)
        if not capability["can_add"]:
            raise PermissionDenied()
        if set(request.data) != {"name", "leader_id"}:
            raise ValidationError({"name": "Expected name and leader_id only."})
        leader = validated_employee(request.data["leader_id"], "leader_id", active=capability["can_choose_leader"])
        if not capability["can_choose_leader"] and leader.pk != capability["default_leader"]["id"]:
            raise PermissionDenied()
        team = Team(name=request.data["name"], leader=leader)
        validate_model(team)
        team.save()
        team.loaded_mates = []
        return Response(team_data(team, request.user, visible_employee_ids(request.user, [team])), status=201)


class TeamListExportV1View(TeamListV1View):
    http_method_names = ("get", "head", "options")
    content_negotiation_class = ListExportContentNegotiation

    def get(self, request, *args, **kwargs):
        query = self.filter_queryset(self.get_queryset())
        return export_list_queryset(request, query, TeamResource, "Team")


class TeamBaseV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def team(self):
        return get_object_or_404(team_queryset(self.request.user), pk=self.kwargs["team_id"])

    def require_change(self, team):
        if not can_change_team(self.request.user, team):
            raise PermissionDenied()


class TeamDetailV1View(TeamBaseV1View):
    def get(self, request, *args, **kwargs):
        team = self.team()
        return Response(team_data(team, request.user, visible_employee_ids(request.user, [team])))

    def patch(self, request, *args, **kwargs):
        team = self.team()
        self.require_change(team)
        if not request.data or set(request.data) - {"name", "leader_id"}:
            raise ValidationError({"name": "Expected name and/or leader_id."})
        fields = []
        if "leader_id" in request.data:
            employee = validated_employee(request.data["leader_id"], "leader_id", active=True)
            if TeamMate.objects.filter(team=team, employee=employee).exists():
                raise ValidationError({"leader_id": "Remove this Employee from TeamMate first."})
            team.leader = employee
            fields.append("leader")
        if "name" in request.data:
            team.name = request.data["name"]
            fields.append("name")
        validate_model(team)
        team.save(update_fields=fields)
        # The previous leader may lose object visibility as a result of this write.
        team = Team.objects.select_related("leader").prefetch_related(
            Prefetch("teammate_set", queryset=TeamMate.objects.select_related("employee"), to_attr="loaded_mates")
        ).get(pk=team.pk)
        return Response(team_data(
            team, request.user, visible_employee_ids(request.user, [team]),
            can_view=visible_teams(request.user, Team.objects.filter(pk=team.pk)).exists(),
        ))


class TeamMateCollectionV1View(TeamBaseV1View):
    def post(self, request, *args, **kwargs):
        team = self.team()
        self.require_change(team)
        if "employee_id" not in request.data or set(request.data) - {"employee_id", "start_date", "end_date"}:
            raise ValidationError({"employee_id": "Expected employee_id and optional dates."})
        employee = validated_employee(request.data["employee_id"], active=True)
        relation = TeamMate(team=team, employee=employee,
                            start_date=validated_date(request.data.get("start_date"), "start_date"),
                            end_date=validated_date(request.data.get("end_date"), "end_date"))
        validate_model(relation)
        relation.save()
        return Response({"id": relation.pk}, status=201)


class TeamMateDetailV1View(TeamBaseV1View):
    def patch(self, request, *args, **kwargs):
        team = self.team()
        self.require_change(team)
        relation = get_object_or_404(TeamMate, team=team, pk=self.kwargs["mate_id"])
        if not request.data or set(request.data) - {"employee_id", "start_date", "end_date"}:
            raise ValidationError({"employee_id": "Expected employee_id and/or dates."})
        fields = []
        if "employee_id" in request.data:
            relation.employee = validated_employee(request.data["employee_id"], active=True)
            fields.append("employee")
        for field in ("start_date", "end_date"):
            if field in request.data:
                setattr(relation, field, validated_date(request.data[field], field))
                fields.append(field)
        validate_model(relation)
        relation.save(update_fields=fields)
        return Response({"id": relation.pk, "employee_id": relation.employee_id,
                         "start_date": relation.start_date, "end_date": relation.end_date,
                         "is_active": relation.is_active})

    def delete(self, request, *args, **kwargs):
        team = self.team()
        self.require_change(team)
        get_object_or_404(TeamMate, team=team, pk=self.kwargs["mate_id"]).delete()
        return Response(status=204)


def led_projects(team, user):
    member_ids = team_members(team).values("pk")
    relevant = Participant.objects.filter(employee_id__in=member_ids, status__in=("l", "cl")).values("project_id")
    visible = Project.get_instances_for_user("view", user, Project.objects.filter(pk__in=relevant))
    return visible.distinct()


class TeamProjectsV1View(TeamBaseV1View):
    def get(self, request, *args, **kwargs):
        projects = led_projects(self.team(), request.user).order_by("name", "pk")
        return Response([
            {"id": item.pk, "name": item.name, "start_date": item.start_date,
             "end_date": item.end_date, "status": item.status}
            for item in projects
        ])


class TeamBudgetsV1View(TeamBaseV1View):
    def get(self, request, *args, **kwargs):
        project_ids = led_projects(self.team(), request.user).values("pk")
        visible_funds = Fund.get_instances_for_user("view", request.user, Fund.objects.filter(project_id__in=project_ids))
        visible = Budget.get_instances_for_user("view", request.user, Budget.objects.filter(fund__in=visible_funds))
        items = visible.select_related("fund__project", "fund__funder", "fund__institution", "cost_type", "emp_type", "employee").prefetch_related("contract_type").order_by("fund__project__name", "fund_id", "pk")
        return Response([
            {**budget_data(item, request.user, item.fund.project, "budget"),
             "capabilities": {"can_add": False, "can_change": False, "can_delete": False},
             "project": {"id": item.fund.project_id, "name": item.fund.project.name}}
            for item in items
        ])


class TeamCalendarBaseV1View(TeamBaseV1View):
    def context(self, bounded=False):
        team = self.team()
        start = end = None
        if bounded:
            try:
                start = date.fromisoformat(self.request.query_params.get("from", ""))
                end = date.fromisoformat(self.request.query_params.get("to", ""))
            except ValueError as error:
                raise ValidationError({"from": "Expected ISO from and to dates."}) from error
            if start > end:
                raise ValidationError({"to": "Must be on or after from."})
        return CalendarContext(calendar_type=CalendarType.TEAM, team_id=team.pk,
                               user=self.request.user, start=start, end=end,
                               filters=self.request.query_params)


class TeamCalendarV1View(TeamCalendarBaseV1View):
    def get(self, request, *args, **kwargs):
        context = self.context(bounded=True)
        service = CalendarService()
        return Response([event.as_dict() for event in service.get_events(
            context, produce_leave_calendar_events(context, service)
        )])


class TeamCalendarFiltersV1View(TeamCalendarBaseV1View):
    def get(self, request, *args, **kwargs):
        return Response([item.as_dict() for item in CalendarService().get_filters(self.context())])


class TeamCalendarParticipantsV1View(TeamCalendarBaseV1View):
    def get(self, request, *args, **kwargs):
        employees = team_members(self.team()).order_by("last_name", "first_name", "pk")
        return Response([{"id": employee.pk, "title": str(employee),
                          "capabilities": leave_capabilities(request.user, employee)}
                         for employee in employees])


class TeamCalendarLeaveCreateV1View(TeamCalendarBaseV1View):
    def post(self, request, *args, **kwargs):
        team = self.team()
        try:
            employee_id = int(request.data.get("employee_id"))
        except (TypeError, ValueError) as error:
            raise ValidationError({"employee_id": "Expected a Team Employee id."}) from error
        employee = get_object_or_404(team_members(team), pk=employee_id)
        if not leave_capabilities(request.user, employee)["can_add"]:
            raise PermissionDenied()
        data = {key: value for key, value in request.data.items() if key != "employee_id"}
        serializer = EmployeeLeaveWriteV1Serializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(EmployeeLeaveV1Serializer(serializer.save(employee=employee), context={"request": request}).data, status=201)


class TeamCalendarLeaveDetailV1View(TeamCalendarBaseV1View):
    def leave(self):
        return get_object_or_404(
            Leave.objects.select_related("employee", "type").filter(employee__in=team_members(self.team())),
            pk=self.kwargs["leave_id"],
        )

    def patch(self, request, *args, **kwargs):
        leave = self.leave()
        if not leave_capabilities(request.user, leave.employee)["can_change"]:
            raise PermissionDenied()
        serializer = EmployeeLeaveWriteV1Serializer(leave, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(EmployeeLeaveV1Serializer(serializer.save(), context={"request": request}).data)

    def delete(self, request, *args, **kwargs):
        leave = self.leave()
        if not leave_capabilities(request.user, leave.employee)["can_delete"]:
            raise PermissionDenied()
        leave.delete()
        return Response(status=204)
