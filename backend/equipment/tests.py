"""Equipment V1 catalogue, history, permissions, and note integration."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.db import transaction
from rest_framework.test import APITestCase

from infos.models import GenericNote
from common.models import favorite, subscription
from project.models import Institution
from staff.models import Employee

from .models import (
    Equipment, EquipmentCategory, EquipmentGenericInfo,
    EquipmentGenericInfoType, EquipmentInstitutionInventory,
    EquipmentResponsibility,
)


class EquipmentV1Tests(APITestCase):
    def setUp(self):
        self.editor = get_user_model().objects.create_user(username="equipment-editor")
        self.reader = get_user_model().objects.create_user(username="equipment-reader")
        self.hidden = get_user_model().objects.create_user(username="equipment-hidden")
        self.category = EquipmentCategory.objects.create(name="Microscope")
        self.equipment = Equipment.objects.create(name="Scope A", internal_reference="EQ-001", category=self.category)
        self.base = f"/api/v1/equipment/{self.equipment.pk}/"
        self.employee = Employee.objects.create(first_name="Ada", last_name="Lovelace", is_active=False)
        self.institution = Institution.objects.create(short_name="LAB", name="Laboratory")
        self.grant(self.editor, "view_equipment", "add_equipment", "change_equipment", "delete_equipment",
                   "add_equipmentcategory", "change_equipmentcategory", "delete_equipmentcategory",
                   "add_equipmentgenericinfotype", "change_equipmentgenericinfotype", "delete_equipmentgenericinfotype",
                   "add_equipmentgenericinfo", "change_equipmentgenericinfo", "delete_equipmentgenericinfo",
                   "add_equipmentresponsibility", "change_equipmentresponsibility", "delete_equipmentresponsibility",
                   "add_equipmentinstitutioninventory", "change_equipmentinstitutioninventory", "delete_equipmentinstitutioninventory")
        self.grant(self.reader, "view_equipment")
        self.client.force_login(self.editor)

    def grant(self, user, *codes):
        user.user_permissions.add(*Permission.objects.filter(content_type__app_label="equipment", codename__in=codes))
        for key in ("_perm_cache", "_user_perm_cache", "_group_perm_cache"):
            user.__dict__.pop(key, None)

    def test_equipment_preferences_follow_view_permission_and_navigation(self):
        url = f"/api/v1/preferences/equipment/{self.equipment.pk}/"
        self.assertEqual(self.client.get(url).data, {"favorite": False, "subscription": False})
        self.assertEqual(self.client.put(url, {"favorite": True, "subscription": True}, format="json").status_code, 200)
        self.assertEqual(self.client.get(url).data, {"favorite": True, "subscription": True})
        for path in ("/api/v1/favorites/", "/api/v1/subscriptions/"):
            self.assertEqual(self.client.get(path).data[0]["url"], f"/equipment/{self.equipment.pk}")
            self.assertEqual(self.client.get(path).data[0]["group"], "equipment")
        self.client.force_login(self.hidden)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.put(url, {"favorite": False}, format="json").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/favorites/").data, [])
        self.client.force_login(self.editor)
        self.assertEqual(self.client.put(url, {"favorite": False, "subscription": False}, format="json").status_code, 200)
        self.assertFalse(favorite.objects.filter(user=self.editor).exists())
        self.assertFalse(subscription.objects.filter(user=self.editor).exists())

    def test_equipment_crud_filters_permissions_and_reference(self):
        response = self.client.get("/api/v1/equipment/?search=EQ-001&category=" + str(self.category.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertTrue(response.json()["capabilities"]["can_add"])
        created = self.client.post("/api/v1/equipment/", {"name": "Scope B", "internal_reference": "EQ-002", "category_id": self.category.pk}, format="json")
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.json()["status"], "in_service")
        self.assertIsNone(created.json()["acquisition_date"])
        self.assertEqual(self.client.patch(self.base, {"status": "retired"}, format="json").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/equipment/?status=retired").json()["count"], 1)
        self.assertEqual(self.client.patch(self.base, {"internal_reference": "CHANGED"}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/v1/equipment/", {"name": "Duplicate", "internal_reference": "EQ-001", "category_id": self.category.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.base, {"status": "invalid"}, format="json").status_code, 400)
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(self.base).status_code, 200)
        self.assertFalse(self.client.get(self.base).json()["capabilities"]["can_change"])
        self.assertEqual(self.client.patch(self.base, {"name": "Wrong"}, format="json").status_code, 403)
        self.client.force_login(self.hidden)
        self.assertEqual(self.client.get(self.base).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/equipment/").status_code, 403)

    def test_current_responsible_and_institution_columns_and_filters(self):
        today = date.today()
        other = Equipment.objects.create(name="Scope B", internal_reference="EQ-OTHER", category=self.category)
        current = EquipmentResponsibility.objects.create(equipment=self.equipment, employee=self.employee,
                                                          start_date=today - timedelta(days=1))
        EquipmentResponsibility.objects.create(equipment=other, employee=self.employee,
                                                end_date=today - timedelta(days=1))
        EquipmentInstitutionInventory.objects.create(equipment=self.equipment, institution=self.institution,
                                                       status="registered", start_date=today)
        EquipmentInstitutionInventory.objects.create(equipment=other, institution=self.institution,
                                                       status="closed", start_date=today)
        list_url = "/api/v1/equipment/"
        self.assertEqual(self.client.get(list_url, {"responsible": self.employee.pk}).json()["count"], 0)
        self.assertEqual(self.client.get(list_url, {"institution": self.institution.pk}).json()["count"], 0)
        self.editor.user_permissions.add(Permission.objects.get(content_type__app_label="staff", codename="view_employee"))
        self.editor.user_permissions.add(Permission.objects.get(content_type__app_label="project", codename="view_institution"))
        self.client.force_login(self.editor)
        for parameter, identifier in (("responsible", self.employee.pk), ("institution", self.institution.pk)):
            result = self.client.get(list_url, {parameter: identifier})
            self.assertEqual(result.status_code, 200, result.content)
            self.assertEqual([row["id"] for row in result.json()["results"]], [self.equipment.pk])
        self.client.force_login(self.reader)
        hidden = self.client.get(list_url).json()["results"]
        first = next(row for row in hidden if row["id"] == self.equipment.pk)
        self.assertEqual(first["current_responsibles"], [{"id": None, "name": None}])
        self.assertEqual(first["current_institutions"], [{"id": None, "name": None}])
        self.client.force_login(self.editor)
        shown = next(row for row in self.client.get(list_url).json()["results"] if row["id"] == self.equipment.pk)
        self.assertEqual(shown["current_responsibles"], [{"id": self.employee.pk, "name": str(self.employee)}])
        self.assertEqual(shown["current_institutions"], [{"id": self.institution.pk, "name": self.institution.short_name}])
        self.assertEqual(self.client.get(self.base).json()["current_responsibles"][0]["id"], self.employee.pk)
        current.end_date = today - timedelta(days=1)
        current.save()
        self.assertEqual(self.client.get(list_url, {"responsible": self.employee.pk}).json()["count"], 0)

    def test_dates_and_category_lifecycle(self):
        self.assertEqual(self.client.patch(self.base, {"acquisition_date": "2025-01-02", "commissioning_date": "2025-01-01"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.base, {"acquisition_date": "2025-01-01", "commissioning_date": "2025-01-02"}, format="json").status_code, 200)
        category_url = f"/api/v1/equipment/categories/{self.category.pk}/"
        self.assertEqual(self.client.patch(category_url, {"is_active": False}, format="json").status_code, 200)
        self.assertEqual(self.client.get(self.base).json()["category"]["is_active"], False)
        self.assertEqual(self.client.delete(category_url).status_code, 400)
        self.assertEqual(self.client.post("/api/v1/equipment/", {"name": "New", "internal_reference": "EQ-003", "category_id": self.category.pk}, format="json").status_code, 400)
        other = self.client.post("/api/v1/equipment/categories/", {"name": "Spectrometer"}, format="json")
        self.assertEqual(other.status_code, 201, other.content)
        self.assertEqual(self.client.patch(f'/api/v1/equipment/categories/{other.json()["id"]}/', {"name": "Spectro"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(f'/api/v1/equipment/categories/{other.json()["id"]}/').status_code, 204)
        self.client.force_login(self.reader)
        self.assertEqual(self.client.post("/api/v1/equipment/categories/", {"name": "Denied"}, format="json").status_code, 403)

    def test_generic_info_and_type_contract(self):
        type_url = "/api/v1/equipment/generic-info-types/"
        response = self.client.post(type_url, {"name": "Serial", "icon": "tag"}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        info_type = response.json()["id"]
        self.assertEqual(self.client.get(type_url).json()["items"][0]["name"], "Serial")
        self.assertEqual(self.client.patch(f"{type_url}{info_type}/", {"icon": "barcode"}, format="json").status_code, 200)
        child_url = self.base + "generic-info/"
        first = self.client.post(child_url, {"type_id": info_type, "value": "SN-1"}, format="json")
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(first.json()["type"], {"id": info_type, "name": "Serial", "icon": "barcode"})
        self.assertEqual(self.client.delete(f"{type_url}{info_type}/").status_code, 400)
        self.assertEqual(self.client.post(child_url, {"type_id": info_type, "value": "SN-2"}, format="json").status_code, 201)
        self.assertEqual(len(self.client.get(child_url).json()["items"]), 2)
        detail = child_url + str(first.json()["id"]) + "/"
        self.assertEqual(self.client.patch(detail, {"value": "Changed"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(detail, {"type_id": info_type}, format="json").status_code, 400)
        self.client.force_login(self.reader)
        self.assertFalse(self.client.get(child_url).json()["capabilities"]["can_add"])
        self.assertEqual(self.client.post(child_url, {"type_id": info_type, "value": "Denied"}, format="json").status_code, 403)

    def test_responsibilities_overlap_dates_and_private_employee(self):
        url = self.base + "responsibilities/"
        self.assertEqual(self.client.post(url, {"employee_id": self.employee.pk}, format="json").status_code, 400)
        self.editor.user_permissions.add(Permission.objects.get(content_type__app_label="staff", codename="view_employee"))
        self.editor.__dict__.pop("_perm_cache", None)
        first = self.client.post(url, {"employee_id": self.employee.pk, "start_date": "2024-01-01"}, format="json")
        self.assertEqual(first.status_code, 201, first.content)
        self.assertFalse(first.json()["employee"]["is_active"])
        self.assertEqual(self.client.post(url, {"employee_id": self.employee.pk, "start_date": "2024-02-01"}, format="json").status_code, 201)
        second_employee = Employee.objects.create(first_name="Grace", last_name="Hopper")
        self.assertEqual(self.client.post(url, {"employee_id": second_employee.pk, "start_date": "2024-02-01"}, format="json").status_code, 201)
        self.assertEqual(EquipmentResponsibility.objects.count(), 3)
        detail = url + str(first.json()["id"]) + "/"
        self.assertEqual(self.client.patch(detail, {"end_date": "2023-12-31"}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(detail, {"end_date": "2024-12-31"}, format="json").status_code, 200)
        self.client.force_login(self.reader)
        item = self.client.get(detail).json()
        self.assertFalse(item["employee"]["can_view"])
        self.assertIsNone(item["employee"]["name"])
        self.assertNotIn("email", str(item))
        with self.assertRaises(ProtectedError):
            self.employee.delete()

    def test_institution_inventory_history(self):
        self.editor.user_permissions.add(Permission.objects.get(content_type__app_label="project", codename="view_institution"))
        self.editor.__dict__.pop("_perm_cache", None)
        url = self.base + "institutions/"
        first = self.client.post(url, {"institution_id": self.institution.pk, "inventory_number": "LAB-1"}, format="json")
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(self.client.post(url, {"institution_id": self.institution.pk, "inventory_number": "LAB-2"}, format="json").status_code, 201)
        other_institution = Institution.objects.create(short_name="UNI", name="University")
        self.assertEqual(self.client.post(url, {"institution_id": other_institution.pk, "inventory_number": "UNI-1"}, format="json").status_code, 201)
        self.assertEqual(EquipmentInstitutionInventory.objects.count(), 3)
        detail = url + str(first.json()["id"]) + "/"
        closed = self.client.patch(detail, {"status": "closed"}, format="json")
        self.assertEqual(closed.status_code, 200)
        self.assertFalse(closed.json()["is_active"])
        self.assertEqual(self.client.patch(detail, {"end_date": "2025-01-01"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(detail, {"status": "bad"}, format="json").status_code, 400)
        self.client.force_login(self.reader)
        self.assertFalse(self.client.get(detail).json()["institution"]["can_view"])
        self.assertIsNone(self.client.get(detail).json()["institution"]["name"])
        with self.assertRaises(ProtectedError):
            self.institution.delete()

    def test_equipment_deletion_protects_history_and_notes(self):
        responsibility = EquipmentResponsibility.objects.create(equipment=self.equipment, employee=self.employee)
        self.assertEqual(self.client.delete(self.base).status_code, 400)
        responsibility.delete()
        note = self.client.post(f"/api/v1/notes/equipment/{self.equipment.pk}/", {"name": "History"}, format="json")
        self.assertEqual(note.status_code, 201, note.content)
        self.assertFalse(self.client.get(self.base).json()["capabilities"]["can_delete"])
        with self.assertRaises(ProtectedError):
            with transaction.atomic():
                self.equipment.delete()
        self.assertEqual(self.client.delete(self.base).status_code, 400)
        GenericNote.objects.get(pk=note.json()["id"]).delete()
        self.assertEqual(self.client.delete(self.base).status_code, 204)

    def test_equipment_notes_follow_parent_and_private_visibility(self):
        url = f"/api/v1/notes/equipment/{self.equipment.pk}/"
        self.assertEqual(self.client.post(url, {"name": "Public"}, format="json").status_code, 201)
        private = self.client.post(url, {"name": "Private", "visibility": "creator"}, format="json")
        self.assertEqual(private.status_code, 201)
        self.client.force_login(self.reader)
        self.assertEqual([item["name"] for item in self.client.get(url).json()["items"]], ["Public"])
        self.assertEqual(self.client.get(url + str(private.json()["id"]) + "/").status_code, 404)
        self.assertEqual(self.client.post(url, {"name": "Denied"}, format="json").status_code, 403)
        self.client.force_login(self.hidden)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_model_reference_and_date_validation(self):
        self.equipment.internal_reference = "DIFFERENT"
        with self.assertRaises(ValidationError):
            self.equipment.full_clean()
        relation = EquipmentResponsibility(equipment=self.equipment, employee=self.employee,
                                           start_date=date(2025, 1, 2), end_date=date(2025, 1, 1))
        with self.assertRaises(ValidationError):
            relation.full_clean()
        self.assertEqual(ContentType.objects.get_for_model(Equipment).app_label, "equipment")

    def test_relation_mutation_needs_parent_and_child_permissions(self):
        info_type = EquipmentGenericInfoType.objects.create(name="Maker")
        self.reader.user_permissions.add(Permission.objects.get(content_type__app_label="equipment", codename="add_equipmentgenericinfo"))
        self.reader.__dict__.pop("_perm_cache", None)
        self.client.force_login(self.reader)
        url = self.base + "generic-info/"
        self.assertEqual(self.client.post(url, {"type_id": info_type.pk, "value": "Acme"}, format="json").status_code, 403)
        self.grant(self.reader, "change_equipment")
        self.assertEqual(self.client.post(url, {"type_id": info_type.pk, "value": "Acme"}, format="json").status_code, 201)
