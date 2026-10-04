"""Employee and Project search axes, including their contextual information."""

from django.db.models import Prefetch, Q
from django.db.models import Value
from django.db.models.functions import Concat
from django.utils.translation import gettext_lazy as _

from .contracts import SearchField, SearchProvider, SearchResult
from .helpers import matching_parent_ids, person_values


class EmployeeSearchProvider(SearchProvider):
    key = "employee"
    label = _("Employees")
    icon = "UserRound"
    autocomplete = True
    supports_generic_info = True
    suggestable_fields = ("status",)
    fields = (
        SearchField("name", _("Name"), ("first_name", "last_name"), weight=100),
        SearchField("email", _("Email"), ("email",), weight=80),
        SearchField("status", _("Status"), (), weight=65),
        SearchField("generic_info", _("Additional information"), (), weight=45),
    )

    def visible_queryset(self, user):
        from staff.models import Employee, Employee_Status, GenericInfo
        return Employee.get_instances_for_user("view", user, Employee.objects.all()).prefetch_related(
            Prefetch("employee_status_set", queryset=Employee_Status.current.select_related("type"), to_attr="search_statuses"),
            Prefetch("genericinfo_set", queryset=GenericInfo.objects.select_related("info"), to_attr="search_infos"),
        )

    def field_query(self, search_field, term, lookup, user):
        from staff.models import Employee, Employee_Status, GenericInfo
        if search_field.key == "name":
            full = Employee.objects.annotate(search_full_name=Concat("first_name", Value(" "), "last_name"))
            return super().field_query(search_field, term, lookup, user) | Q(pk__in=full.filter(
                **{f"search_full_name__{lookup}": term}).values("pk"))
        if search_field.key == "status":
            return Q(pk__in=Employee_Status.current.filter(**{f"type__name__{lookup}": term}).values("employee_id"))
        if search_field.key == "generic_info":
            return Q(pk__in=GenericInfo.objects.filter(**{f"value__{lookup}": term}).values("employee_id"))
        return super().field_query(search_field, term, lookup, user)

    def generic_info_query(self, type_name, value, user):
        from staff.models import GenericInfo
        return Q(pk__in=GenericInfo.objects.filter(info__name__iexact=type_name, value__iexact=value).values("employee_id"))

    def generic_info_values(self, obj, user):
        return tuple((info.info.name, info.value or "") for info in obj.search_infos)

    def suggest_generic_info_types(self, user, prefix, limit):
        from staff.models import GenericInfoType
        return tuple(GenericInfoType.objects.filter(name__icontains=prefix).order_by("name", "pk").values_list("name", flat=True)[:limit])

    def suggestion_values(self, obj, search_field, user):
        if search_field.key == "name":
            return (str(obj),)
        return super().suggestion_values(obj, search_field, user)

    def search_values(self, obj, search_field, user):
        if search_field.key == "name":
            return tuple((str(search_field.label), value) for value in person_values(obj))
        if search_field.key == "status":
            return tuple((str(search_field.label), status.type.name) for status in obj.search_statuses)
        if search_field.key == "generic_info":
            return tuple((info.info.name, info.value or "") for info in obj.search_infos)
        return super().search_values(obj, search_field, user)

    def make_result(self, obj, *, score, match_reason):
        return SearchResult(self.key, str(obj.pk), str(obj), obj.email or "",
                            f"/app/employees/{obj.pk}", score, self.icon, match_reason)


class ProjectSearchProvider(SearchProvider):
    key = "project"
    label = _("Projects")
    icon = "FolderKanban"
    autocomplete = True
    supports_generic_info = True
    suggestable_fields = ("leader", "coleader", "participant", "institution")
    fields = (
        SearchField("name", _("Name"), ("name",), weight=100),
        SearchField("leader", _("Leader"), (), weight=65),
        SearchField("coleader", _("Co-leader"), (), weight=62),
        SearchField("participant", _("Participant"), (), weight=55),
        SearchField("institution", _("Institution"), (), weight=60),
        SearchField("generic_info", _("Additional information"), (), weight=45),
    )

    def visible_queryset(self, user):
        from project.models import GenericInfoProject, Institution_Participant, Participant, Project
        return Project.get_instances_for_user("view", user, Project.objects.all()).prefetch_related(
            Prefetch("participant_project", queryset=Participant.objects.select_related("employee"), to_attr="search_participants"),
            Prefetch("institution_participant_set", queryset=Institution_Participant.objects.select_related("institution"), to_attr="search_institutions"),
            Prefetch("genericinfoproject_set", queryset=GenericInfoProject.objects.select_related("info"), to_attr="search_infos"),
        )

    def field_query(self, search_field, term, lookup, user):
        from project.models import GenericInfoProject, Institution_Participant, Participant
        roles = {"leader": "l", "coleader": "cl", "participant": "p"}
        if search_field.key in roles:
            ids = matching_parent_ids(Participant, "project_id", ("employee__first_name", "employee__last_name"),
                                      term, lookup, status=roles[search_field.key])
            return Q(pk__in=ids)
        if search_field.key == "institution":
            ids = matching_parent_ids(Institution_Participant, "project_id", ("institution__short_name", "institution__name"), term, lookup)
            return Q(pk__in=ids)
        if search_field.key == "generic_info":
            return Q(pk__in=GenericInfoProject.objects.filter(**{f"value__{lookup}": term}).values("project_id"))
        return super().field_query(search_field, term, lookup, user)

    def generic_info_query(self, type_name, value, user):
        from project.models import GenericInfoProject
        return Q(pk__in=GenericInfoProject.objects.filter(info__name__iexact=type_name, value__iexact=value).values("project_id"))

    def generic_info_values(self, obj, user):
        return tuple((info.info.name, info.value or "") for info in obj.search_infos)

    def suggest_generic_info_types(self, user, prefix, limit):
        from project.models import GenericInfoTypeProject
        if not self.visible_queryset(user).exists():
            return ()
        return tuple(GenericInfoTypeProject.objects.filter(name__icontains=prefix).order_by("name", "pk").values_list("name", flat=True)[:limit])

    def suggestion_values(self, obj, search_field, user):
        roles = {"leader": "l", "coleader": "cl", "participant": "p"}
        if search_field.key in roles:
            return tuple(str(relation.employee) for relation in obj.search_participants
                         if relation.status == roles[search_field.key])
        return super().suggestion_values(obj, search_field, user)

    def search_values(self, obj, search_field, user):
        roles = {"leader": "l", "coleader": "cl", "participant": "p"}
        if search_field.key in roles:
            return tuple((str(search_field.label), value) for relation in obj.search_participants
                         if relation.status == roles[search_field.key] for value in person_values(relation.employee))
        if search_field.key == "institution":
            return tuple((str(search_field.label), value) for relation in obj.search_institutions
                         for value in (relation.institution.short_name, relation.institution.name))
        if search_field.key == "generic_info":
            return tuple((info.info.name, info.value or "") for info in obj.search_infos)
        return super().search_values(obj, search_field, user)

    def make_result(self, obj, *, score, match_reason):
        return SearchResult(self.key, str(obj.pk), obj.name, "",
                            f"/app/projects/{obj.pk}", score, self.icon, match_reason)


from .business_providers import FundSearchProvider, ContractSearchProvider, TeamSearchProvider  # noqa: E402

CORE_PROVIDERS = (EmployeeSearchProvider(), ProjectSearchProvider(), FundSearchProvider(),
                  ContractSearchProvider(), TeamSearchProvider())
