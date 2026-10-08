from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Case, DateField, F, IntegerField, Prefetch, Q, Value, When
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from labsmanager.pagination import LabPagination
from labsmanager.list_export_v1 import ListExportContentNegotiation, export_list_queryset
from endpoints.models import Milestones
from endpoints.planning_serializers_v1 import EmployeePlanningMilestoneV1Serializer, EmployeeMilestonePartialWriteV1Serializer
from endpoints.planning_v1 import filter_planning_items, planning_serializer_context, preload_planning_items
from expense.models import Contract, Contract_expense
from fund.models import Budget, Contribution, Cost_Type
from leave.calendar import produce_leave_calendar_events
from leave.models import Leave, Leave_Type
from project.models import Participant, Project

from .permissions_v1 import employee_detail_capabilities, generic_info_capabilities, leave_capabilities
from .ressources import EmployeeResource
from .filters_v1 import EmployeeListV1Filter
from .models import Employee, Employee_Status, Employee_Superior, Employee_Type, GenericInfo, GenericInfoType, Team, TeamMate
from .serializers_v1 import (
    EmployeeDetailV1Serializer,
    EmployeeDetailWriteV1Serializer,
    EmployeeContractDetailV1Serializer,
    EmployeeContractV1Serializer,
    EmployeeBudgetV1Serializer,
    EmployeeContributionV1Serializer,
    EmployeeGenericInfoV1Serializer,
    GenericInfoTypeV1Serializer,
    GenericInfoWriteV1Serializer,
    EmployeeHierarchyV1Serializer,
    EmployeeLeaveV1Serializer,
    EmployeeLeaveWriteV1Serializer,
    EmployeeListV1Serializer,
    EmployeeStatusHistoryV1Serializer,
    ProjectParticipationV1Serializer,
)

from common.calendar import CalendarContext, CalendarService, CalendarType


class EmployeeContractV1Mixin:
    """Resolve Employee first, then expose its contextual Contracts."""

    def get_employee(self):
        if not hasattr(self, "_v1_employee"):
            visible_employees = Employee.get_instances_for_user(
                "view", self.request.user, Employee.objects.all()
            )
            self._v1_employee = get_object_or_404(
                visible_employees, pk=self.kwargs["pk"]
            )
        return self._v1_employee

    def get_contract_queryset(self):
        employee = self.get_employee()
        return Contract.objects.filter(employee=employee).select_related(
            "employee",
            "contract_type",
            "fund__project",
            "fund__funder",
            "fund__institution",
        )

    def get_contract_context(self):
        visible_project_ids = set(
            Project.get_instances_for_user(
                "view", self.request.user, Project.objects.all()
            ).values_list("pk", flat=True)
        )
        return {
            "request": self.request,
            "today": timezone.localdate(),
            "visible_project_ids": visible_project_ids,
            "can_view_organizations": self.request.user.has_perm(
                "common.display_infos"
            ),
        }


class EmployeeContractListV1View(EmployeeContractV1Mixin, generics.ListAPIView):
    """List scoped Contracts for one visible Employee in temporal groups."""

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EmployeeContractV1Serializer
    pagination_class = None

    def get_queryset(self):
        today = timezone.localdate()
        future = Q(start_date__gt=today)
        past = ~future & Q(end_date__lt=today)
        return self.get_contract_queryset().annotate(
            _v1_temporal_order=Case(
                When(future, then=Value(1)),
                When(past, then=Value(2)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            _v1_current_end=Case(
                When(future | past, then=Value(None)),
                default=F("end_date"),
                output_field=DateField(),
            ),
            _v1_future_start=Case(
                When(future, then=F("start_date")),
                default=Value(None),
                output_field=DateField(),
            ),
            _v1_past_end=Case(
                When(past, then=F("end_date")),
                default=Value(None),
                output_field=DateField(),
            ),
        ).order_by(
            "_v1_temporal_order",
            F("_v1_current_end").asc(nulls_last=True),
            F("_v1_future_start").asc(nulls_last=True),
            F("_v1_past_end").desc(nulls_last=True),
            "pk",
        )

    def get_serializer_context(self):
        return self.get_contract_context()


class EmployeeContractDetailV1View(EmployeeContractV1Mixin, generics.RetrieveAPIView):
    """Return one scoped Contract and its expenses on demand."""

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EmployeeContractDetailV1Serializer
    lookup_url_kwarg = "contract_pk"

    def get_queryset(self):
        return self.get_contract_queryset()

    def get_object(self):
        if not hasattr(self, "_v1_contract"):
            self._v1_contract = super().get_object()
        return self._v1_contract

    def get_serializer_context(self):
        context = self.get_contract_context()
        contract = self.get_object()
        context["contract_expenses"] = list(
            Contract_expense.objects.filter(contract=contract)
            .select_related("type")
            .order_by(F("date").desc(), F("pk").desc())
        )
        return context


class EmployeeContributionListV1View(generics.ListAPIView):
    """List every Contribution attached to one visible Employee."""

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EmployeeContributionV1Serializer
    pagination_class = None

    def get_queryset(self):
        visible_employees = Employee.get_instances_for_user(
            "view", self.request.user, Employee.objects.all()
        )
        employee = get_object_or_404(visible_employees, pk=self.kwargs["pk"])
        today = timezone.localdate()
        future = Q(start_date__gt=today)
        past = ~future & Q(end_date__lt=today)
        return (
            Contribution.objects.filter(employee=employee)
            .select_related("fund__project", "cost_type", "emp_type")
            .prefetch_related("contract_type")
            .annotate(
                _v1_temporal_order=Case(
                    When(future, then=Value(1)),
                    When(past, then=Value(2)),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
                _v1_current_end=Case(
                    When(future | past, then=Value(None)),
                    default=F("end_date"),
                    output_field=DateField(),
                ),
                _v1_future_start=Case(
                    When(future, then=F("start_date")),
                    default=Value(None),
                    output_field=DateField(),
                ),
                _v1_past_end=Case(
                    When(past, then=F("end_date")),
                    default=Value(None),
                    output_field=DateField(),
                ),
            )
            .order_by(
                "_v1_temporal_order",
                F("_v1_current_end").asc(nulls_last=True),
                F("_v1_future_start").asc(nulls_last=True),
                F("_v1_past_end").desc(nulls_last=True),
                "pk",
            )
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(
            today=timezone.localdate(),
            hr_cost_type_ids=set(
                Cost_Type.objects.filter(is_hr=True)
                .get_descendants(include_self=True)
                .values_list("pk", flat=True)
            ),
        )
        return context


class EmployeeBudgetListV1View(generics.ListAPIView):
    """List Budget items explicitly attached to one visible Employee."""

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EmployeeBudgetV1Serializer
    pagination_class = None

    def get_queryset(self):
        visible_employees = Employee.get_instances_for_user(
            "view", self.request.user, Employee.objects.all()
        )
        employee = get_object_or_404(visible_employees, pk=self.kwargs["pk"])
        return (
            Budget.objects.filter(employee=employee)
            .select_related(
                "fund__project",
                "fund__funder",
                "fund__institution",
                "cost_type",
                "emp_type",
            )
            .prefetch_related("contract_type")
            .order_by("fund__project__name", "cost_type__name", "pk")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["hr_cost_type_ids"] = set(
            Cost_Type.objects.filter(is_hr=True)
            .get_descendants(include_self=True)
            .values_list("pk", flat=True)
        )
        return context


def _v1_date_parameter(request, name, required=False):
    """Parse an ISO date query parameter with a stable validation error."""
    raw = request.query_params.get(name)
    if not raw:
        if required:
            raise ValidationError({name: "This query parameter is required."})
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError({name: "Expected an ISO date (YYYY-MM-DD)."}) from exc


class EmployeeLeaveQuerysetMixin:
    """Resolve Employee scope before loading its contextual Leave objects."""

    def get_employee(self):
        visible_employees = Employee.get_instances_for_user(
                "view", self.request.user, Employee.objects.all()
            )
        print(f' ###########  EmployeeLeaveQuerysetMixin -> get_employee / visible_employees :{visible_employees}')
        return get_object_or_404(visible_employees, pk=self.kwargs["pk"])

    def get_leave_queryset(self, *, require_bounds=False):
        employee = self.get_employee()
        start = _v1_date_parameter(self.request, "from", required=require_bounds)
        end = _v1_date_parameter(self.request, "to", required=require_bounds)
        if start and end and start > end:
            raise ValidationError({"to": "Must be on or after from."})

        queryset = Leave.objects.filter(employee=employee).select_related("type")
        if start:
            queryset = queryset.filter(end_date__gte=start)
        if end:
            queryset = queryset.filter(start_date__lte=end)

        leave_type = self.request.query_params.get("type")
        if leave_type:
            try:
                queryset = queryset.filter(type_id=int(leave_type))
            except ValueError as exc:
                raise ValidationError({"type": "Expected a Leave type id."}) from exc
        return queryset.order_by("start_date", "start_period", "end_date", "pk"), start, end


class EmployeeLeaveListV1View(EmployeeLeaveQuerysetMixin, generics.ListAPIView):
    """List Leave records belonging to one authorized Employee."""

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EmployeeLeaveV1Serializer
    pagination_class = None

    def get_queryset(self):
        queryset, _start, _end = self.get_leave_queryset()
        return queryset

    def post(self, request, *args, **kwargs):
        employee = self.get_employee()
        if not leave_capabilities(request.user, employee)["can_add"]:
            raise PermissionDenied()
        serializer = EmployeeLeaveWriteV1Serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave = serializer.save(employee=employee)
        return Response(EmployeeLeaveV1Serializer(leave, context={"request": request}).data, status=201)


class EmployeeLeaveCapabilitiesV1View(EmployeeLeaveQuerysetMixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        return Response(leave_capabilities(request.user, self.get_employee()))


class EmployeeLeaveDetailV1View(EmployeeLeaveQuerysetMixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_leave(self):
        return get_object_or_404(
            Leave.objects.select_related("type").filter(employee=self.get_employee()),
            pk=self.kwargs["leave_id"],
        )

    def patch(self, request, *args, **kwargs):
        leave = self.get_leave()
        if not leave_capabilities(request.user, leave.employee)["can_change"]:
            raise PermissionDenied()
        serializer = EmployeeLeaveWriteV1Serializer(leave, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(EmployeeLeaveV1Serializer(serializer.save(), context={"request": request}).data)

    def delete(self, request, *args, **kwargs):
        leave = self.get_leave()
        if not leave_capabilities(request.user, leave.employee)["can_delete"]:
            raise PermissionDenied()
        leave.delete()
        return Response(status=204)


class LeaveTypeCatalogueV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response([{
            "id": leave_type.pk,
            "name": leave_type.name,
            "short_name": leave_type.short_name,
            "color": str(leave_type.color),
            "parent_id": leave_type.parent_id,
            "depth": leave_type.level,
        } for leave_type in Leave_Type.objects.order_by("tree_id", "lft")])


class EmployeeCalendarV1View(EmployeeLeaveQuerysetMixin, APIView):
    """Aggregate bounded Employee Leave and plugin calendar events."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        gantt = request.query_params.get("context") == CalendarType.EMPLOYEE_GANTT.value
        if gantt:
            employee = self.get_employee()
            start = _v1_date_parameter(request, "from", required=True)
            end = _v1_date_parameter(request, "to", required=True)
            if start > end:
                raise ValidationError({"to": "Must be on or after from."})
        else:
            self.get_employee()
            start = _v1_date_parameter(request, "from", required=True)
            end = _v1_date_parameter(request, "to", required=True)
            if start > end:
                raise ValidationError({"to": "Must be on or after from."})
        context = CalendarContext(
            calendar_type=CalendarType.EMPLOYEE_GANTT if gantt else CalendarType.EMPLOYEE,
            user=request.user,
            start=start,
            end=end,
            employee_id=employee.pk if gantt else self.kwargs["pk"],
            filters=request.query_params,
        )
        service = CalendarService()
        core_events = [] if gantt else produce_leave_calendar_events(context, service)
        events = service.get_events(context, core_events)
        return Response([event.as_dict() for event in events])


class EmployeeCalendarFilterV1View(EmployeeLeaveQuerysetMixin, APIView):
    """Expose plugin filters applicable to one authorized Employee calendar."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        employee = self.get_employee()
        gantt = request.query_params.get("context") == CalendarType.EMPLOYEE_GANTT.value
        context = CalendarContext(
            calendar_type=CalendarType.EMPLOYEE_GANTT if gantt else CalendarType.EMPLOYEE,
            user=request.user,
            employee_id=employee.pk,
            filters=request.query_params,
        )
        filters = CalendarService().get_filters(context)
        return Response([calendar_filter.as_dict() for calendar_filter in filters])


def _parse_v1_boolean(value):
    """Interpret a query value with the existing v1 boolean convention.

    The Employee list relies on django-filter's boolean widget: lower-case
    ``true`` and ``false`` are recognized, while an absent or invalid value is
    treated as no filter. This helper preserves that behavior for a computed
    property that cannot be declared as a regular model-field filter.

    Args:
        value: Raw query-string value, or ``None`` when omitted.

    Returns:
        bool | None: The parsed boolean, or ``None`` when no valid filter was
        supplied.
    """
    return {"true": True, "false": False}.get(value)


class EmployeeV1QuerysetMixin:
    """Build the shared visible Employee queryset for list and detail views.

    Visibility is delegated to the existing
    `Employee.get_instances_for_user("view", ...)` mechanism, except for list
    and detail views that opt into staff or global change access. Global viewers
    retain the full queryset, while other users receive their existing
    relation-based scope. Current statuses and superiors are prefetched solely
    for the v1 Employee serializer.

    A detail view using this queryset returns the same 404 for an unknown
    employee and an employee outside the caller's visible scope.
    """

    def get_queryset(self):
        """Return visible employees with the relations required by v1.

        Returns:
            QuerySet: Permission-bounded employees with current status and
            superior relations prefetched.
        """
        queryset = Employee.objects.all()
        if not (getattr(self, "allow_editor_view", False) and (
            self.request.user.is_staff or self.request.user.has_perm("staff.change_employee")
        )):
            queryset = Employee.get_instances_for_user(
                "view", self.request.user, queryset
            )

        current_statuses = Employee_Status.current.select_related("type").order_by(
            "type__name", "pk"
        )
        current_superiors = Employee_Superior.current.select_related(
            "superior"
        ).order_by("superior__first_name", "superior__last_name", "superior_id")

        return queryset.prefetch_related(
            Prefetch(
                "employee_status_set",
                queryset=current_statuses,
                to_attr="current_status_relations",
            ),
            Prefetch(
                "employee_hierarchy",
                queryset=current_superiors,
                to_attr="current_superior_relations",
            ),
        )


class EmployeeListV1View(EmployeeV1QuerysetMixin, generics.ListAPIView):
    """List employees visible to the authenticated user.

    Object visibility is applied by `EmployeeV1QuerysetMixin` before DRF
    performs search, filtering, ordering, and limit/offset pagination.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EmployeeListV1Serializer
    allow_editor_view = True
    pagination_class = LabPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = EmployeeListV1Filter
    search_fields = ("first_name", "last_name")
    ordering_fields = ("first_name", "last_name", "entry_date", "exit_date", "is_active")
    ordering = ("first_name", "last_name", "pk")


class EmployeeListExportV1View(EmployeeListV1View):
    """Export the exact visible, filtered and ordered list without pagination."""

    http_method_names = ("get", "head", "options")
    content_negotiation_class = ListExportContentNegotiation

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return export_list_queryset(request, queryset, EmployeeResource, "Employee")


class EmployeeListFilterOptionsV1View(APIView):
    """Offer status types and teams linked to visible Employees."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        visible = Employee.objects.all()
        if not (request.user.is_staff or request.user.has_perm("staff.change_employee")):
            visible = Employee.get_instances_for_user("view", request.user, visible)
        type_ids = Employee_Status.objects.filter(employee__in=visible).values("type_id")
        team_ids = TeamMate.objects.filter(employee__in=visible).values("team_id")
        return Response({
            "statuses": list(Employee_Type.objects.filter(pk__in=type_ids).order_by("name", "pk").values("id", "name")),
            "teams": list(Team.objects.filter(Q(leader__in=visible) | Q(pk__in=team_ids)).distinct().order_by("name", "pk").values("id", "name")),
        })


class EmployeeDetailV1View(EmployeeV1QuerysetMixin, generics.RetrieveAPIView):
    """Retrieve or edit the Employee summary used by the React detail.

    Staff retain their legacy access to every Employee detail. Other users use
    the list's permission-bounded queryset; hidden and unknown IDs return 404.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EmployeeDetailV1Serializer
    allow_editor_view = True

    def patch(self, request, *args, **kwargs):
        employee = self.get_object()
        if not employee_detail_capabilities(request.user, employee)["can_change"]:
            raise PermissionDenied()
        serializer = EmployeeDetailWriteV1Serializer(employee, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        employee.refresh_from_db()
        return Response(self.get_serializer(employee).data)


class EmployeeGenericInfoV1Mixin:
    """Authorize the root before resolving or mutating a contextual child."""

    permission_classes = (permissions.IsAuthenticated,)

    def get_employee(self):
        """Resolve once in the existing view scope; hidden and absent both yield 404."""
        if not hasattr(self, "_employee"):
            visible = Employee.get_instances_for_user(
                "view", self.request.user, Employee.objects.all()
            )
            self._employee = get_object_or_404(visible, pk=self.kwargs["pk"])
        return self._employee

    def get_queryset(self):
        return GenericInfo.objects.filter(employee=self.get_employee()).select_related(
            "info"
        ).order_by("info__name", "pk")

    def get_capabilities(self):
        return generic_info_capabilities(self.request.user, self.get_employee())

    def require_capability(self, action):
        """Enforce the same capability advertised by the contextual collection."""
        if not self.get_capabilities()[action]:
            raise PermissionDenied()


class EmployeeGenericInfoV1View(EmployeeGenericInfoV1Mixin, generics.GenericAPIView):
    """List contextual capabilities and values, or create a new value."""

    serializer_class = EmployeeGenericInfoV1Serializer

    def get(self, request, *args, **kwargs):
        return Response({
            "capabilities": self.get_capabilities(),
            "items": self.get_serializer(self.get_queryset(), many=True).data,
        })

    def post(self, request, *args, **kwargs):
        self.require_capability("can_add")
        serializer = GenericInfoWriteV1Serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        info = serializer.save(employee=self.get_employee())
        return Response(self.get_serializer(info).data, status=201)


class EmployeeGenericInfoDetailV1View(EmployeeGenericInfoV1Mixin, generics.GenericAPIView):
    """Change only value, or delete an Employee-owned information item."""

    serializer_class = EmployeeGenericInfoV1Serializer
    lookup_url_kwarg = "generic_info_id"

    def patch(self, request, *args, **kwargs):
        info = self.get_object()
        self.require_capability("can_change")
        serializer = GenericInfoWriteV1Serializer(info, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        info = serializer.save()
        return Response(self.get_serializer(info).data)

    def delete(self, request, *args, **kwargs):
        info = self.get_object()
        self.require_capability("can_delete")
        info.delete()
        return Response(status=204)


class GenericInfoTypeV1View(generics.ListAPIView):
    """Expose the global information-type catalogue to authenticated users."""

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = GenericInfoTypeV1Serializer
    pagination_class = None
    queryset = GenericInfoType.objects.order_by("name", "pk")


class EmployeeMilestoneV1View(generics.ListAPIView):
    """List all milestones assigned to one visible Employee.

    Milestones are contextual workload data: Project and co-assignee identity
    remains visible even when the caller cannot open those linked resources.
    The serializer receives the independent Project and Employee visibility
    sets so that it can expose `can_view` without filtering the collection.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EmployeePlanningMilestoneV1Serializer
    pagination_class = None

    def get_queryset(self):
        """Resolve Employee scope and preload every contextual relation."""
        user = self.request.user
        visible_employees = Employee.get_instances_for_user(
            "view", user, Employee.objects.all()
        )
        employee = get_object_or_404(visible_employees, pk=self.kwargs["pk"])

        milestones = filter_planning_items(
            Milestones.objects.filter(employee=employee).distinct(),
            self.request.query_params,
        )
        self.planning_context = planning_serializer_context(user, milestones)
        return preload_planning_items(milestones)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(getattr(self, "planning_context", {}))
        return context


class EmployeeMilestoneDetailV1View(APIView):
    """Limit an assigned Employee milestone update to progress, status and description."""

    permission_classes = (permissions.IsAuthenticated,)

    @transaction.atomic
    def patch(self, request, pk, item_id):
        visible = Employee.get_instances_for_user("view", request.user, Employee.objects.all())
        employee = get_object_or_404(visible, pk=pk)
        item = get_object_or_404(
            Milestones.objects.select_for_update().filter(employee=employee), pk=item_id,
        )
        if not request.user.has_perm("endpoints.change_milestones", item):
            raise PermissionDenied()
        serializer = EmployeeMilestonePartialWriteV1Serializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        saved = serializer.save()
        scoped = Milestones.objects.filter(pk=saved.pk)
        loaded = preload_planning_items(scoped).get()
        context = {"request": request, **planning_serializer_context(request.user, scoped)}
        return Response(EmployeePlanningMilestoneV1Serializer(loaded, context=context).data)


class EmployeeStatusHistoryV1View(generics.ListAPIView):
    """List the complete status history of one visible employee.

    The target is first resolved through
    `Employee.get_instances_for_user("view", ...)`; unknown and out-of-scope
    identifiers therefore both return 404. The resulting collection is
    read-only, unpaginated, and ordered chronologically using the historical
    end-date convention with deterministic tie-breakers.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EmployeeStatusHistoryV1Serializer
    pagination_class = None

    def get_queryset(self):
        """Return status relations after resolving the visible employee.

        Returns:
            QuerySet: Status relations with their type loaded and deterministic
            historical ordering.

        Raises:
            Http404: If the employee does not exist or is outside the caller's
            v1 visibility scope.
        """
        visible_employees = Employee.get_instances_for_user(
            "view", self.request.user, Employee.objects.all()
        )
        employee = get_object_or_404(visible_employees, pk=self.kwargs["pk"])

        return (
            Employee_Status.objects.filter(employee=employee)
            .select_related("type")
            .order_by(
                F("end_date").asc(nulls_last=True),
                F("start_date").asc(nulls_first=True),
                "pk",
            )
        )


class EmployeeHierarchyV1View(generics.RetrieveAPIView):
    """Return direct current and historical hierarchy for a visible employee.

    The target Employee is resolved only inside
    `Employee.get_instances_for_user("view", ...)`; unknown and out-of-scope
    identifiers therefore both return 404. Once the target is visible, each
    linked superior or subordinate may expose its minimal identity even when
    that linked person is outside the caller's general Employee scope. This
    relation visibility does not grant access to the linked person's detail.

    Both directions are prefetched with their linked Employee, avoiding one
    query per relation. No recursive hierarchy or unrelated Employee data is
    loaded.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EmployeeHierarchyV1Serializer

    def get_queryset(self):
        """Return visible employees with both direct relation histories.

        Each collection follows the historical end-date ordering, with open
        relations last and deterministic start-date and primary-key
        tie-breakers.

        Returns:
            QuerySet: Permission-bounded employees with direct hierarchy
            relations prefetched in both directions.
        """
        visible_employees = Employee.get_instances_for_user(
            "view", self.request.user, Employee.objects.all()
        )
        relation_order = (
            F("end_date").asc(nulls_last=True),
            F("start_date").asc(nulls_first=True),
            "pk",
        )
        superior_relations = Employee_Superior.objects.select_related(
            "superior"
        ).order_by(*relation_order)
        subordinate_relations = Employee_Superior.objects.select_related(
            "employee"
        ).order_by(*relation_order)

        return visible_employees.prefetch_related(
            Prefetch(
                "employee_hierarchy",
                queryset=superior_relations,
                to_attr="hierarchy_superiors",
            ),
            Prefetch(
                "superior_employee",
                queryset=subordinate_relations,
                to_attr="hierarchy_subordinates",
            ),
        )


class EmployeeProjectParticipationV1View(generics.ListAPIView):
    """List project participations belonging to one visible Employee.

    The target is first resolved exclusively inside
    `Employee.get_instances_for_user("view", ...)`; unknown and out-of-scope
    identifiers therefore both return 404. Once the Employee is visible, all
    of that Employee's Participant relations are returned without applying a
    separate Project visibility filter. This is relation visibility in the
    Employee context and grants no independent right to retrieve the Project.

    Only a minimal Project reference is loaded with `select_related`. Results
    are unpaginated and deterministic: active participations first, then by
    most recent end date, most recent start date, and primary key.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProjectParticipationV1Serializer
    pagination_class = None

    def get_serializer_context(self):
        """Expose independent Project visibility without filtering participations."""
        context = super().get_serializer_context()
        project_ids = Participant.objects.filter(
            employee_id=self.kwargs["pk"]
        ).values_list("project_id", flat=True)
        context["visible_project_ids"] = set(
            Project.get_instances_for_user(
                "view", self.request.user, Project.objects.filter(pk__in=project_ids)
            ).values_list("pk", flat=True)
        )
        return context

    def get_queryset(self):
        """Return the target Employee's optionally filtered participations.

        The ORM active expression is strictly equivalent to
        `ActiveDateMixin.is_active`: a missing bound is open, a start date is
        active from that date inclusively, and an end date remains active
        through that date inclusively. Its negation therefore uses strict
        future-start and past-end comparisons. This intentionally avoids the
        mixin's `get_inactive_filter`, whose inclusive comparisons overlap the
        active set on today's boundaries.

        Returns:
            QuerySet: Participant rows with only their Project relation joined,
            filtered inside the already-authorized Employee scope.

        Raises:
            Http404: If the Employee is unknown or outside the caller's v1
            visibility scope.
        """
        visible_employees = Employee.get_instances_for_user(
            "view", self.request.user, Employee.objects.all()
        )
        employee = get_object_or_404(visible_employees, pk=self.kwargs["pk"])

        today = date.today()
        active_filter = (
            (Q(start_date__isnull=True) | Q(start_date__lte=today))
            & (Q(end_date__isnull=True) | Q(end_date__gte=today))
        )
        queryset = Participant.objects.filter(employee=employee).select_related(
            "project"
        )
        requested_active = _parse_v1_boolean(
            self.request.query_params.get("is_active")
        )
        if requested_active is True:
            queryset = queryset.filter(active_filter)
        elif requested_active is False:
            queryset = queryset.filter(
                Q(start_date__gt=today) | Q(end_date__lt=today)
            )

        return queryset.annotate(
            _v1_active_order=Case(
                When(active_filter, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by(
            "_v1_active_order",
            F("end_date").desc(nulls_first=True),
            F("start_date").desc(nulls_last=True),
            "pk",
        )


def _workload_composition(participations, segment_start, visible_project_ids):
    """Aggregate active Participant quotities by Project at one boundary."""
    projects = {}
    for participation in participations:
        starts_before = participation.start_date is None or segment_start is None or participation.start_date <= segment_start
        ends_after = participation.end_date is None or segment_start is None or participation.end_date >= segment_start
        if segment_start is None:
            starts_before = participation.start_date is None
            ends_after = participation.end_date is None or participation.start_date is None
        if not (starts_before and ends_after):
            continue
        project = projects.setdefault(
            participation.project_id,
            {
                "id": participation.project_id,
                "name": participation.project.name,
                "quotity": Decimal("0"),
                "can_view": participation.project_id in visible_project_ids,
            },
        )
        project["quotity"] += participation.quotity

    result = []
    for project in sorted(projects.values(), key=lambda item: (item["name"], item["id"])):
        result.append({**project, "quotity": format(project["quotity"], "f")})
    return result


def _build_workload_segments(participations, requested_start, requested_end, visible_project_ids):
    """Build inclusive, contiguous segments only at Participant boundaries."""
    if requested_start is not None and requested_end is not None:
        boundaries = {requested_start, requested_end + timedelta(days=1)}
        for participation in participations:
            boundaries.add(max(participation.start_date or requested_start, requested_start))
            effective_end = min(participation.end_date or requested_end, requested_end)
            boundaries.add(effective_end + timedelta(days=1))
        ordered = sorted(boundaries)
        intervals = [(ordered[index], ordered[index + 1] - timedelta(days=1)) for index in range(len(ordered) - 1)]
    else:
        boundaries = sorted(
            {participation.start_date for participation in participations if participation.start_date is not None}
            | {participation.end_date + timedelta(days=1) for participation in participations if participation.end_date is not None}
        )
        if not boundaries:
            intervals = [(None, None)] if participations else []
        else:
            intervals = []
            if any(participation.start_date is None for participation in participations):
                intervals.append((None, boundaries[0] - timedelta(days=1)))
            intervals.extend(
                (boundaries[index], boundaries[index + 1] - timedelta(days=1))
                for index in range(len(boundaries) - 1)
            )
            if any(participation.end_date is None for participation in participations):
                intervals.append((boundaries[-1], None))

    segments = []
    for segment_start, segment_end in intervals:
        composition = _workload_composition(participations, segment_start, visible_project_ids)
        total = sum((Decimal(project["quotity"]) for project in composition), Decimal("0"))
        segment = {
            "start": segment_start.isoformat() if segment_start else None,
            "end": segment_end.isoformat() if segment_end else None,
            "total_quotity": format(total, "f"),
            "projects": composition,
        }
        if segments and segments[-1]["projects"] == segment["projects"]:
            segments[-1]["end"] = segment["end"]
        else:
            segments.append(segment)
    return segments


class EmployeeProjectWorkloadV1View(APIView):
    """Return the exact temporal Project workload of one visible Employee."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        visible_employees = Employee.get_instances_for_user(
            "view", request.user, Employee.objects.all()
        )
        employee = get_object_or_404(visible_employees, pk=pk)

        range_value = request.query_params.get("range")
        raw_start = request.query_params.get("start")
        raw_end = request.query_params.get("end")
        if range_value is not None:
            if range_value != "all" or raw_start is not None or raw_end is not None:
                raise ValidationError({"range": "Use range=all without start or end."})
            requested_start = requested_end = None
            queryset = Participant.objects.filter(employee=employee)
        else:
            if raw_start is None or raw_end is None:
                raise ValidationError({"range": "Both start and end are required."})
            try:
                requested_start = date.fromisoformat(raw_start)
                requested_end = date.fromisoformat(raw_end)
            except ValueError as error:
                raise ValidationError({"range": "start and end must use YYYY-MM-DD."}) from error
            if requested_start.isoformat() != raw_start or requested_end.isoformat() != raw_end:
                raise ValidationError({"range": "start and end must use YYYY-MM-DD."})
            if requested_start > requested_end:
                raise ValidationError({"range": "start must be before or equal to end."})
            queryset = Participant.objects.filter(
                employee=employee,
            ).filter(
                Q(start_date__isnull=True) | Q(start_date__lte=requested_end),
                Q(end_date__isnull=True) | Q(end_date__gte=requested_start),
            )

        participations = list(queryset.select_related("project").order_by("pk"))
        project_ids = {participation.project_id for participation in participations}
        visible_project_ids = set(
            Project.get_instances_for_user(
                "view", request.user, Project.objects.filter(pk__in=project_ids)
            ).values_list("pk", flat=True)
        )
        if range_value == "all":
            range_start = None if any(item.start_date is None for item in participations) else min((item.start_date for item in participations), default=None)
            range_end = None if any(item.end_date is None for item in participations) else max((item.end_date for item in participations), default=None)
        else:
            range_start, range_end = requested_start, requested_end

        return Response({
            "range": {
                "start": range_start.isoformat() if range_start else None,
                "end": range_end.isoformat() if range_end else None,
            },
            "segments": _build_workload_segments(
                participations, requested_start, requested_end, visible_project_ids
            ),
        })


def _contribution_workload_composition(contributions, segment_start):
    """Return active Contributions and their exact Decimal quotities."""
    composition = []
    for contribution in contributions:
        if segment_start is None:
            active = contribution.start_date is None
        else:
            active = (
                (contribution.start_date is None or contribution.start_date <= segment_start)
                and (contribution.end_date is None or contribution.end_date >= segment_start)
            )
        if not active:
            continue
        composition.append(
            {
                "id": contribution.pk,
                "quotity": format(contribution.quotity or Decimal("0"), "f"),
                "fund": {
                    "id": contribution.fund_id,
                    "display_name": str(contribution.fund),
                    "reference": contribution.fund.ref or None,
                },
                "project": {
                    "id": contribution.fund.project_id,
                    "name": contribution.fund.project.name,
                },
                "cost_type": (
                    {
                        "id": contribution.cost_type_id,
                        "short_name": contribution.cost_type.short_name,
                        "name": contribution.cost_type.name,
                    }
                    if contribution.cost_type_id
                    else None
                ),
            }
        )
    return composition


def _build_contribution_workload_segments(
    contributions, requested_start, requested_end
):
    """Build an inclusive step profile at Contribution date boundaries."""
    if requested_start is not None and requested_end is not None:
        boundaries = {requested_start, requested_end + timedelta(days=1)}
        for contribution in contributions:
            boundaries.add(
                max(contribution.start_date or requested_start, requested_start)
            )
            effective_end = min(
                contribution.end_date or requested_end, requested_end
            )
            boundaries.add(effective_end + timedelta(days=1))
        ordered = sorted(boundaries)
        intervals = [
            (ordered[index], ordered[index + 1] - timedelta(days=1))
            for index in range(len(ordered) - 1)
        ]
    else:
        boundaries = sorted(
            {
                contribution.start_date
                for contribution in contributions
                if contribution.start_date is not None
            }
            | {
                contribution.end_date + timedelta(days=1)
                for contribution in contributions
                if contribution.end_date is not None
            }
        )
        if not boundaries:
            intervals = [(None, None)] if contributions else []
        else:
            intervals = []
            if any(item.start_date is None for item in contributions):
                intervals.append((None, boundaries[0] - timedelta(days=1)))
            intervals.extend(
                (boundaries[index], boundaries[index + 1] - timedelta(days=1))
                for index in range(len(boundaries) - 1)
            )
            if any(item.end_date is None for item in contributions):
                intervals.append((boundaries[-1], None))

    segments = []
    for segment_start, segment_end in intervals:
        composition = _contribution_workload_composition(
            contributions, segment_start
        )
        total = sum(
            (Decimal(item["quotity"]) for item in composition), Decimal("0")
        )
        segment = {
            "start": segment_start.isoformat() if segment_start else None,
            "end": segment_end.isoformat() if segment_end else None,
            "total_quotity": format(total, "f"),
            "contributions": composition,
        }
        if segments and segments[-1]["contributions"] == composition:
            segments[-1]["end"] = segment["end"]
        else:
            segments.append(segment)
    return segments


class EmployeeContributionWorkloadV1View(APIView):
    """Return the exact Contribution quotity profile of one visible Employee."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        visible_employees = Employee.get_instances_for_user(
            "view", request.user, Employee.objects.all()
        )
        employee = get_object_or_404(visible_employees, pk=pk)

        range_value = request.query_params.get("range")
        raw_start = request.query_params.get("start")
        raw_end = request.query_params.get("end")
        if range_value is not None:
            if range_value != "all" or raw_start is not None or raw_end is not None:
                raise ValidationError(
                    {"range": "Use range=all without start or end."}
                )
            requested_start = requested_end = None
            queryset = Contribution.objects.filter(employee=employee)
        else:
            if raw_start is None or raw_end is None:
                raise ValidationError(
                    {"range": "Both start and end are required."}
                )
            try:
                requested_start = date.fromisoformat(raw_start)
                requested_end = date.fromisoformat(raw_end)
            except ValueError as error:
                raise ValidationError(
                    {"range": "start and end must use YYYY-MM-DD."}
                ) from error
            if (
                requested_start.isoformat() != raw_start
                or requested_end.isoformat() != raw_end
            ):
                raise ValidationError(
                    {"range": "start and end must use YYYY-MM-DD."}
                )
            if requested_start > requested_end:
                raise ValidationError(
                    {"range": "start must be before or equal to end."}
                )
            queryset = Contribution.objects.filter(employee=employee).filter(
                Q(start_date__isnull=True) | Q(start_date__lte=requested_end),
                Q(end_date__isnull=True) | Q(end_date__gte=requested_start),
            )

        contributions = list(
            queryset.select_related(
                "fund__project",
                "fund__funder",
                "fund__institution",
                "cost_type",
            ).order_by("pk")
        )
        if range_value == "all":
            range_start = (
                None
                if any(item.start_date is None for item in contributions)
                else min((item.start_date for item in contributions), default=None)
            )
            range_end = (
                None
                if any(item.end_date is None for item in contributions)
                else max((item.end_date for item in contributions), default=None)
            )
        else:
            range_start, range_end = requested_start, requested_end

        return Response(
            {
                "range": {
                    "start": range_start.isoformat() if range_start else None,
                    "end": range_end.isoformat() if range_end else None,
                },
                "segments": _build_contribution_workload_segments(
                    contributions, requested_start, requested_end
                ),
            }
        )
