"""Shared Planning read contract for Employee and future Project scopes."""

from rest_framework import serializers
from labsmanager.admin_links_v1 import get_admin_change_url
from django.core.exceptions import ValidationError as DjangoValidationError
from project.models import Participant
from staff.models import Employee

from .models import Milestones, effective_start_date


class PlanningMilestoneV1Serializer(serializers.ModelSerializer):
    """Serialize Planning items for an authorized contextual scope."""

    admin_url = serializers.SerializerMethodField()
    display_state = serializers.SerializerMethodField()
    days_to_due = serializers.SerializerMethodField()
    work_kind = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    employees = serializers.SerializerMethodField()
    dependencies = serializers.SerializerMethodField()

    class Meta:
        model = Milestones
        fields = (
            "id",
            "admin_url",
            "name",
            "desc",
            "start_date",
            "end_date",
            "status",
            "type",
            "quotity",
            "display_state",
            "days_to_due",
            "work_kind",
            "project",
            "employees",
            "dependencies",
        )

    def get_admin_url(self, milestone):
        return get_admin_change_url(self.context.get("user"), milestone)

    def get_display_state(self, milestone):
        """Classify attention state using the viewer's configured threshold."""
        today = self.context["today"]
        if milestone.status is True:
            return "completed"
        if milestone.end_date and milestone.end_date < today:
            return "overdue"
        if (
            milestone.end_date
            and milestone.end_date <= today + self.context["stale_delta"]
        ):
            return "due_soon"
        if milestone.start_date and milestone.start_date > today:
            return "planned"
        return "in_progress"

    def get_days_to_due(self, milestone):
        """Return signed calendar days to the deadline, when one exists."""
        if milestone.end_date is None:
            return None
        return (milestone.end_date - self.context["today"]).days

    def get_work_kind(self, milestone):
        return "milestone" if milestone.start_date is None else "task"

    def get_project(self, milestone):
        return {
            "id": milestone.project_id,
            "name": milestone.project.name,
            "can_view": milestone.project_id in self.context["visible_project_ids"],
        }

    def get_employees(self, milestone):
        visible_ids = self.context["visible_employee_ids"]
        return [
            {
                "id": employee.pk,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "can_view": employee.pk in visible_ids,
            }
            for employee in milestone.employee.all()
        ]

    def get_dependencies(self, milestone):
        visible_ids = self.context["visible_work_ids"]
        successor_start = effective_start_date(milestone)
        return [{
            "id": relation.pk,
            "predecessor_id": relation.predecessor_id,
            "successor_id": milestone.pk,
            "temporally_inconsistent": bool(
                successor_start
                and effective_start_date(relation.predecessor)
                and successor_start < effective_start_date(relation.predecessor)
            ),
        } for relation in milestone.visible_dependencies
            if relation.predecessor_id in visible_ids]


class EmployeePlanningMilestoneV1Serializer(PlanningMilestoneV1Serializer):
    """Add the logged-in user's limited Employee-context edit capability."""

    can_change = serializers.SerializerMethodField()

    class Meta(PlanningMilestoneV1Serializer.Meta):
        fields = PlanningMilestoneV1Serializer.Meta.fields + ("can_change",)

    def get_can_change(self, milestone):
        return self.context["request"].user.has_perm("endpoints.change_milestones", milestone)


def cohere_planning_progress(attrs, instance):
    """Preserve the existing Project Planning completion/status behavior."""
    if attrs.get("status", instance.status if instance else False):
        attrs["quotity"] = 1
    elif attrs.get("quotity", instance.quotity if instance else 0) == 1:
        attrs["status"] = True
    return attrs


class PlanningMilestoneWriteV1Serializer(serializers.ModelSerializer):
    """Write a Project-scoped Task or Milestone with participant-only assignees."""

    work_kind = serializers.ChoiceField(choices=("task", "milestone"), write_only=True)
    employee_ids = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), many=True, write_only=True, required=False,
    )

    class Meta:
        model = Milestones
        fields = (
            "id", "name", "desc", "start_date", "end_date", "type", "quotity",
            "status", "work_kind", "employee_ids",
        )
        read_only_fields = ("id",)

    def validate(self, attrs):
        kind = attrs.get("work_kind")
        start = attrs.get("start_date", self.instance.start_date if self.instance else None)
        if kind == "task" and start is None:
            raise serializers.ValidationError({"start_date": "A task requires a start date."})
        if kind == "milestone":
            if "start_date" in attrs and attrs["start_date"] is not None:
                raise serializers.ValidationError({"start_date": "A milestone cannot have a start date."})
            attrs["start_date"] = None
        employees = attrs.get("employee_ids")
        if employees is not None:
            allowed = set(Participant.objects.filter(
                project=self.context["project"], employee_id__in=[employee.pk for employee in employees],
            ).values_list("employee_id", flat=True))
            if any(employee.pk not in allowed for employee in employees):
                raise serializers.ValidationError({"employee_ids": "Assignees must participate in this Project."})
        return cohere_planning_progress(attrs, self.instance)

    def create(self, validated_data):
        employees = validated_data.pop("employee_ids", [])
        validated_data.pop("work_kind")
        item = Milestones(project=self.context["project"], **validated_data)
        self._validate_model(item)
        item.save()
        item.employee.set(employees)
        return item

    def update(self, instance, validated_data):
        employees = validated_data.pop("employee_ids", None)
        validated_data.pop("work_kind")
        for key, value in validated_data.items():
            setattr(instance, key, value)
        self._validate_model(instance)
        instance.save()
        if employees is not None:
            instance.employee.set(employees)
        return instance

    @staticmethod
    def _validate_model(item):
        try:
            item.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(getattr(error, "message_dict", None) or error.messages) from error


class EmployeeMilestonePartialWriteV1Serializer(serializers.ModelSerializer):
    """Accept only the three Employee-context fields, even for Project owners."""

    class Meta:
        model = Milestones
        fields = ("desc", "quotity", "status")

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("An object is required.")
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({key: "This field cannot be changed from Employee Planning." for key in sorted(unknown)})
        return super().to_internal_value(data)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one editable field is required.")
        return cohere_planning_progress(attrs, self.instance)

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        PlanningMilestoneWriteV1Serializer._validate_model(instance)
        instance.save()
        return instance
