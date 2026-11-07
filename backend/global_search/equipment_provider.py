"""Search Equipment through the same permission-scoped contract as its API."""

from django.db.models import Prefetch, Q
from django.utils.translation import gettext_lazy as _

from .contracts import SearchField, SearchProvider, SearchResult


class EquipmentSearchProvider(SearchProvider):
    key = "equipment"
    label = _("Equipment")
    icon = "Microscope"
    autocomplete = True
    supports_generic_info = True
    suggestable_fields = ("reference", "category", "inventory")
    fields = (
        SearchField("name", _("Name"), ("name",), weight=100),
        SearchField("reference", _("Internal reference"), ("internal_reference",), weight=90),
        SearchField("category", _("Category"), ("category__name",), weight=60),
        SearchField("generic_info", _("Additional information"), (), weight=50),
        SearchField("inventory", _("Inventory number"), (), weight=55),
    )

    def available(self, user):
        return user.is_authenticated and user.has_perm("equipment.view_equipment")

    def visible_queryset(self, user):
        from equipment.api_v1 import visible_equipment
        from equipment.models import EquipmentGenericInfo, EquipmentInstitutionInventory

        return visible_equipment(user).select_related("category").prefetch_related(
            Prefetch("generic_info", queryset=EquipmentGenericInfo.objects.select_related("info"), to_attr="search_infos"),
            Prefetch("institution_inventories", queryset=EquipmentInstitutionInventory.objects.only("equipment_id", "inventory_number"), to_attr="search_inventories"),
        )

    def field_query(self, search_field, term, lookup, user):
        from equipment.models import EquipmentGenericInfo, EquipmentInstitutionInventory

        if search_field.key == "generic_info":
            matches = EquipmentGenericInfo.objects.filter(
                Q(**{f"value__{lookup}": term}) | Q(**{f"info__name__{lookup}": term})
            ).values("equipment_id")
            return Q(pk__in=matches)
        if search_field.key == "inventory":
            return Q(pk__in=EquipmentInstitutionInventory.objects.filter(
                **{f"inventory_number__{lookup}": term}
            ).values("equipment_id"))
        return super().field_query(search_field, term, lookup, user)

    def generic_info_query(self, type_name, value, user):
        from equipment.models import EquipmentGenericInfo

        return Q(pk__in=EquipmentGenericInfo.objects.filter(
            info__name__iexact=type_name, value__iexact=value
        ).values("equipment_id"))

    def generic_info_values(self, obj, user):
        return tuple((info.info.name, info.value or "") for info in obj.search_infos)

    def search_values(self, obj, search_field, user):
        if search_field.key == "category":
            return ((str(search_field.label), obj.category.name),)
        if search_field.key == "generic_info":
            return tuple((info.info.name, info.value or "") for info in obj.search_infos) + tuple(
                (str(search_field.label), info.info.name) for info in obj.search_infos
            )
        if search_field.key == "inventory":
            return tuple((str(search_field.label), item.inventory_number)
                         for item in obj.search_inventories if item.inventory_number)
        return super().search_values(obj, search_field, user)

    def suggestion_values(self, obj, search_field, user):
        if search_field.key == "inventory":
            return tuple(item.inventory_number for item in obj.search_inventories if item.inventory_number)
        return super().suggestion_values(obj, search_field, user)

    def suggest_generic_info_types(self, user, prefix, limit):
        from equipment.models import EquipmentGenericInfoType

        if not self.visible_queryset(user).exists():
            return ()
        return tuple(EquipmentGenericInfoType.objects.filter(name__icontains=prefix).order_by(
            "name", "pk"
        ).values_list("name", flat=True)[:limit])

    def make_result(self, obj, *, score, match_reason):
        return SearchResult(self.key, str(obj.pk), obj.name,
                            f"{obj.internal_reference} · {obj.category.name}",
                            f"/app/equipment/{obj.pk}", score, self.icon, match_reason)
