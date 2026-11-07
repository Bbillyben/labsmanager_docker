"""Equipment Search uses the live provider contract and model visibility."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from equipment.models import (
    Equipment, EquipmentCategory, EquipmentGenericInfo,
    EquipmentGenericInfoType, EquipmentInstitutionInventory,
)
from project.models import Institution


class EquipmentSearchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="equipment-search")
        self.category = EquipmentCategory.objects.create(name="Microscopes")
        self.item = Equipment.objects.create(name="Zeiss Scope", internal_reference="EQ-SEARCH-1", category=self.category)
        self.other = Equipment.objects.create(name="Other Scope", internal_reference="EQ-SEARCH-2", category=self.category)
        self.info_type = EquipmentGenericInfoType.objects.create(name="Serial number")
        EquipmentGenericInfo.objects.create(equipment=self.item, info=self.info_type, value="SERIAL-ABC")
        EquipmentGenericInfo.objects.create(equipment=self.item, info=self.info_type, value="SERIAL-XYZ")
        institution = Institution.objects.create(short_name="UNI", name="University")
        EquipmentInstitutionInventory.objects.create(equipment=self.item, institution=institution, inventory_number="INV-42")
        EquipmentInstitutionInventory.objects.create(equipment=self.item, institution=institution, inventory_number="INV-43")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def search(self, query):
        response = self.client.get("/api/v1/search/", {"q": query, "provider": "equipment"})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def grant(self):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="equipment", codename="view_equipment"))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_authenticate(self.user)

    def test_provider_visibility_and_navigation(self):
        schema = self.client.get("/api/v1/search/schema/").data["providers"]
        self.assertNotIn("equipment", {item["key"] for item in schema})
        self.assertEqual(self.client.get("/api/v1/search/", {"q": "Zeiss"}).data["results"], [])
        self.grant()
        schema = self.client.get("/api/v1/search/schema/").data["providers"]
        provider = next(item for item in schema if item["key"] == "equipment")
        self.assertTrue(provider["supports_generic_info"])
        for query in ("Zeiss", "EQ-SEARCH-1", "Microscopes", "SERIAL-ABC", "Serial number", "INV-42"):
            self.assertIn(str(self.item.pk), {item["object_id"] for item in self.search(query)["results"]}, query)
        self.assertEqual(self.search("Zeiss")["results"][0]["url"], f"/app/equipment/{self.item.pk}")

    def test_advanced_queries_deduplicate_multiple_relations(self):
        self.grant()
        for query in ('equipment:"Zeiss Scope"', 'reference:EQ-SEARCH-1',
                      'category:Microscopes AND inventory:INV-42',
                      'info:"Serial number"="SERIAL-ABC"'):
            self.assertEqual([item["object_id"] for item in self.search(query)["results"]], [str(self.item.pk)], query)
        self.assertEqual(self.search("SERIAL")["counts"]["equipment"], 1)
        self.assertEqual(self.search("INV")["counts"]["equipment"], 1)

    def test_autocomplete_is_permission_scoped(self):
        query = 'info:"Ser'
        response = self.client.get("/api/v1/search/autocomplete/", {"q": query, "cursor": len(query)})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Serial number", {item["label"] for item in response.data["suggestions"]})
        self.grant()
        response = self.client.get("/api/v1/search/autocomplete/", {"q": query, "cursor": len(query)})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Serial number", {item["label"] for item in response.data["suggestions"]})
