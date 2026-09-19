from rest_framework import serializers

from project.models import Participant, Project

from .models import Employee, Employee_Status, Employee_Superior, Employee_Type


class EmployeeStatusTypeV1Serializer(serializers.ModelSerializer):
    """Serialize the stable status-type identity shared by Employee v1."""

    code = serializers.CharField(source="shortname")

    class Meta:
        model = Employee_Type
        fields = ("id", "code", "name")


class EmployeeListV1Serializer(serializers.ModelSerializer):
    """Serialize the minimal contract shared by Employee list and detail.

    The view must attach `current_status_relations` and
    `current_superior_relations` through prefetches. Keeping these relations
    explicit prevents per-row queries and avoids expanding the contract with
    unrelated Employee data.
    """

    current_statuses = serializers.SerializerMethodField()
    superiors = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = (
            "id",
            "first_name",
            "last_name",
            "entry_date",
            "exit_date",
            "is_active",
            "current_statuses",
            "superiors",
        )

    def get_current_statuses(self, employee):
        """Serialize prefetched current status types.

        Args:
            employee: Employee instance carrying `current_status_relations`.

        Returns:
            list[dict]: Status types in the shared `id`, `code`, `name`
            representation.
        """
        status_types = (
            status.type for status in employee.current_status_relations
        )
        return EmployeeStatusTypeV1Serializer(status_types, many=True).data

    def get_superiors(self, employee):
        """Serialize prefetched current superiors without extra queries.

        Args:
            employee: Employee instance carrying
                `current_superior_relations`.

        Returns:
            list[dict]: Minimal identities of current superiors.
        """
        return [
            {
                "id": relation.superior_id,
                "first_name": relation.superior.first_name,
                "last_name": relation.superior.last_name,
            }
            for relation in employee.current_superior_relations
        ]


class EmployeeStatusHistoryV1Serializer(serializers.ModelSerializer):
    """Serialize one historical Employee-to-status relation.

    The contract exposes both the stable stored contractuality code and the
    human label supplied by the model choices. `is_active` reuses the
    date-aware property inherited by `Employee_Status`.
    """

    type = EmployeeStatusTypeV1Serializer(read_only=True)
    contractuality = serializers.SerializerMethodField()
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Employee_Status
        fields = (
            "id",
            "type",
            "start_date",
            "end_date",
            "contractuality",
            "is_active",
        )

    def get_contractuality(self, status):
        """Return the stored contractuality code and its Django label.

        Args:
            status: Employee_Status relation being serialized.

        Returns:
            dict[str, str]: Stable code plus the choice display label.
        """
        return {
            "code": status.is_contractual,
            "label": status.get_is_contractual_display(),
        }


class EmployeeIdentityV1Serializer(serializers.ModelSerializer):
    """Serialize only the identity allowed for a related employee."""

    class Meta:
        model = Employee
        fields = ("id", "first_name", "last_name")


class EmployeeSuperiorRelationV1Serializer(serializers.ModelSerializer):
    """Serialize a hierarchy relation from its employee to its superior.

    `is_active` comes from the existing date-aware property inherited by
    `Employee_Superior`; no date logic is duplicated in the API.
    """

    employee = EmployeeIdentityV1Serializer(source="superior", read_only=True)
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Employee_Superior
        fields = ("id", "employee", "start_date", "end_date", "is_active")


class EmployeeSubordinateRelationV1Serializer(serializers.ModelSerializer):
    """Serialize a hierarchy relation from its superior to its subordinate.

    `is_active` comes from the existing date-aware property inherited by
    `Employee_Superior`; no date logic is duplicated in the API.
    """

    employee = EmployeeIdentityV1Serializer(read_only=True)
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Employee_Superior
        fields = ("id", "employee", "start_date", "end_date", "is_active")


class EmployeeHierarchyV1Serializer(serializers.ModelSerializer):
    """Serialize direct superior and subordinate histories for one employee.

    The view attaches both relation collections through dedicated prefetches.
    Linked people are intentionally represented only by identity: their
    presence in a visible relation does not make their own Employee detail
    endpoint accessible.
    """

    superiors = serializers.SerializerMethodField()
    subordinates = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ("superiors", "subordinates")

    def get_superiors(self, employee):
        """Serialize prefetched relations where the target is subordinate.

        Args:
            employee: Visible Employee carrying `hierarchy_superiors`.

        Returns:
            list[dict]: Direct current and historical superior relations.
        """
        return EmployeeSuperiorRelationV1Serializer(
            employee.hierarchy_superiors,
            many=True,
        ).data

    def get_subordinates(self, employee):
        """Serialize prefetched relations where the target is superior.

        Args:
            employee: Visible Employee carrying `hierarchy_subordinates`.

        Returns:
            list[dict]: Direct current and historical subordinate relations.
        """
        return EmployeeSubordinateRelationV1Serializer(
            employee.hierarchy_subordinates,
            many=True,
        ).data


class ProjectReferenceV1Serializer(serializers.ModelSerializer):
    """Serialize the minimal Project identity needed by an Employee relation.

    This reference deliberately excludes Project status, permissions, finance,
    participants, and other domain data. Its presence does not grant access to
    a future standalone Project resource.
    """

    class Meta:
        model = Project
        fields = ("id", "name", "start_date", "end_date")


class ProjectParticipationV1Serializer(serializers.ModelSerializer):
    """Serialize an Employee's read-only participation in a Project.

    Role combines the stable stored code with the label from the model choices.
    Quotity keeps DRF's exact decimal string representation, and `is_active`
    delegates to the existing `ActiveDateMixin` property.
    """

    project = ProjectReferenceV1Serializer(read_only=True)
    role = serializers.SerializerMethodField()
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Participant
        fields = (
            "id",
            "project",
            "role",
            "start_date",
            "end_date",
            "quotity",
            "is_active",
        )

    def get_role(self, participant):
        """Return the stored role code and its existing Django choice label.

        Args:
            participant: Participant relation being serialized.

        Returns:
            dict[str, str]: Stable role code plus its human-readable label.
        """
        return {
            "code": participant.status,
            "label": participant.get_status_display(),
        }
