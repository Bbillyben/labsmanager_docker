"""Equipment import through the shared django-import-export workflow."""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import tablib
from import_export import fields, widgets

from labsmanager.ressources import labResource
from project.models import Institution
from staff.models import Employee

from .models import (
    Equipment, EquipmentCategory, EquipmentInstitutionInventory,
    EquipmentResponsibility,
)


class EquipmentImportResource(labResource):
    """Import one Equipment and optionally one of each dated relation per row.

    Repeated internal references allow multiple relations in one selected sheet.
    A relation ID resolves edits explicitly; otherwise its stable business key is
    used. Ambiguous keys are rejected instead of overwriting arbitrary history.
    """

    internal_reference = fields.Field(attribute="internal_reference", column_name="Internal reference")
    name = fields.Field(attribute="name", column_name="Name")
    category = fields.Field(
        attribute="category", column_name="Category",
        widget=widgets.ForeignKeyWidget(EquipmentCategory, field="name"),
    )
    status = fields.Field(attribute="status", column_name="Status")
    acquisition_date = fields.Field(
        attribute="acquisition_date", column_name="Acquisition date", widget=widgets.DateWidget(),
    )
    commissioning_date = fields.Field(
        attribute="commissioning_date", column_name="Commissioning date", widget=widgets.DateWidget(),
    )
    decommissioning_date = fields.Field(
        attribute="decommissioning_date", column_name="Decommissioning date", widget=widgets.DateWidget(),
    )
    responsibility_id = fields.Field(column_name="Responsibility ID", readonly=True)
    employee_name = fields.Field(column_name="Employee Name", readonly=True)
    responsibility_start = fields.Field(column_name="Responsibility start", readonly=True)
    responsibility_end = fields.Field(column_name="Responsibility end", readonly=True)
    inventory_id = fields.Field(column_name="Inventory ID", readonly=True)
    institution_name = fields.Field(column_name="Institution Name", readonly=True)
    inventory_number = fields.Field(column_name="Inventory number", readonly=True)
    inventory_status = fields.Field(column_name="Inventory status", readonly=True)
    inventory_start = fields.Field(column_name="Inventory start", readonly=True)
    inventory_end = fields.Field(column_name="Inventory end", readonly=True)

    class Meta:
        model = Equipment
        fields = (
            "internal_reference", "name", "category", "status", "acquisition_date",
            "commissioning_date", "decommissioning_date", "responsibility_id",
            "employee_name", "responsibility_start", "responsibility_end", "inventory_id",
            "institution_name", "inventory_number", "inventory_status", "inventory_start",
            "inventory_end",
        )
        import_id_fields = ("internal_reference",)
        clean_model_instances = True
        store_instance = True
        use_transactions = True

    def before_import(self, dataset, using_transactions, dry_run, **kwargs):
        """Reject incomplete or contradictory parent rows before any write."""
        obsolete = {"Employee ID", "Institution ID"} & set(dataset.headers or ())
        if obsolete:
            raise ValidationError(_("Use Employee Name and Institution Name instead of ID columns."))
        parent_columns = (
            "Internal reference", "Name", "Category", "Status", "Acquisition date",
            "Commissioning date", "Decommissioning date",
        )
        missing = set(parent_columns) - set(dataset.headers or ())
        if missing:
            raise ValidationError(_("Missing Equipment columns: %(columns)s") % {
                "columns": ", ".join(sorted(missing)),
            })
        seen = {}
        for row in dataset.dict:
            if any(not self._value(row, column) for column in parent_columns[:4]):
                raise ValidationError(_("Internal reference, name, category and status are required on every row."))
            reference = self._value(row, "Internal reference")
            values = tuple(self._value(row, column) for column in parent_columns[1:])
            if reference in seen and seen[reference] != values:
                raise ValidationError(_("Conflicting Equipment values for internal reference %(reference)s.") % {
                    "reference": reference,
                })
            seen[reference] = values

    def after_import_instance(self, instance, new, **kwargs):
        """Apply the same parent create/change permissions as the Equipment API."""
        user = kwargs["user"]
        permission = "equipment.add_equipment" if new else "equipment.change_equipment"
        if not user.has_perm(permission):
            raise ValidationError(_("Equipment write permission is required."))

    @staticmethod
    def _value(row, column):
        value = row.get(column)
        return "" if value is None else str(value).strip()

    @classmethod
    def _identifier(cls, row, column):
        value = cls._value(row, column)
        if not value:
            return None
        try:
            identifier = int(value)
        except ValueError as error:
            raise ValidationError({column: _("Enter a valid integer ID.")}) from error
        if identifier <= 0:
            raise ValidationError({column: _("Enter a valid integer ID.")})
        return identifier

    @staticmethod
    def _normalize_name(value):
        """Normalize case and whitespace without fuzzy matching."""
        return " ".join(str(value).split()).casefold()

    def _employee_candidates(self, name):
        if not hasattr(self, "_employee_names"):
            self._employee_names = {}
            for identifier, first_name, last_name in Employee.objects.values_list(
                "pk", "first_name", "last_name"
            ):
                key = self._normalize_name(f"{first_name} {last_name}")
                self._employee_names.setdefault(key, set()).add(identifier)
        return self._employee_names.get(self._normalize_name(name), set())

    def _institution_candidates(self, name):
        if not hasattr(self, "_institution_names"):
            self._institution_names = {}
            for identifier, long_name, short_name in Institution.objects.values_list(
                "pk", "name", "short_name"
            ):
                for value in (long_name, short_name):
                    key = self._normalize_name(value)
                    self._institution_names.setdefault(key, set()).add(identifier)
        return self._institution_names.get(self._normalize_name(name), set())

    def _resolve_name(self, row, column, candidates, equipment, relation_id, model, identity_field):
        """Use a relation ID to disambiguate an existing named association."""
        name = self._value(row, column)
        if not name or not candidates:
            raise ValidationError({column: _("No matching name was found.")})
        if len(candidates) == 1:
            return next(iter(candidates))
        if relation_id is not None:
            linked_id = model.objects.filter(equipment=equipment, pk=relation_id).values_list(
                identity_field, flat=True
            ).first()
            if linked_id in candidates:
                return linked_id
        raise ValidationError({column: _("Ambiguous name; provide the existing relation ID.")})

    @classmethod
    def _date(cls, row, column):
        value = row.get(column)
        if value in (None, ""):
            return None
        try:
            return widgets.DateWidget().clean(value)
        except (ValueError, TypeError) as error:
            raise ValidationError({column: _("Enter a valid date.")}) from error

    @staticmethod
    def _relation(instance, model, explicit_id, identity, permission_stem, user):
        """Resolve a child by ID or unique business key, never by row order."""
        candidates = model.objects.filter(equipment=instance)
        if explicit_id is not None:
            child = candidates.filter(pk=explicit_id).first()
            if child is None:
                raise ValidationError(_("Relation ID does not belong to this Equipment."))
            identity_field = "employee_id" if model is EquipmentResponsibility else "institution_id"
            if getattr(child, identity_field) != identity[identity_field]:
                raise ValidationError(_("A relation's Employee or Institution cannot be changed."))
            action = "change"
        else:
            matches = list(candidates.filter(**identity)[:2])
            if len(matches) > 1:
                raise ValidationError(_("Ambiguous relation: provide its ID."))
            child = matches[0] if matches else model(equipment=instance)
            action = "change" if matches else "add"
        if not user.has_perm("equipment.change_equipment") or not user.has_perm(
            f"equipment.{action}_{permission_stem}"
        ):
            raise ValidationError(_("Equipment relation write permission is required."))
        return child

    def _responsibility(self, row, equipment, user):
        columns = ("Responsibility ID", "Employee Name", "Responsibility start", "Responsibility end")
        if not any(self._value(row, column) for column in columns):
            return
        relation_id = self._identifier(row, "Responsibility ID")
        employee_id = self._resolve_name(
            row, "Employee Name", self._employee_candidates(self._value(row, "Employee Name")),
            equipment, relation_id, EquipmentResponsibility, "employee_id",
        )
        if not Employee.get_instances_for_user(
            "view", user, Employee.objects.filter(pk=employee_id)
        ).exists():
            raise ValidationError({"Employee Name": _("Employee is not available.")})
        start = self._date(row, "Responsibility start")
        child = self._relation(
            equipment, EquipmentResponsibility, relation_id,
            {"employee_id": employee_id, "start_date": start}, "equipmentresponsibility", user,
        )
        end = self._date(row, "Responsibility end")
        changed = child.pk is None or (child.employee_id, child.start_date, child.end_date) != (
            employee_id, start, end,
        )
        child.employee_id = employee_id
        child.start_date = start
        child.end_date = end
        child.full_clean()
        if changed:
            child.save()

    def _inventory(self, row, equipment, user):
        columns = (
            "Inventory ID", "Institution Name", "Inventory number", "Inventory status",
            "Inventory start", "Inventory end",
        )
        if not any(self._value(row, column) for column in columns):
            return
        if not (
            user.has_perm("common.display_infos") or user.has_perm("project.view_institution")
        ):
            raise ValidationError({"Institution Name": _("Institution is not available.")})
        relation_id = self._identifier(row, "Inventory ID")
        institution_id = self._resolve_name(
            row, "Institution Name", self._institution_candidates(self._value(row, "Institution Name")),
            equipment, relation_id, EquipmentInstitutionInventory, "institution_id",
        )
        start = self._date(row, "Inventory start")
        number = self._value(row, "Inventory number")
        child = self._relation(
            equipment, EquipmentInstitutionInventory, relation_id,
            {"institution_id": institution_id, "start_date": start, "inventory_number": number},
            "equipmentinstitutioninventory", user,
        )
        end = self._date(row, "Inventory end")
        status = self._value(row, "Inventory status") or (
            child.status if child.pk else EquipmentInstitutionInventory.Status.REGISTERED
        )
        changed = child.pk is None or (
            child.institution_id, child.start_date, child.end_date,
            child.inventory_number, child.status,
        ) != (institution_id, start, end, number, status)
        child.institution_id = institution_id
        child.start_date = start
        child.end_date = end
        child.inventory_number = number
        child.status = status
        child.full_clean()
        if changed:
            child.save()

    def after_import_row(self, row, row_result, **kwargs):
        """Write children inside the Resource's preview/commit transaction."""
        equipment = row_result.instance
        self._responsibility(row, equipment, kwargs["user"])
        self._inventory(row, equipment, kwargs["user"])


class EquipmentExportResource(EquipmentImportResource):
    """Export import-shaped rows without multiplying the two independent histories."""

    @staticmethod
    def _safe_text(value):
        # Apply the same spreadsheet formula guard as labResource.export_resource.
        return str(value).strip().lstrip("@=+-\t\r\n")

    def export(self, queryset=None, **kwargs):
        dataset = tablib.Dataset(headers=self.get_export_headers())
        for equipment in queryset:
            responsibilities = getattr(equipment, "export_responsibilities", ())
            inventories = getattr(equipment, "export_inventories", ())
            for index in range(max(len(responsibilities), len(inventories), 1)):
                row = super().export_resource(equipment)
                if index < len(responsibilities):
                    relation = responsibilities[index]
                    row[7:11] = (
                        relation.pk,
                        self._safe_text(f"{relation.employee.first_name} {relation.employee.last_name}"),
                        relation.start_date.isoformat() if relation.start_date else "",
                        relation.end_date.isoformat() if relation.end_date else "",
                    )
                if index < len(inventories):
                    relation = inventories[index]
                    name = relation.institution.name
                    if len(self._institution_candidates(name)) != 1:
                        short_name = relation.institution.short_name
                        if len(self._institution_candidates(short_name)) == 1:
                            name = short_name
                    row[11:17] = (
                        relation.pk, self._safe_text(name),
                        self._safe_text(relation.inventory_number), relation.status,
                        relation.start_date.isoformat() if relation.start_date else "",
                        relation.end_date.isoformat() if relation.end_date else "",
                    )
                dataset.append(row)
        return dataset
