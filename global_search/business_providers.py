"""Fund, Contract and Team search over their existing visibility scopes."""

from django.db.models import Exists, OuterRef, Prefetch, Q
from django.db.models import Value
from django.db.models.functions import Concat
from django.utils.translation import gettext_lazy as _

from .contracts import SearchField, SearchProvider, SearchResult
from .helpers import matching_parent_ids, person_values


class FundSearchProvider(SearchProvider):
    key = "fund"
    label = _("Funds")
    icon = "PiggyBank"
    autocomplete = True
    suggestable_fields = ("funder", "manager")
    fields = (
        SearchField("reference", _("Reference"), ("ref",), weight=100),
        SearchField("funder", _("Funder"), ("funder__short_name", "funder__name"), weight=65),
        SearchField("manager", _("Manager"), ("institution__short_name", "institution__name"), weight=65),
    )

    def visible_queryset(self, user):
        from fund.financial_tools_api_v1 import visible_funds
        return visible_funds(user).select_related("project", "funder", "institution")

    def search_values(self, obj, search_field, user):
        if search_field.key in ("funder", "manager"):
            organization = obj.funder if search_field.key == "funder" else obj.institution
            return tuple((str(search_field.label), value) for value in (organization.short_name, organization.name))
        return super().search_values(obj, search_field, user)

    def make_result(self, obj, *, score, match_reason):
        title = obj.ref or f"{obj.funder.short_name} → {obj.institution.short_name}"
        return SearchResult(self.key, str(obj.pk), title, obj.project.name,
                            f"/app/projects/{obj.project_id}/funding#fund-row-{obj.pk}", score, self.icon, match_reason)


class ContractSearchProvider(SearchProvider):
    key = "contract"
    label = _("Contracts")
    icon = "FileSignature"
    autocomplete = True
    suggestable_fields = ("status",)
    fields = (
        SearchField("employee", _("Employee"), ("employee__first_name", "employee__last_name"), weight=85),
        SearchField("email", _("Employee email"), (), weight=70),
        SearchField("type", _("Contract type"), ("contract_type__name",), weight=75),
        SearchField("status", _("Status"), (), weight=45),
    )

    def visible_queryset(self, user):
        from expense.contract_hub_api_v1 import visible_contracts
        from staff.models import Employee
        visible_employees = Employee.get_instances_for_user("view", user, Employee.objects.all())
        return visible_contracts(user).select_related("employee", "contract_type", "fund__project").annotate(
            search_email_visible=Exists(visible_employees.filter(pk=OuterRef("employee_id")))
        )

    def field_query(self, search_field, term, lookup, user):
        from expense.models import Contract
        from staff.models import Employee
        if search_field.key == "email":
            visible = Employee.get_instances_for_user("view", user, Employee.objects.all())
            return Q(pk__in=Contract.objects.filter(employee_id__in=visible,
                    **{f"employee__email__{lookup}": term}).values("pk"))
        if search_field.key == "status":
            matching = [code for code, label in Contract.type_cont if term.casefold() in str(label).casefold()]
            return Q(status__in=matching)
        if search_field.key == "employee":
            full = Contract.objects.annotate(search_full_name=Concat(
                "employee__first_name", Value(" "), "employee__last_name"))
            return super().field_query(search_field, term, lookup, user) | Q(pk__in=full.filter(
                **{f"search_full_name__{lookup}": term}).values("pk"))
        return super().field_query(search_field, term, lookup, user)

    def search_values(self, obj, search_field, user):
        if search_field.key == "employee":
            return tuple((str(search_field.label), value) for value in person_values(obj.employee))
        if search_field.key == "email":
            return ((str(search_field.label), obj.employee.email or ""),) if obj.search_email_visible else ()
        if search_field.key == "type":
            return ((str(search_field.label), obj.contract_type.name),) if obj.contract_type else ()
        if search_field.key == "status":
            return ((str(search_field.label), str(obj.get_status_display())),)
        return super().search_values(obj, search_field, user)

    def suggestion_values(self, obj, search_field, user):
        if search_field.key == "employee":
            return (str(obj.employee),)
        return super().suggestion_values(obj, search_field, user)

    def make_result(self, obj, *, score, match_reason):
        title = f"{obj.employee} — {obj.contract_type.name if obj.contract_type else obj.get_status_display()}"
        return SearchResult(self.key, str(obj.pk), title, obj.fund.project.name,
                            f"/app/tools/contracts?employee={obj.employee_id}", score, self.icon, match_reason)


class TeamSearchProvider(SearchProvider):
    key = "team"
    label = _("Teams")
    icon = "UsersRound"
    autocomplete = True
    suggestable_fields = ("leader", "participant")
    fields = (
        SearchField("name", _("Name"), ("name",), weight=100),
        SearchField("leader", _("Leader"), ("leader__first_name", "leader__last_name"), weight=65),
        SearchField("participant", _("Participant"), (), weight=55),
    )

    def visible_queryset(self, user):
        from staff.models import TeamMate
        from staff.team_api_v1 import visible_teams
        return visible_teams(user).select_related("leader").prefetch_related(
            Prefetch("teammate_set", queryset=TeamMate.objects.select_related("employee"), to_attr="search_mates")
        )

    def field_query(self, search_field, term, lookup, user):
        from staff.models import TeamMate
        if search_field.key == "participant":
            ids = matching_parent_ids(TeamMate, "team_id", ("employee__first_name", "employee__last_name"), term, lookup)
            return Q(pk__in=ids)
        if search_field.key == "leader":
            from staff.models import Team
            full = Team.objects.annotate(search_full_name=Concat(
                "leader__first_name", Value(" "), "leader__last_name"))
            return super().field_query(search_field, term, lookup, user) | Q(pk__in=full.filter(
                **{f"search_full_name__{lookup}": term}).values("pk"))
        return super().field_query(search_field, term, lookup, user)

    def search_values(self, obj, search_field, user):
        if search_field.key == "leader":
            return tuple((str(search_field.label), value) for value in person_values(obj.leader))
        if search_field.key == "participant":
            return tuple((str(search_field.label), value) for relation in obj.search_mates
                         for value in person_values(relation.employee))
        return super().search_values(obj, search_field, user)

    def suggestion_values(self, obj, search_field, user):
        if search_field.key == "leader":
            return (str(obj.leader),) if obj.leader else ()
        if search_field.key == "participant":
            return tuple(str(relation.employee) for relation in obj.search_mates)
        return super().suggestion_values(obj, search_field, user)

    def make_result(self, obj, *, score, match_reason):
        return SearchResult(self.key, str(obj.pk), obj.name, "",
                            f"/app/teams/{obj.pk}", score, self.icon, match_reason)
