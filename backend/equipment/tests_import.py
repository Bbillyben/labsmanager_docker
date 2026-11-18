"""Focused Equipment import workflow checks."""

import csv
from io import StringIO

import tablib
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase

from project.models import Institution
from staff.models import Employee

from .models import Equipment, EquipmentCategory, EquipmentInstitutionInventory, EquipmentResponsibility
from .resources import EquipmentImportResource


class EquipmentImportTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="equipment-importer")
        self.employee = Employee.objects.create(first_name="Alice", last_name="One")
        self.other_employee = Employee.objects.create(first_name="Élodie", last_name="Dupont")
        self.institution = Institution.objects.create(short_name="UNI", name="University")
        self.other_institution = Institution.objects.create(short_name="LAB", name="Laboratory")
        self.category = EquipmentCategory.objects.create(name="Instruments")
        for app, codes in (
            ("common", ("import", "display_infos")),
            ("staff", ("view_employee",)),
            ("equipment", (
                "view_equipment", "add_equipment", "change_equipment",
                "add_equipmentresponsibility", "change_equipmentresponsibility",
                "add_equipmentinstitutioninventory", "change_equipmentinstitutioninventory",
            )),
        ):
            for code in codes:
                self.grant(app, code)
        self.refresh_user()

    def grant(self, app, code):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=code))

    def refresh_user(self):
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_login(self.user)

    @staticmethod
    def url(action):
        return reverse(f"api_v1:import-{action}", kwargs={"profile": "equipment"})

    def upload_preview(self, rows):
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=EquipmentImportResource().export(
            queryset=Equipment.objects.none()
        ).headers)
        writer.writeheader()
        writer.writerows(rows)
        upload = self.client.post(
            self.url("upload"), {"file": SimpleUploadedFile("equipment.csv", output.getvalue().encode())},
            format="multipart",
        )
        self.assertEqual(upload.status_code, 200, upload.data)
        preview = self.client.post(
            self.url("preview"), {"import_token": upload.data["import_token"], "sheet": ""}, format="json",
        )
        self.assertEqual(preview.status_code, 200, preview.data)
        return preview

    def row(self, reference="EQ-1", **overrides):
        return {
            "Internal reference": reference, "Name": "Microscope", "Category": self.category.name,
            "Status": "in_service", **overrides,
        }

    def test_create_update_multiple_relations_and_idempotent_reimport(self):
        rows = [
            self.row(**{"Employee Name": "  alice   one  ", "Responsibility start": "2026-01-01",
                        "Institution Name": " university ", "Inventory number": "INV-1",
                        "Inventory status": "registered", "Inventory start": "2026-01-01"}),
            self.row(**{"Employee Name": "éLODIE DUPONT", "Responsibility start": "2026-02-01",
                        "Institution Name": " lab ", "Inventory number": "INV-2",
                        "Inventory status": "closed", "Inventory start": "2026-02-01"}),
        ]
        template = self.client.get(self.url("template"))
        self.assertEqual(template.status_code, 200)
        headers = tablib.import_set(template.content, format="xlsx").headers
        self.assertIn("Internal reference", headers)
        self.assertIn("Employee Name", headers)
        self.assertIn("Institution Name", headers)
        self.assertNotIn("Employee ID", headers)
        self.assertNotIn("Institution ID", headers)
        self.assertIn("equipment", {profile["key"] for profile in self.client.get(reverse("api_v1:import-profiles")).data["items"]})
        for expected in ("new", "update"):
            preview = self.upload_preview(rows)
            self.assertTrue(preview.data["can_commit"], preview.data)
            self.assertEqual(Equipment.objects.count(), 0 if expected == "new" else 1)
            result = self.client.post(self.url("commit"), {"import_token": preview.data["import_token"]}, format="json")
            self.assertEqual(result.status_code, 200, result.data)
            self.assertTrue(result.data["can_commit"], result.data)
            self.assertEqual(Equipment.objects.count(), 1)
            self.assertEqual(EquipmentResponsibility.objects.count(), 2)
            self.assertEqual(EquipmentInstitutionInventory.objects.count(), 2)

        equipment = Equipment.objects.get(internal_reference="EQ-1")
        rows[0]["Name"] = rows[1]["Name"] = "Updated microscope"
        rows[0]["Responsibility end"] = "2026-12-31"
        rows[0]["Inventory status"] = "closed"
        rows[0]["Inventory ID"] = EquipmentInstitutionInventory.objects.get(inventory_number="INV-1").pk
        preview = self.upload_preview(rows)
        self.assertTrue(preview.data["can_commit"], preview.data)
        self.client.post(self.url("commit"), {"import_token": preview.data["import_token"]}, format="json")
        equipment.refresh_from_db()
        self.assertEqual(equipment.name, "Updated microscope")
        self.assertEqual(EquipmentResponsibility.objects.count(), 2)
        self.assertEqual(EquipmentInstitutionInventory.objects.count(), 2)
        self.assertEqual(str(EquipmentResponsibility.objects.get(employee=self.employee).end_date), "2026-12-31")
        self.assertEqual(EquipmentInstitutionInventory.objects.get(inventory_number="INV-1").status, "closed")

    def test_invalid_reference_ambiguous_relation_and_atomic_rollback(self):
        good = self.row(reference="EQ-GOOD")
        bad = self.row(reference="EQ-BAD", **{"Employee Name": "Nobody Missing"})
        preview = self.upload_preview([good, bad])
        self.assertFalse(preview.data["can_commit"])
        result = self.client.post(self.url("commit"), {"import_token": preview.data["import_token"]}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(Equipment.objects.count(), 0)

        for invalid in (
            self.row(reference="EQ-NO-CATEGORY", Category="Unknown"),
            self.row(reference="EQ-BAD-STATUS", Status="unknown"),
            self.row(reference="EQ-BAD-DATE", **{"Acquisition date": "not-a-date"}),
            self.row(reference="EQ-NO-INSTITUTION", **{"Institution Name": "Unknown institution"}),
            self.row(reference="EQ-REVERSED-DATES", **{
                "Employee Name": "Alice One", "Responsibility start": "2026-12-31",
                "Responsibility end": "2026-01-01",
            }),
        ):
            preview = self.upload_preview([invalid])
            self.assertFalse(preview.data["can_commit"], preview.data)
            self.assertEqual(Equipment.objects.count(), 0)

        preview = self.upload_preview([good, {**good, "Name": "Conflicting name"}])
        self.assertFalse(preview.data["can_commit"], preview.data)
        self.assertIn("Conflicting Equipment", str(preview.data["global_errors"]))
        self.assertEqual(Equipment.objects.count(), 0)

        equipment = Equipment.objects.create(name="Existing", internal_reference="EQ-1", category=self.category)
        for _ in range(2):
            EquipmentResponsibility.objects.create(equipment=equipment, employee=self.employee)
        preview = self.upload_preview([self.row(**{"Employee Name": "Alice One"})])
        self.assertFalse(preview.data["can_commit"])
        self.assertIn("Ambiguous", str(preview.data["rows"]))
        self.assertEqual(EquipmentResponsibility.objects.count(), 2)

        preview = self.upload_preview([self.row(**{
            "Responsibility ID": EquipmentResponsibility.objects.first().pk,
            "Employee Name": "Alice One", "Responsibility end": "2026-12-31",
        })])
        self.assertTrue(preview.data["can_commit"], preview.data)
        self.client.post(self.url("commit"), {"import_token": preview.data["import_token"]}, format="json")
        self.assertEqual(EquipmentResponsibility.objects.count(), 2)

    def test_homonyms_and_institution_name_collision_require_relation_ids(self):
        equipment = Equipment.objects.create(name="Existing", internal_reference="EQ-1", category=self.category)
        responsibility = EquipmentResponsibility.objects.create(equipment=equipment, employee=self.employee)
        inventory = EquipmentInstitutionInventory.objects.create(
            equipment=equipment, institution=self.institution, inventory_number="INV-1",
        )
        Employee.objects.create(first_name="  aLiCe ", last_name=" one ")
        Institution.objects.create(name="Different institution", short_name="University")

        ambiguous_employee = self.row(**{"Employee Name": "Alice One"})
        preview = self.upload_preview([ambiguous_employee])
        self.assertFalse(preview.data["can_commit"])
        self.assertIn("Ambiguous name", str(preview.data["rows"]))
        linked_employee = {**ambiguous_employee, "Responsibility ID": responsibility.pk}
        preview = self.upload_preview([linked_employee])
        self.assertTrue(preview.data["can_commit"], preview.data)
        self.client.post(self.url("commit"), {"import_token": preview.data["import_token"]}, format="json")

        ambiguous_institution = self.row(**{
            "Institution Name": "university", "Inventory number": "INV-1",
        })
        preview = self.upload_preview([ambiguous_institution])
        self.assertFalse(preview.data["can_commit"])
        self.assertIn("Ambiguous name", str(preview.data["rows"]))
        linked_institution = {**ambiguous_institution, "Inventory ID": inventory.pk}
        preview = self.upload_preview([linked_institution])
        self.assertTrue(preview.data["can_commit"], preview.data)
        self.client.post(self.url("commit"), {"import_token": preview.data["import_token"]}, format="json")
        self.assertEqual(EquipmentResponsibility.objects.count(), 1)
        self.assertEqual(EquipmentInstitutionInventory.objects.count(), 1)
        self.assertEqual(EquipmentResponsibility.objects.get().employee_id, self.employee.pk)
        self.assertEqual(EquipmentInstitutionInventory.objects.get().institution_id, self.institution.pk)

    def test_profile_and_relation_permissions(self):
        self.user.user_permissions.remove(Permission.objects.get(content_type__app_label="equipment", codename="view_equipment"))
        self.refresh_user()
        self.assertEqual(self.client.get(self.url("template")).status_code, 403)
        self.assertNotIn("equipment", {profile["key"] for profile in self.client.get(reverse("api_v1:import-profiles")).data["items"]})

        self.grant("equipment", "view_equipment")
        self.user.user_permissions.remove(Permission.objects.get(
            content_type__app_label="equipment", codename="add_equipmentresponsibility",
        ))
        self.refresh_user()
        preview = self.upload_preview([self.row(**{"Employee Name": "Alice One"})])
        self.assertFalse(preview.data["can_commit"])
        result = self.client.post(self.url("commit"), {"import_token": preview.data["import_token"]}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(Equipment.objects.count(), 0)
