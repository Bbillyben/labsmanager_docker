from django.urls import reverse
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import connection, transaction
from rest_framework import serializers
from labsmanager.admin_links_v1 import AdminUrlSerializerMixin

from expense.models import Contract, Contract_expense
from fund.models import Budget, Contribution
from leave.models import Leave, Leave_Type
from project.models import Participant, Project
from reports.api_v1 import report_capabilities
from .permissions_v1 import employee_detail_capabilities

from .models import (
    Employee,
    Employee_Status,
    Employee_Superior,
    Employee_Type,
    GenericInfo,
    GenericInfoType,
)


class EmployeeStatusTypeV1Serializer(serializers.ModelSerializer):
    """Serialize the stable status-type identity shared by Employee v1."""

    code = serializers.CharField(source="shortname")

    class Meta:
        model = Employee_Type
        fields = ("id", "code", "name")


class EmployeeListV1Serializer(AdminUrlSerializerMixin, serializers.ModelSerializer):
    """Serialize the minimal contract shared by Employee list and detail.

    The view must attach `current_status_relations` and
    `current_superior_relations` through prefetches. Keeping these relations
    explicit prevents per-row queries and avoids expanding the contract with
    unrelated Employee data.
    """

    current_statuses = serializers.SerializerMethodField()
    superiors = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = (
            "id",
            "admin_url",
            "first_name",
            "last_name",
            "entry_date",
            "exit_date",
            "is_active",
            "current_statuses",
            "superiors",
            "capabilities",
        )

    def get_capabilities(self, employee):
        return employee_detail_capabilities(self.context["request"].user, employee)

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


class EmployeeDetailV1Serializer(EmployeeListV1Serializer):
    """Serialize the read-only Employee summary used by the React detail."""

    contract_quotity = serializers.SerializerMethodField()
    project_quotity = serializers.SerializerMethodField()
    contribution_quotity = serializers.SerializerMethodField()
    active_milestones_count = serializers.SerializerMethodField()

    class Meta(EmployeeListV1Serializer.Meta):
        fields = EmployeeListV1Serializer.Meta.fields + (
            "birth_date",
            "email",
            "contract_quotity",
            "project_quotity",
            "contribution_quotity",
            "active_milestones_count",
        )

    def get_capabilities(self, employee):
        user = self.context["request"].user
        return {
            **report_capabilities(user, "employee", employee),
            **employee_detail_capabilities(user, employee),
        }

    @staticmethod
    def _quotity(value):
        """Keep nullable aggregate quotities in the API's decimal-string form."""
        return None if value is None else format(value, ".3f")

    def get_contract_quotity(self, employee):
        return self._quotity(employee.contracts_quotity())

    def get_project_quotity(self, employee):
        return self._quotity(employee.projects_quotity())

    def get_contribution_quotity(self, employee):
        return self._quotity(employee.contribution_quotity())

    def get_active_milestones_count(self, employee):
        return employee.active_milestones().count()


class EmployeeDetailWriteV1Serializer(serializers.ModelSerializer):
    """The fields editable in the legacy Employee form after creation."""

    class Meta:
        model = Employee
        fields = ("birth_date", "entry_date", "exit_date", "email", "is_active")

    def validate(self, attrs):
        entry_date = attrs.get("entry_date", self.instance.entry_date)
        exit_date = attrs.get("exit_date", self.instance.exit_date)
        if entry_date and exit_date and entry_date > exit_date:
            raise serializers.ValidationError({"exit_date": _("Exit date must be after entry date.")})
        return attrs


class GenericInfoTypeV1Serializer(serializers.ModelSerializer):
    """Serialize the configured identity of an Employee information type."""

    class Meta:
        model = GenericInfoType
        fields = ("id", "name", "icon")


class EmployeeGenericInfoV1Serializer(serializers.ModelSerializer):
    """Serialize the server representation used by reads and successful writes."""

    type = GenericInfoTypeV1Serializer(source="info", read_only=True)

    class Meta:
        model = GenericInfo
        fields = ("id", "type", "value")


class GenericInfoWriteV1Serializer(serializers.Serializer):
    """Validate explicit writes; identity and parent cannot be reassigned."""

    type_id = serializers.PrimaryKeyRelatedField(
        source="info", queryset=GenericInfoType.objects.all()
    )
    value = serializers.CharField(
        max_length=150, required=False, allow_blank=True, allow_null=True,
        trim_whitespace=False,
    )

    def to_internal_value(self, data):
        """Reject parent injection and type reassignment before DRF validation."""
        allowed = {"value"} if self.instance is not None else {"type_id", "value"}
        if isinstance(data, dict):
            unexpected = set(data) - allowed
            if unexpected:
                raise serializers.ValidationError({
                    key: [_("This field cannot be supplied or changed.")]
                    for key in sorted(unexpected)
                })
        return super().to_internal_value(data)

    def create(self, validated_data):
        return GenericInfo.objects.create(**validated_data)

    def update(self, instance, validated_data):
        if "value" in validated_data:
            instance.value = validated_data["value"]
            instance.save(update_fields=["value"])
        return instance


class EmployeeContractExpenseV1Serializer(serializers.ModelSerializer):
    """Serialize the small expense subset needed by the Contract Sheet."""

    type = serializers.SerializerMethodField()

    class Meta:
        model = Contract_expense
        fields = ("id", "expense_id", "date", "desc", "type", "amount")

    def get_type(self, expense):
        return {
            "id": expense.type_id,
            "short_name": expense.type.short_name,
            "name": expense.type.name,
        }


class EmployeeContractV1Serializer(serializers.ModelSerializer):
    """Serialize one scoped Contract for the Employee contracts panel."""

    contract_type = serializers.SerializerMethodField()
    employee = serializers.SerializerMethodField()
    fund = serializers.SerializerMethodField()
    requires_follow_up = serializers.BooleanField(source="is_active")
    status = serializers.SerializerMethodField()
    temporal_state = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = (
            "id",
            "employee",
            "contract_type",
            "fund",
            "start_date",
            "end_date",
            "quotity",
            "status",
            "requires_follow_up",
            "temporal_state",
        )

    def get_employee(self, contract):
        return {
            "id": contract.employee_id,
            "first_name": contract.employee.first_name,
            "last_name": contract.employee.last_name,
            "can_view": contract.employee_id in self.context.get("visible_employee_ids", set()),
        }

    def get_contract_type(self, contract):
        if contract.contract_type_id is None:
            return None
        return {"id": contract.contract_type_id, "name": contract.contract_type.name}

    def get_fund(self, contract):
        fund = contract.fund
        can_view_organizations = self.context.get("can_view_organizations", False)
        visible_project_ids = self.context.get("visible_project_ids", set())
        return {
            "id": fund.pk,
            "display_name": str(fund),
            "reference": fund.ref or None,
            "project": {
                "id": fund.project_id,
                "name": fund.project.name,
                "can_view": fund.project_id in visible_project_ids,
                "url": None,
            },
            "funder": {
                "id": fund.funder_id,
                "short_name": fund.funder.short_name,
                "name": fund.funder.name,
                "can_view": can_view_organizations,
                "url": (
                    reverse(
                        "orga_single",
                        kwargs={
                            "app": "fund",
                            "model": "fund_institution",
                            "pk": fund.funder_id,
                        },
                    )
                    if can_view_organizations
                    else None
                ),
            },
            "institution": {
                "id": fund.institution_id,
                "short_name": fund.institution.short_name,
                "name": fund.institution.name,
                "can_view": can_view_organizations,
                "url": (
                    reverse(
                        "orga_single",
                        kwargs={
                            "app": "project",
                            "model": "institution",
                            "pk": fund.institution_id,
                        },
                    )
                    if can_view_organizations
                    else None
                ),
            },
        }

    def get_status(self, contract):
        return {"code": contract.status, "label": contract.get_status_display()}

    def get_temporal_state(self, contract):
        today = self.context["today"]
        if contract.start_date and contract.start_date > today:
            return "future"
        if contract.end_date and contract.end_date < today:
            return "past"
        return "current"


class EmployeeContractDetailV1Serializer(EmployeeContractV1Serializer):
    """Add on-demand Contract expenses to the summary contract."""

    expenses = serializers.SerializerMethodField()
    expense_count = serializers.SerializerMethodField()
    expense_total = serializers.SerializerMethodField()

    class Meta(EmployeeContractV1Serializer.Meta):
        fields = EmployeeContractV1Serializer.Meta.fields + (
            "expense_count",
            "expense_total",
            "expenses",
        )

    def get_expenses(self, contract):
        return EmployeeContractExpenseV1Serializer(
            self.context.get("contract_expenses", ()), many=True
        ).data

    def get_expense_count(self, contract):
        return len(self.context.get("contract_expenses", ()))

    def get_expense_total(self, contract):
        total = sum(
            (expense.amount for expense in self.context.get("contract_expenses", ())),
            start=0,
        )
        return format(total, ".2f")


class EmployeeContributionV1Serializer(serializers.ModelSerializer):
    """Serialize one Contribution in the context of an authorized Employee."""

    fund = serializers.SerializerMethodField()
    cost_type = serializers.SerializerMethodField()
    employee_type = serializers.SerializerMethodField()
    contract_types = serializers.SerializerMethodField()
    temporal_state = serializers.SerializerMethodField()

    class Meta:
        model = Contribution
        fields = (
            "id",
            "fund",
            "cost_type",
            "desc",
            "start_date",
            "end_date",
            "quotity",
            "amount",
            "employee_type",
            "contract_types",
            "temporal_state",
        )

    def get_fund(self, contribution):
        fund = contribution.fund
        return {
            "id": fund.pk,
            "display_name": str(fund),
            "reference": fund.ref or None,
            "project": {
                "id": fund.project_id,
                "name": fund.project.name,
            },
        }

    def get_cost_type(self, contribution):
        cost_type = contribution.cost_type
        if cost_type is None:
            return None
        return {
            "id": cost_type.pk,
            "short_name": cost_type.short_name,
            "name": cost_type.name,
            "is_hr": cost_type.pk in self.context.get("hr_cost_type_ids", set()),
        }

    def get_employee_type(self, contribution):
        employee_type = contribution.emp_type
        if employee_type is None:
            return None
        return {
            "id": employee_type.pk,
            "code": employee_type.shortname,
            "name": employee_type.name,
        }

    def get_contract_types(self, contribution):
        return [
            {"id": contract_type.pk, "name": contract_type.name}
            for contract_type in contribution.contract_type.all()
        ]

    def get_temporal_state(self, contribution):
        today = self.context["today"]
        if contribution.start_date and contribution.start_date > today:
            return "future"
        if contribution.end_date and contribution.end_date < today:
            return "past"
        return "current"


class EmployeeBudgetV1Serializer(serializers.ModelSerializer):
    """Serialize one Employee Budget with explicit Django-side financials."""

    fund = serializers.SerializerMethodField()
    cost_type = serializers.SerializerMethodField()
    employee_type = serializers.SerializerMethodField()
    contract_types = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    consumed = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()
    consumption_ratio = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = (
            "id",
            "fund",
            "cost_type",
            "desc",
            "employee_type",
            "contract_types",
            "quotity",
            "amount",
            "consumed",
            "available",
            "consumption_ratio",
        )

    def get_fund(self, budget):
        fund = budget.fund
        return {
            "id": fund.pk,
            "display_name": str(fund),
            "reference": fund.ref or None,
            "project": {
                "id": fund.project_id,
                "name": fund.project.name,
            },
        }

    def get_cost_type(self, budget):
        cost_type = budget.cost_type
        if cost_type is None:
            return None
        return {
            "id": cost_type.pk,
            "short_name": cost_type.short_name,
            "name": cost_type.name,
            "is_hr": cost_type.pk in self.context.get("hr_cost_type_ids", set()),
        }

    def get_employee_type(self, budget):
        employee_type = budget.emp_type
        if employee_type is None:
            return None
        return {
            "id": employee_type.pk,
            "code": employee_type.shortname,
            "name": employee_type.name,
        }

    def get_contract_types(self, budget):
        return [
            {"id": contract_type.pk, "name": contract_type.name}
            for contract_type in budget.contract_type.all()
        ]

    def get_amount(self, budget):
        return self._money(budget.amount)

    def get_consumed(self, budget):
        if budget.expense is None:
            return None
        return self._money(budget.expense)

    def get_available(self, budget):
        return self._money(budget.available)

    def get_consumption_ratio(self, budget):
        ratio = budget.get_consumption_ratio()
        if ratio == "-":
            return None
        return format(ratio, "f")

    @staticmethod
    def _money(value):
        return None if value is None else format(value, ".2f")


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


class EmployeeStatusCreateV1Serializer(serializers.Serializer):
    type = serializers.PrimaryKeyRelatedField(queryset=Employee_Type.objects.all())
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    is_contractual = serializers.ChoiceField(choices=Employee_Status.contract_status, required=False, default="c")


class EmployeeStatusUpdateV1Serializer(serializers.Serializer):
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    is_contractual = serializers.ChoiceField(choices=Employee_Status.contract_status, required=False)


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
    can_view = serializers.SerializerMethodField()

    class Meta:
        model = Employee_Superior
        fields = ("id", "employee", "start_date", "end_date", "is_active", "can_view")

    def get_can_view(self, relation):
        return relation.superior_id in self.context.get("visible_linked_ids", set())


class EmployeeSubordinateRelationV1Serializer(serializers.ModelSerializer):
    """Serialize a hierarchy relation from its superior to its subordinate.

    `is_active` comes from the existing date-aware property inherited by
    `Employee_Superior`; no date logic is duplicated in the API.
    """

    employee = EmployeeIdentityV1Serializer(read_only=True)
    is_active = serializers.ReadOnlyField()
    can_view = serializers.SerializerMethodField()

    class Meta:
        model = Employee_Superior
        fields = ("id", "employee", "start_date", "end_date", "is_active", "can_view")

    def get_can_view(self, relation):
        return relation.employee_id in self.context.get("visible_linked_ids", set())


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
            context=self.context,
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
            context=self.context,
        ).data


class EmployeeHierarchyCreateV1Serializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=("superior", "subordinate"))
    employee_id = serializers.IntegerField(min_value=1)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)


class EmployeeHierarchyDatesV1Serializer(serializers.Serializer):
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)


class ProjectReferenceV1Serializer(serializers.ModelSerializer):
    """Serialize the minimal Project identity needed by an Employee relation.

    This reference deliberately excludes Project status, finance, participants,
    and other domain data. Its presence does not grant standalone Project access;
    `can_view` only reports the existing independent visibility rule.
    """

    can_view = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ("id", "name", "start_date", "end_date", "can_view")

    def get_can_view(self, project):
        """Report independent visibility for this contextual reference."""
        return project.pk in self.context.get("visible_project_ids", set())


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


class EmployeeLeaveTypeV1Serializer(serializers.ModelSerializer):
    """Serialize the Leave type displayed by the Employee panel."""

    class Meta:
        model = Leave_Type
        fields = ("id", "short_name", "name", "color")


class EmployeeLeaveV1Serializer(AdminUrlSerializerMixin, serializers.ModelSerializer):
    """Serialize one contextual Leave without autonomous Leave permissions."""

    type = EmployeeLeaveTypeV1Serializer(read_only=True)
    day_count = serializers.ReadOnlyField(source="dayCount")

    class Meta:
        model = Leave
        fields = (
            "id",
            "admin_url",
            "type",
            "start_date",
            "start_period",
            "end_date",
            "end_period",
            "day_count",
            "comment",
        )


class EmployeeLeaveWriteV1Serializer(serializers.ModelSerializer):
    type_id = serializers.PrimaryKeyRelatedField(source="type", queryset=Leave_Type.objects.all())
    start_date = serializers.DateField(required=True, allow_null=False)
    end_date = serializers.DateField(required=True, allow_null=False)

    class Meta:
        model = Leave
        fields = ("type_id", "start_date", "start_period", "end_date", "end_period", "comment")

    def validate(self, attrs):
        unexpected = set(self.initial_data) - set(self.fields)
        if unexpected:
            raise serializers.ValidationError({name: "This field is not accepted." for name in unexpected})
        return attrs

    def _save_validated(self, instance):
        with transaction.atomic():
            if connection.vendor == "postgresql":
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_xact_lock(%s, %s)", [291010, instance.employee_id])
            try:
                instance.full_clean()
            except DjangoValidationError as exc:
                details = exc.message_dict if hasattr(exc, "message_dict") else {"non_field_errors": exc.messages}
                if "__all__" in details:
                    details["non_field_errors"] = details.pop("__all__")
                raise serializers.ValidationError(details) from exc
            instance.save()
        return instance

    def create(self, validated_data):
        return self._save_validated(Leave(**validated_data))

    def update(self, instance, validated_data):
        for name, value in validated_data.items():
            setattr(instance, name, value)
        return self._save_validated(instance)
