"""Permission-scoped Project list and root-object mutations for React."""

from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as django_filters
from rest_framework import filters, generics, permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from fund.models import Fund, Fund_Institution
from labsmanager.admin_links_v1 import AdminUrlSerializerMixin
from labsmanager.pagination import LabPagination
from labsmanager.list_export_v1 import ListExportContentNegotiation, export_list_queryset
from staff.models import Employee, Team, TeamMate
from reports.api_v1 import report_capabilities
from settings.api_v1 import can_change_project_settings

from .models import GenericInfoProject, GenericInfoTypeProject, Institution, Institution_Participant, Participant, Project
from .resources import ProjectResource


def project_capabilities(user, project=None):
    return {
        "can_add": user.has_perm("project.add_project"),
        "can_change": bool(project and Project.get_instances_for_user("change", user, Project.objects.filter(pk=project.pk)).exists()),
        "can_delete": bool(project and user.has_perm("project.delete_project")),
    }


def project_child_capabilities(user, project, model_name):
    """One authority for advertised child actions and mutation enforcement."""
    can_change_project = project_capabilities(user, project)["can_change"]
    prefix = f"project.{{}}_{model_name}"
    # Legacy Project actions grant leaders/co-leaders add/change. Deletion keeps
    # the explicit model permission, as for Project and its existing child UI.
    return {
        "can_add": can_change_project or user.has_perm(prefix.format("add")),
        "can_change": can_change_project or user.has_perm(prefix.format("change")),
        "can_delete": user.has_perm(prefix.format("delete")),
    }


def validate_model(instance):
    try:
        instance.full_clean()
    except DjangoValidationError as error:
        raise serializers.ValidationError(getattr(error, "message_dict", None) or error.messages) from error


class ProjectListV1Serializer(AdminUrlSerializerMixin, serializers.ModelSerializer):
    institutions = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    funds = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ("id", "admin_url", "name", "start_date", "end_date", "status", "institutions", "participants", "funds", "capabilities")

    def get_institutions(self, project):
        return [relation.institution.short_name for relation in project.list_institutions]

    def get_participants(self, project):
        return [str(relation.employee) for relation in project.list_participants]

    def get_funds(self, project):
        return [" · ".join(part for part in (fund.funder.short_name, fund.ref) if part) for fund in project.list_funds]

    def get_capabilities(self, project):
        if "change_project_ids" in self.context:
            user = self.context["request"].user
            return {
                "can_add": user.has_perm("project.add_project"),
                "can_change": project.pk in self.context["change_project_ids"],
                "can_delete": user.has_perm("project.delete_project"),
            }
        return project_capabilities(self.context["request"].user, project)


class ProjectWriteV1Serializer(AdminUrlSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ("id", "admin_url", "name", "start_date", "end_date", "status")
        read_only_fields = ("id",)

    def validate(self, attrs):
        instance = self.instance
        if instance and "name" in attrs and attrs["name"] != instance.name:
            raise serializers.ValidationError({"name": "Project name cannot be changed."})
        start = attrs.get("start_date", instance.start_date if instance else None)
        end = attrs.get("end_date", instance.end_date if instance else None)
        if end and (not start or end < start):
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})
        return attrs


class ProjectGenericInfoV1Serializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()

    class Meta:
        model = GenericInfoProject
        fields = ("id", "type", "value")

    def get_type(self, item):
        return {"id": item.info_id, "name": item.info.name, "icon": str(item.info.icon) if item.info.icon else None}


class ProjectInstitutionV1Serializer(serializers.ModelSerializer):
    institution = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Institution_Participant
        fields = ("id", "institution", "status", "status_label")

    def get_institution(self, item):
        return {"id": item.institution_id, "short_name": item.institution.short_name, "name": item.institution.name}


class ProjectParticipantV1Serializer(serializers.ModelSerializer):
    employee = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    quotity = serializers.DecimalField(max_digits=4, decimal_places=3, read_only=True)

    class Meta:
        model = Participant
        fields = ("id", "employee", "status", "status_label", "start_date", "end_date", "quotity", "is_active")

    def get_employee(self, item):
        employee = item.employee
        return {
            "id": employee.pk,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "is_active": employee.is_active,
            "can_view": employee.pk in self.context.get("visible_employee_ids", set()),
        }


class ProjectOverviewV1Serializer(AdminUrlSerializerMixin, serializers.ModelSerializer):
    capabilities = serializers.SerializerMethodField()
    funding_visible = serializers.SerializerMethodField()
    generic_info = serializers.SerializerMethodField()
    institutions = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ("id", "admin_url", "name", "start_date", "end_date", "status", "capabilities", "funding_visible", "generic_info", "institutions", "participants")

    def get_capabilities(self, project):
        user = self.context["request"].user
        return {
            **project_capabilities(user, project),
            **report_capabilities(user, "project", project),
            "can_change_settings": can_change_project_settings(user, project),
        }

    def get_funding_visible(self, project):
        user = self.context["request"].user
        return bool(user.has_perm("fund.view_fund") or user.has_perm("fund.view_fund", project))

    def child_collection(self, project, model_name, items, serializer):
        return {
            "capabilities": project_child_capabilities(self.context["request"].user, project, model_name),
            "items": serializer(items, many=True, context=self.context).data,
        }

    def get_generic_info(self, project):
        return self.child_collection(project, "genericinfoproject", project.overview_generic_info, ProjectGenericInfoV1Serializer)

    def get_institutions(self, project):
        return self.child_collection(project, "institution_participant", project.overview_institutions, ProjectInstitutionV1Serializer)

    def get_participants(self, project):
        return self.child_collection(project, "participant", project.overview_participants, ProjectParticipantV1Serializer)


class ContextualWriteSerializer(serializers.Serializer):
    """Reject parent substitution and unknown fields for Project-owned resources."""

    def to_internal_value(self, data):
        allowed = set(self.fields)
        if self.instance is not None:
            allowed -= self.immutable_on_update
        if isinstance(data, dict):
            unexpected = set(data) - allowed
            if unexpected:
                raise serializers.ValidationError({field: "This field cannot be supplied or changed." for field in sorted(unexpected)})
        return super().to_internal_value(data)

    immutable_on_update = frozenset()


class ProjectGenericInfoWriteV1Serializer(ContextualWriteSerializer):
    immutable_on_update = frozenset({"type_id"})
    type_id = serializers.PrimaryKeyRelatedField(source="info", queryset=GenericInfoTypeProject.objects.all())
    value = serializers.CharField(max_length=150, required=False, allow_blank=True, allow_null=True, trim_whitespace=False)

    def create(self, validated_data):
        item = GenericInfoProject(project=self.context["project"], **validated_data)
        validate_model(item)
        item.save()
        return item

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        validate_model(instance)
        instance.save()
        return instance


class ProjectInstitutionWriteV1Serializer(ContextualWriteSerializer):
    immutable_on_update = frozenset({"institution_id"})
    institution_id = serializers.PrimaryKeyRelatedField(source="institution", queryset=Institution.objects.all())
    status = serializers.ChoiceField(choices=Institution_Participant.type_part, required=False)

    def create(self, validated_data):
        item = Institution_Participant(project=self.context["project"], **validated_data)
        validate_model(item)
        item.save()
        return item

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        validate_model(instance)
        instance.save()
        return instance


class ProjectParticipantWriteV1Serializer(ContextualWriteSerializer):
    immutable_on_update = frozenset({"employee_id"})
    employee_id = serializers.PrimaryKeyRelatedField(source="employee", queryset=Employee.objects.all())
    status = serializers.ChoiceField(choices=Participant.type_part, required=False)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    quotity = serializers.DecimalField(max_digits=4, decimal_places=3, min_value=Decimal("0"), max_value=Decimal("1"))

    def validate(self, attrs):
        start = attrs.get("start_date", self.instance.start_date if self.instance else None)
        end = attrs.get("end_date", self.instance.end_date if self.instance else None)
        if end and (not start or end < start):
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})
        if self.instance is None:
            visible = Employee.get_instances_for_user("view", self.context["request"].user, Employee.objects.all())
            if not visible.filter(pk=attrs["employee"].pk).exists():
                raise serializers.ValidationError({"employee_id": "Employee is not available."})
        return attrs

    def create(self, validated_data):
        item = Participant(project=self.context["project"], **validated_data)
        validate_model(item)
        item.save()
        return item

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        validate_model(instance)
        instance.save()
        return instance


class ProjectListV1Filter(django_filters.FilterSet):
    project_name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")
    participant_name = django_filters.CharFilter(method="by_participant")
    participant = django_filters.NumberFilter(field_name="participant_project__employee_id", distinct=True)
    fundref = django_filters.CharFilter(method="by_fundref")
    funder = django_filters.NumberFilter(method="by_funder")
    institution_name = django_filters.NumberFilter(method="by_institution")
    team = django_filters.NumberFilter(method="by_team")
    stale = django_filters.BooleanFilter(method="by_stale")

    class Meta:
        model = Project
        fields = ("status", "name", "start_date", "end_date", "project_name", "participant_name", "participant", "fundref", "funder", "institution_name", "team", "stale")

    def by_participant(self, queryset, name, value):
        ids = Participant.objects.filter(Q(employee__first_name__icontains=value) | Q(employee__last_name__icontains=value)).values("project_id")
        return queryset.filter(pk__in=ids)

    def visible_funds(self, queryset):
        return Fund.get_instances_for_user("view", self.request.user, Fund.objects.filter(project__in=queryset))

    def by_fundref(self, queryset, name, value):
        return queryset.filter(pk__in=self.visible_funds(queryset).filter(ref__icontains=value).values("project_id"))

    def by_funder(self, queryset, name, value):
        return queryset.filter(pk__in=self.visible_funds(queryset).filter(funder_id=value).values("project_id"))

    def by_institution(self, queryset, name, value):
        partner_ids = Institution_Participant.objects.filter(institution_id=value).values("project_id")
        fund_ids = self.visible_funds(queryset).filter(institution_id=value).values("project_id")
        return queryset.filter(Q(pk__in=partner_ids) | Q(pk__in=fund_ids))

    def by_team(self, queryset, name, value):
        member_ids = TeamMate.objects.filter(team_id=value).values("employee_id")
        leader_ids = Team.objects.filter(pk=value).values("leader_id")
        project_ids = Participant.objects.filter(Q(employee_id__in=member_ids) | Q(employee_id__in=leader_ids)).values("project_id")
        return queryset.filter(pk__in=project_ids)

    def by_stale(self, queryset, name, value):
        return queryset.filter(Project.staleFilter()) if value else queryset.exclude(Project.staleFilter())


class ProjectV1QuerysetMixin:
    def get_queryset(self):
        visible = Project.get_instances_for_user("view", self.request.user, Project.objects.all())
        visible_funds = Fund.get_instances_for_user("view", self.request.user, Fund.objects.all())
        return visible.prefetch_related(
            Prefetch("institution_participant_set", queryset=Institution_Participant.objects.select_related("institution").order_by("institution__short_name", "pk"), to_attr="list_institutions"),
            Prefetch("participant_project", queryset=Participant.objects.select_related("employee").filter(employee__is_active=True).order_by("employee__last_name", "employee__first_name", "pk"), to_attr="list_participants"),
            Prefetch("fund_set", queryset=visible_funds.select_related("funder", "institution").order_by("funder__short_name", "ref", "pk"), to_attr="list_funds"),
        )


class ProjectListV1View(ProjectV1QuerysetMixin, generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = LabPagination
    filter_backends = (django_filters.DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = ProjectListV1Filter
    search_fields = ("name", "participant_project__employee__first_name", "participant_project__employee__last_name", "institution_participant__institution__name")
    ordering_fields = ("name", "start_date", "end_date", "status")
    ordering = ("name", "pk")

    def get_serializer_class(self):
        return ProjectWriteV1Serializer if self.request.method == "POST" else ProjectListV1Serializer

    def get_queryset(self):
        return super().get_queryset().distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        projects = page if page is not None else list(queryset)
        ids = [project.pk for project in projects]
        change_ids = set(Project.get_instances_for_user("change", request.user, Project.objects.filter(pk__in=ids)).values_list("pk", flat=True)) if ids else set()
        context = {**self.get_serializer_context(), "change_project_ids": change_ids}
        data = self.get_serializer(projects, many=True, context=context).data
        return self.get_paginated_response(data) if page is not None else Response(data)

    @transaction.atomic
    def perform_create(self, serializer):
        if not project_capabilities(self.request.user)["can_add"]:
            raise PermissionDenied()
        project = serializer.save()
        if not self.request.user.has_perm("project.change_project"):
            employee = getattr(self.request.user, "employee", None)
            if employee is None:
                from staff.models import Employee
                employee = Employee.objects.filter(user=self.request.user).first()
            if employee is not None:
                Participant.objects.create(project=project, employee=employee, status="l")


class ProjectListExportV1View(ProjectListV1View):
    """Export the list's scoped filters and ordering before pagination."""

    http_method_names = ("get", "head", "options")
    content_negotiation_class = ListExportContentNegotiation

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return export_list_queryset(request, queryset, ProjectResource, "Project", resource_kwargs={"fund_scope": "visible"})


class ProjectDetailV1View(ProjectV1QuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        return ProjectWriteV1Serializer if self.request.method in ("PATCH", "PUT") else ProjectOverviewV1Serializer

    def get_queryset(self):
        if self.request.method != "GET":
            return Project.get_instances_for_user("view", self.request.user, Project.objects.all())
        return Project.get_instances_for_user("view", self.request.user, Project.objects.all()).prefetch_related(
            Prefetch("genericinfoproject_set", queryset=GenericInfoProject.objects.select_related("info").order_by("info__name", "pk"), to_attr="overview_generic_info"),
            Prefetch("institution_participant_set", queryset=Institution_Participant.objects.select_related("institution").order_by("institution__short_name", "pk"), to_attr="overview_institutions"),
            Prefetch("participant_project", queryset=Participant.objects.select_related("employee").order_by("employee__last_name", "employee__first_name", "pk"), to_attr="overview_participants"),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method == "GET":
            context["visible_employee_ids"] = set(Employee.get_instances_for_user(
                "view", self.request.user, Employee.objects.all()
            ).values_list("pk", flat=True))
        return context

    def perform_update(self, serializer):
        if not project_capabilities(self.request.user, serializer.instance)["can_change"]:
            raise PermissionDenied()
        serializer.save()

    def perform_destroy(self, instance):
        if not project_capabilities(self.request.user, instance)["can_delete"]:
            raise PermissionDenied()
        instance.delete()


class ProjectCapabilitiesV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response(project_capabilities(request.user))


class ProjectFilterOptionsV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        projects = Project.get_instances_for_user("view", request.user, Project.objects.all())
        funds = Fund.get_instances_for_user("view", request.user, Fund.objects.filter(project__in=projects))
        return Response({
            "funders": list(Fund_Institution.objects.filter(fund__in=funds).distinct().order_by("short_name").values("id", "short_name")),
            "institutions": list(Institution.objects.filter(Q(institution_participant__project__in=projects) | Q(fund__in=funds)).distinct().order_by("short_name").values("id", "short_name")),
            "teams": list(Team.objects.filter(Q(teammate__employee__participant_employee__project__in=projects) | Q(leader__participant_employee__project__in=projects)).distinct().order_by("name").values("id", "name")),
        })


class ProjectOverviewChildMixin:
    permission_classes = (permissions.IsAuthenticated,)
    model = None
    model_name = ""
    write_serializer = None
    read_serializer = None
    related = ""
    item_kwarg = "item_id"

    def get_project(self):
        if not hasattr(self, "_project"):
            visible = Project.get_instances_for_user("view", self.request.user, Project.objects.all())
            self._project = get_object_or_404(visible, pk=self.kwargs["pk"])
        return self._project

    def get_queryset(self):
        return self.model.objects.filter(project=self.get_project()).select_related(self.related).order_by("pk")

    def get_item(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs[self.item_kwarg])

    def capabilities(self):
        return project_child_capabilities(self.request.user, self.get_project(), self.model_name)

    def require_action(self, action):
        if not self.capabilities()[action]:
            raise PermissionDenied()

    def serializer_context(self):
        context = {"request": self.request, "project": self.get_project()}
        if self.model_name == "participant":
            context["visible_employee_ids"] = set(Employee.get_instances_for_user(
                "view", self.request.user, Employee.objects.all()
            ).values_list("pk", flat=True))
        return context

    def read(self, item):
        return self.read_serializer(item, context=self.serializer_context()).data


class ProjectOverviewChildCollectionV1View(ProjectOverviewChildMixin, APIView):
    def get(self, request, *args, **kwargs):
        return Response({
            "capabilities": self.capabilities(),
            "items": self.read_serializer(self.get_queryset(), many=True, context=self.serializer_context()).data,
        })

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        self.require_action("can_add")
        serializer = self.write_serializer(data=request.data, context=self.serializer_context())
        serializer.is_valid(raise_exception=True)
        return Response(self.read(serializer.save()), status=201)


class ProjectOverviewChildDetailV1View(ProjectOverviewChildMixin, APIView):
    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        item = self.get_item()
        self.require_action("can_change")
        serializer = self.write_serializer(item, data=request.data, partial=True, context=self.serializer_context())
        serializer.is_valid(raise_exception=True)
        return Response(self.read(serializer.save()))

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        item = self.get_item()
        self.require_action("can_delete")
        item.delete()
        return Response(status=204)


PROJECT_OVERVIEW_RESOURCES = {
    "generic-info": (GenericInfoProject, "genericinfoproject", ProjectGenericInfoWriteV1Serializer, ProjectGenericInfoV1Serializer, "info"),
    "institutions": (Institution_Participant, "institution_participant", ProjectInstitutionWriteV1Serializer, ProjectInstitutionV1Serializer, "institution"),
    "participants": (Participant, "participant", ProjectParticipantWriteV1Serializer, ProjectParticipantV1Serializer, "employee"),
}


def project_child_view(resource, detail=False):
    model, model_name, write_serializer, read_serializer, related = PROJECT_OVERVIEW_RESOURCES[resource]
    base = ProjectOverviewChildDetailV1View if detail else ProjectOverviewChildCollectionV1View
    return base.as_view(model=model, model_name=model_name, write_serializer=write_serializer, read_serializer=read_serializer, related=related)


class ProjectOverviewOptionsV1View(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        visible = Project.get_instances_for_user("view", request.user, Project.objects.all())
        get_object_or_404(visible, pk=pk)
        return Response({
            "generic_info_types": [
                {"id": item.pk, "name": item.name, "icon": str(item.icon) if item.icon else None}
                for item in GenericInfoTypeProject.objects.order_by("name", "pk")
            ],
            "institutions": list(Institution.objects.order_by("short_name", "pk").values("id", "short_name", "name")),
        })
