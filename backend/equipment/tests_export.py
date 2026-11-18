"""Filtered Equipment XLSX export and import-shaped history checks."""

import tablib
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APITestCase

from project.models import Institution
from staff.models import Employee

from .models import Equipment, EquipmentCategory, EquipmentInstitutionInventory, EquipmentResponsibility
from .resources import EquipmentImportResource


class EquipmentExportTests(APITestCase):
    url = "/api/v1/equipment/export/"

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="equipment-exporter")
        self.category = EquipmentCategory.objects.create(name="Instruments")
        self.equipment = Equipment.objects.create(
            name="Microscope", internal_reference="EQ-1", category=self.category
        )
        self.other = Equipment.objects.create(
            name="Centrifuge", internal_reference="EQ-2", category=self.category,
            status=Equipment.Status.RETIRED,
        )
        self.employees = [
            Employee.objects.create(first_name="Alice", last_name="One"),
            Employee.objects.create(first_name="Bob", last_name="Two"),
            Employee.objects.create(first_name="Cara", last_name="Three"),
        ]
        self.institutions = [
            Institution.objects.create(name="University", short_name="UNI"),
            Institution.objects.create(name="Laboratory", short_name="LAB"),
        ]
        self.responsibilities = [
            EquipmentResponsibility.objects.create(
                equipment=self.equipment, employee=employee, start_date=f"202{index}-01-01"
            ) for index, employee in enumerate(self.employees, start=4)
        ]
        self.inventories = [
            EquipmentInstitutionInventory.objects.create(
                equipment=self.equipment, institution=institution,
                inventory_number=f"INV-{index}", start_date=f"202{index}-02-01",
            ) for index, institution in enumerate(self.institutions, start=4)
        ]
        self.grant(
            "equipment", "view_equipment", "view_equipmentresponsibility",
            "view_equipmentinstitutioninventory", "change_equipment",
            "change_equipmentresponsibility", "change_equipmentinstitutioninventory",
        )
        self.grant("staff", "view_employee")
        self.grant("project", "view_institution")
        self.client.force_login(self.user)

    def grant(self, app, *codes):
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label=app, codename__in=codes
        ))
        for key in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            self.user.__dict__.pop(key, None)

    def export(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("Equipment_", response["Content-Disposition"])
        return tablib.import_set(response.content, format="xlsx")

    def test_filters_ignore_pagination_and_export_matches_import_columns(self):
        dataset = self.export(search="EQ-1", category=self.category.pk, status="in_service",
                              limit=1, offset=100)
        self.assertEqual(dataset.headers, EquipmentImportResource().export(
            queryset=Equipment.objects.none()
        ).headers)
        self.assertEqual(len(dataset), 3)
        self.assertEqual({row["Internal reference"] for row in dataset.dict}, {"EQ-1"})
        self.assertEqual({row["Responsibility ID"] for row in dataset.dict},
                         {item.pk for item in self.responsibilities})
        self.assertEqual({row["Inventory ID"] for row in dataset.dict if row["Inventory ID"]},
                         {item.pk for item in self.inventories})
        self.assertEqual([row["Employee Name"] for row in dataset.dict],
                         [str(employee) for employee in self.employees])
        self.assertEqual(dataset.dict[0]["Institution Name"], "University")
        self.assertEqual(dataset.dict[2]["Inventory ID"], None)
        self.assertEqual(self.export(status="retired").dict[0]["Internal reference"], "EQ-2")

        # The same Resource accepts exported rows without creating duplicate children.
        result = EquipmentImportResource().import_data(dataset, dry_run=False, user=self.user)
        self.assertFalse(result.has_errors(), result.row_errors())
        self.assertFalse(result.has_validation_errors(), result.invalid_rows)
        self.assertEqual(EquipmentResponsibility.objects.count(), 3)
        self.assertEqual(EquipmentInstitutionInventory.objects.count(), 2)

    def test_export_omits_relations_without_their_visibility_permissions(self):
        self.user.user_permissions.clear()
        self.grant("equipment", "view_equipment")
        self.assertEqual(self.client.get(self.url).status_code, 200)
        rows = self.export(search="EQ-1").dict
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["Employee Name"])
        self.assertFalse(rows[0]["Institution Name"])

        self.grant("equipment", "view_equipmentresponsibility", "view_equipmentinstitutioninventory")
        rows = self.export(search="EQ-1").dict
        self.assertFalse(any(row["Employee Name"] for row in rows))
        self.assertFalse(any(row["Institution Name"] for row in rows))

        self.user.user_permissions.clear()
        self.assertEqual(self.client.get(self.url).status_code, 403)
