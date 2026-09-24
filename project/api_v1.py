"""Permission-scoped Project list and root-object mutations for React."""

from django.db import transaction
from django.db.models import Prefetch, Q
from django_filters import rest_framework as django_filters
from rest_framework import filters, generics, permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from fund.models import Fund, Fund_Institution
from labsmanager.pagination import LabPagination
from staff.models import Team, TeamMate

from .models import Institution, Institution_Participant, Participant, Project


def project_capabilities(user, project=None):
    return {
        "can_add": user.has_perm("project.add_project"),
        "can_change": bool(project and Project.get_instances_for_user("change", user, Project.objects.filter(pk=project.pk)).exists()),
        "can_delete": bool(project and user.has_perm("project.delete_project")),
    }


class ProjectListV1Serializer(serializers.ModelSerializer):
    institutions = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    funds = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ("id", "name", "start_date", "end_date", "status", "institutions", "participants", "funds", "capabilities")

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


class ProjectWriteV1Serializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ("id", "name", "start_date", "end_date", "status")
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
            Prefetch("fund_set", queryset=visible_funds.select_related("funder").order_by("funder__short_name", "ref", "pk"), to_attr="list_funds"),
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


class ProjectDetailV1View(ProjectV1QuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        return ProjectWriteV1Serializer if self.request.method in ("PATCH", "PUT") else ProjectListV1Serializer

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
