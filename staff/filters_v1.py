from django.db.models import Q
from django_filters import rest_framework as filters

from .models import Employee, Employee_Status, Employee_Superior, Team, TeamMate


class EmployeeListV1Filter(filters.FilterSet):
    """Apply explicit Employee list filters without widening visible scope.

    DRF receives an Employee queryset already bounded by
    `Employee.get_instances_for_user("view", ...)`. Every method narrows that
    queryset through related identifiers and never starts from an unrestricted
    Employee collection.
    """

    is_active = filters.BooleanFilter(field_name="is_active")
    status = filters.NumberFilter(method="filter_status")
    current_status = filters.NumberFilter(method="filter_current_status")
    superior = filters.NumberFilter(method="filter_superior")
    team = filters.NumberFilter(method="filter_team")

    class Meta:
        model = Employee
        fields = ("is_active", "status", "current_status", "superior", "team")

    def filter_status(self, queryset, name, value):
        """Keep employees having the requested status type at any date.

        Args:
            queryset: Already permission-bounded Employee queryset.
            name: Filter name supplied by django-filter.
            value: Employee_Type primary key.

        Returns:
            QuerySet: The original scope narrowed to matching employees.
        """
        employee_ids = Employee_Status.objects.filter(type_id=value).values(
            "employee_id"
        )
        return queryset.filter(pk__in=employee_ids)

    def filter_current_status(self, queryset, name, value):
        """Keep employees currently assigned to the requested status type.

        Args:
            queryset: Already permission-bounded Employee queryset.
            name: Filter name supplied by django-filter.
            value: Employee_Type primary key.

        Returns:
            QuerySet: The original scope narrowed to current matches.
        """
        employee_ids = Employee_Status.current.filter(type_id=value).values(
            "employee_id"
        )
        return queryset.filter(pk__in=employee_ids)

    def filter_superior(self, queryset, name, value):
        """Keep employees currently reporting to the selected superior.

        Args:
            queryset: Already permission-bounded Employee queryset.
            name: Filter name supplied by django-filter.
            value: Superior Employee primary key.

        Returns:
            QuerySet: The original scope narrowed to current relationships.
        """
        employee_ids = Employee_Superior.current.filter(superior_id=value).values(
            "employee_id"
        )
        return queryset.filter(pk__in=employee_ids)

    def filter_team(self, queryset, name, value):
        """Keep current team members and the selected team's leader.

        Args:
            queryset: Already permission-bounded Employee queryset.
            name: Filter name supplied by django-filter.
            value: Team primary key.

        Returns:
            QuerySet: Distinct employees in the original scope who lead or
            currently belong to the team.
        """
        leader_ids = Team.objects.filter(pk=value).values("leader_id")
        member_ids = TeamMate.current.filter(team_id=value).values("employee_id")
        return queryset.filter(Q(pk__in=leader_ids) | Q(pk__in=member_ids)).distinct()
