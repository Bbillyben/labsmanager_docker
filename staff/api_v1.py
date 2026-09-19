from datetime import date

from django.db.models import Case, F, IntegerField, Prefetch, Q, Value, When
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions

from labsmanager.pagination import LabPagination
from project.models import Participant

from .filters_v1 import EmployeeListV1Filter
from .models import Employee, Employee_Status, Employee_Superior
from .serializers_v1 import (
    EmployeeHierarchyV1Serializer,
    EmployeeListV1Serializer,
    EmployeeStatusHistoryV1Serializer,
    ProjectParticipationV1Serializer,
)


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
    `Employee.get_instances_for_user("view", ...)` mechanism. Global viewers
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
    pagination_class = LabPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = EmployeeListV1Filter
    search_fields = ("first_name", "last_name")
    ordering_fields = ("first_name", "last_name", "entry_date", "exit_date", "is_active")
    ordering = ("first_name", "last_name", "pk")


class EmployeeDetailV1View(EmployeeV1QuerysetMixin, generics.RetrieveAPIView):
    """Retrieve the minimal Employee v1 representation within visible scope.

    The lookup runs against the same permission-bounded queryset as the list.
    Consequently, unknown and out-of-scope identifiers both return 404.
    """

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EmployeeListV1Serializer


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
