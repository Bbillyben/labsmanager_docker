"""One public Organization result type backed by two legacy organization tables."""

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from common.preferences import visible_objects
from fund.models import Fund_Institution
from infos.models import OrganizationInfos, OrganizationInfosType
from project.models import Institution

from .contracts import SearchField, SearchProvider, SearchResult


FIELDS = (
    SearchField("name", _("Name"), ("name",), weight=100),
    SearchField("short_name", _("Abbreviation"), ("short_name",), weight=90),
    SearchField("generic_info", _("Additional information"), (), weight=45),
)


class _OrganizationSource(SearchProvider):
    key = "organization"
    icon = "Building2"
    fields = FIELDS
    supports_generic_info = True

    def __init__(self, model, kind, role):
        self.model = model
        self.kind = kind
        self.role = role

    def visible_queryset(self, user):
        return visible_objects(user, "institution" if self.kind == "institutions" else "fund_institution")

    def _content_type(self):
        return ContentType.objects.get_for_model(self.model)

    def _infos(self, **filters):
        return OrganizationInfos.objects.filter(content_type=self._content_type(), **filters)

    def field_query(self, search_field, term, lookup, user):
        if search_field.key == "generic_info":
            return Q(pk__in=self._infos(**{f"value__{lookup}": term}).values("object_id"))
        return super().field_query(search_field, term, lookup, user)

    def generic_info_query(self, type_name, value, user):
        return Q(pk__in=self._infos(info__name__iexact=type_name, value__iexact=value).values("object_id"))

    def prepare_candidates(self, candidates):
        if not candidates:
            return candidates
        by_object = {}
        infos = self._infos(object_id__in=[item.pk for item in candidates]).select_related("info")
        for info in infos:
            by_object.setdefault(info.object_id, []).append(info)
        for item in candidates:
            item.search_infos = by_object.get(item.pk, ())
        return candidates

    def search_values(self, obj, search_field, user):
        if search_field.key == "generic_info":
            return tuple((info.info.name, info.value or "") for info in obj.search_infos)
        return super().search_values(obj, search_field, user)

    def generic_info_values(self, obj, user):
        return tuple((info.info.name, info.value or "") for info in obj.search_infos)

    def make_result(self, obj, *, score, match_reason):
        return SearchResult(
            self.key, f"{self.kind}:{obj.pk}", obj.name, str(self.role),
            f"/app/organizations/{self.kind}/{obj.pk}", score, self.icon, match_reason,
            {"role": "institution" if self.kind == "institutions" else "funder"},
        )


class OrganizationSearchProvider(SearchProvider):
    key = "organization"
    label = _("Organizations")
    icon = "Building2"
    autocomplete = True
    supports_generic_info = True
    suggestable_fields = ("short_name",)
    fields = FIELDS

    def __init__(self):
        self.sources = (
            _OrganizationSource(Institution, "institutions", _("Institution")),
            _OrganizationSource(Fund_Institution, "funders", _("Funder")),
        )

    def available(self, user):
        return user.is_authenticated and user.has_perm("common.display_infos")

    def search_variants(self):
        return self.sources

    def suggest_provider_values(self, user, prefix, limit):
        values = {}
        for source in self.sources:
            for value in source.visible_queryset(user).filter(name__icontains=prefix).values_list("name", flat=True)[:limit]:
                values.setdefault(value.casefold(), value)
        return tuple(sorted(values.values(), key=lambda value: (not value.casefold().startswith(prefix.casefold()), value.casefold()))[:limit])

    def suggest_values(self, user, search_field, prefix, limit):
        if search_field.key != "short_name":
            return ()
        values = {}
        for source in self.sources:
            for value in source.visible_queryset(user).filter(short_name__icontains=prefix).values_list("short_name", flat=True)[:limit]:
                values.setdefault(value.casefold(), value)
        return tuple(sorted(values.values(), key=lambda value: (not value.casefold().startswith(prefix.casefold()), value.casefold()))[:limit])

    def suggest_generic_info_types(self, user, prefix, limit):
        if not self.available(user):
            return ()
        return tuple(OrganizationInfosType.objects.filter(name__icontains=prefix)
                     .order_by("name", "pk").values_list("name", flat=True)[:limit])
