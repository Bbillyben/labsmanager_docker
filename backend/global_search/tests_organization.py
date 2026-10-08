"""Organization joins Global Search through one provider and existing visibility."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APIClient

from fund.models import Fund_Institution
from infos.models import OrganizationInfos, OrganizationInfosType
from project.models import Institution


class OrganizationSearchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="organization-search")
        self.institution = Institution.objects.create(name="Northern Research Institute", short_name="NRI")
        self.funder = Fund_Institution.objects.create(name="National Research Fund", short_name="NRF")
        self.info_type = OrganizationInfosType.objects.create(name="Research email", type="mail")
        OrganizationInfos.objects.create(
            content_type=ContentType.objects.get_for_model(Institution), object_id=self.institution.pk,
            info=self.info_type, value="contact@nri.example",
        )
        OrganizationInfos.objects.create(
            content_type=ContentType.objects.get_for_model(Institution), object_id=self.institution.pk,
            info=self.info_type, value="alternate@nri.example",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def search(self, text):
        response = self.client.get("/api/v1/search/", {"q": text, "provider": "organization"})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_visibility_matches_organization_detail_permission(self):
        schema = self.client.get("/api/v1/search/schema/").data["providers"]
        self.assertNotIn("organization", {item["key"] for item in schema})
        self.assertEqual(self.client.get("/api/v1/search/", {"q": "Northern"}).data["results"], [])
        self.assertEqual(self.client.get("/api/v1/search/", {"q": "contact@nri.example"}).data["results"], [])
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="common", codename="display_infos",
        ))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_authenticate(self.user)
        schema = self.client.get("/api/v1/search/schema/").data["providers"]
        self.assertEqual([item["key"] for item in schema if item["key"] == "organization"], ["organization"])
        self.assertTrue(next(item for item in schema if item["key"] == "organization")["supports_generic_info"])
        self.assertEqual(len(self.search("Northern")["results"]), 1)

    def test_name_acronym_dynamic_info_and_routes(self):
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="common", codename="display_infos",
        ))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_authenticate(self.user)
        for term in ("Northern", "NRI", "contact@nri.example", 'info:"Research email"="contact@nri.example"'):
            data = self.search(term)
            self.assertEqual(len(data["results"]), 1, term)
            self.assertEqual(data["results"][0]["url"], f"/app/organizations/institutions/{self.institution.pk}")
            self.assertEqual(data["results"][0]["provider_key"], "organization")
        self.assertEqual(len(self.search('organization:"Northern Research Institute"')["results"]), 1)
        # Two matching info rows still produce one result for the same organization.
        self.assertEqual(len(self.search("nri.example")["results"]), 1)
        funder = self.search("NRF")["results"]
        self.assertEqual(len(funder), 1)
        self.assertEqual(funder[0]["url"], f"/app/organizations/funders/{self.funder.pk}")
        self.assertEqual(funder[0]["subtitle"], "Funder")
        completion = self.client.get("/api/v1/search/autocomplete/", {"q": 'info:"Res', "cursor": 9})
        self.assertEqual(completion.status_code, 200, completion.data)
        self.assertIn("Research email", {item["label"] for item in completion.data["suggestions"]})

    def test_same_name_in_both_tables_remains_two_role_specific_records(self):
        self.user.user_permissions.add(Permission.objects.get(
            content_type__app_label="common", codename="display_infos",
        ))
        self.user = get_user_model().objects.get(pk=self.user.pk)
        self.client.force_authenticate(self.user)
        counterpart = Fund_Institution.objects.create(name=self.institution.name, short_name=self.institution.short_name)
        results = self.search("Northern")["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual({item["provider_key"] for item in results}, {"organization"})
        self.assertEqual({item["metadata"]["role"] for item in results}, {"institution", "funder"})
        self.assertEqual({item["url"] for item in results}, {
            f"/app/organizations/institutions/{self.institution.pk}",
            f"/app/organizations/funders/{counterpart.pk}",
        })
