"""R3.8 registry, query, engine, schema, API and visibility contracts."""

from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from project.models import Participant, Project
from staff.models import Employee
from plugin import LabManagerPlugin
from plugin.mixins import SearchPluginMixin

from .contracts import SearchField, SearchProvider, SearchQuery, SearchResult
from .engine import SearchEngine
from .providers import ProjectSearchProvider
from .registry import DuplicateProviderKey, SearchRegistry


class SearchContractsTests(SimpleTestCase):
    def test_plugin_mixin_registers_search_capability(self):
        class TestPlugin(SearchPluginMixin, LabManagerPlugin):
            NAME = "TestSearchPlugin"

        plugin = TestPlugin()
        self.assertTrue(plugin.mixin_enabled("search"))
        self.assertEqual(plugin.get_search_providers(object()), ())

    def test_structured_query_and_required_result_fields(self):
        query = SearchQuery.from_text("  Jean  Dupont ", provider_filter="employee")
        self.assertEqual(query.raw_text, "Jean Dupont")
        self.assertEqual(query.free_text_terms, ("Jean", "Dupont"))
        self.assertEqual(query.provider_filter, "employee")
        self.assertEqual(query.field_filters, {})
        self.assertIsNone(query.ast)
        result = SearchResult("employee", "7", "Jean Dupont", "", "/app/employees/7", 100,
                              "UserRound", "Name: Jean Dupont")
        self.assertEqual(result.as_dict()["match_reason"], "Name: Jean Dupont")
        for invalid in ("/admin/", "https://example.test/app/employees/7"):
            with self.assertRaises(ValueError):
                SearchResult("employee", "7", "Jean", "", invalid, 1, "UserRound", "Name")
        with self.assertRaises(ValueError):
            SearchResult("employee", "7", "Jean", "", "/app/employees/7", -1, "UserRound", "Name")

    def test_registry_register_collision_unregister_and_plugin_lifecycle(self):
        registry = SearchRegistry()
        provider = ProjectSearchProvider()
        registry.register(provider)
        with self.assertRaises(DuplicateProviderKey):
            registry.register(ProjectSearchProvider())
        actor = SimpleNamespace(is_authenticated=True)

        class PluginProvider(SearchProvider):
            key = "publication"
            label = "Publications"
            icon = "BookOpen"
            fields = (SearchField("title", "Title", ("name",)),)

            def visible_queryset(self, user):
                return Project.objects.none()

            def make_result(self, obj, *, score, match_reason):
                return SearchResult(self.key, str(obj.pk), obj.name, "", f"/app/projects/{obj.pk}",
                                    score, self.icon, match_reason)

        plugin_provider = PluginProvider()
        plugin = SimpleNamespace(get_search_providers=lambda user: (plugin_provider,))
        with patch("plugin.registry.registry.with_mixin", return_value=[plugin]) as active:
            self.assertEqual([item.key for item in registry.active(actor)], ["project", "publication"])
            self.assertIs(registry.get("publication", actor), plugin_provider)
            active.assert_called_with("search", active=True)
        duplicate = SimpleNamespace(get_search_providers=lambda user: (ProjectSearchProvider(),))
        with patch("plugin.registry.registry.with_mixin", return_value=[duplicate]):
            with self.assertLogs("labsmanager", level="ERROR"):
                self.assertEqual([item.key for item in registry.active(actor)], ["project"])
        with patch("plugin.registry.registry.with_mixin", return_value=[]):
            self.assertIsNone(registry.get("publication", actor))
        self.assertIs(registry.unregister("project"), provider)
        self.assertEqual(registry.unregister("project"), None)


class SearchApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="search-reader", password="test")
        self.employee = Employee.objects.create(first_name="Jean", last_name="Dupont", email="jean@example.test", user=self.user)
        self.hidden_employee = Employee.objects.create(first_name="Jean", last_name="Hidden", email="hidden@example.test")
        self.project = Project.objects.create(name="PreciseIT visible")
        self.hidden_project = Project.objects.create(name="PreciseIT secret")
        Participant.objects.create(project=self.project, employee=self.employee, status="p")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_search_schema_core_and_visibility(self):
        schema = self.client.get(reverse("api_v1:search-schema"))
        self.assertEqual(schema.status_code, 200)
        providers = {item["key"]: item for item in schema.data["providers"]}
        self.assertIn("employee", providers)
        self.assertIn("project", providers)
        self.assertEqual([field["key"] for field in providers["employee"]["fields"]], ["name", "email", "status", "generic_info"])
        self.assertEqual(providers["project"]["icon"], "FolderKanban")
        self.assertTrue(providers["project"]["supports_generic_info"])
        self.assertTrue(providers["project"]["autocomplete"])
        self.assertTrue(next(field for field in providers["project"]["fields"] if field["key"] == "leader")["suggest_values"])
        employee = self.client.get(reverse("api_v1:search"), {"q": "Jean Dupont", "provider": "employee"})
        self.assertEqual(employee.status_code, 200)
        self.assertEqual([item["object_id"] for item in employee.data["results"]], [str(self.employee.pk)])
        self.assertEqual(employee.data["results"][0]["url"], f"/app/employees/{self.employee.pk}")
        self.assertIn("Name", employee.data["results"][0]["match_reason"])
        self.assertNotIn("hidden@example.test", str(employee.data))
        projects = self.client.get(reverse("api_v1:search"), {"q": "PreciseIT"})
        self.assertEqual([item["object_id"] for item in projects.data["results"]], [str(self.project.pk)])
        self.assertEqual(projects.data["results"][0]["url"], f"/app/projects/{self.project.pk}")
        self.assertNotIn("secret", str(projects.data))

    def test_provider_filter_empty_and_validation(self):
        endpoint = reverse("api_v1:search")
        self.assertEqual(self.client.get(endpoint, {"q": ""}).data["results"], [])
        self.assertEqual(self.client.get(endpoint, {"q": "PreciseIT", "provider": "employee"}).data["results"], [])
        self.assertEqual([item["provider_key"] for item in self.client.get(endpoint, {"q": "PreciseIT", "provider": "project"}).data["results"]], ["project"])
        for params in ({"q": "x", "provider": "missing"}, {"q": "x", "limit": 0},
                       {"q": "x", "limit": 101}, {"q": "x", "per_provider": 26},
                       {"q": "x " * 13}, {"q": "x" * 201}):
            self.assertEqual(self.client.get(endpoint, params).status_code, 400, params)

    def test_engine_scores_and_merges_without_returning_hidden_rows(self):
        with patch("plugin.registry.registry.with_mixin", return_value=[]):
            exact = Project.objects.create(name="PreciseIT")
            Participant.objects.create(project=exact, employee=self.employee, status="p")
            results = SearchEngine().search(self.user, SearchQuery.from_text("PreciseIT"), limit=2)
        self.assertEqual([item.object_id for item in results], [str(exact.pk), str(self.project.pk)])
        self.assertGreater(results[0].score, results[1].score)
        self.assertNotIn(str(self.hidden_project.pk), [item.object_id for item in results])
        self.assertEqual(len(SearchEngine().search(self.user, SearchQuery.from_text("Jean"), limit=1)), 1)

    def test_exact_match_after_candidate_boundary_keeps_priority(self):
        Project.objects.bulk_create([Project(name=f"A Needle project {index}") for index in range(110)])
        exact = Project.objects.create(name="Needle")
        with (patch("plugin.registry.registry.with_mixin", return_value=[]),
              patch.object(Project, "get_instances_for_user", side_effect=lambda perm, user, queryset: queryset)):
            results = SearchEngine().search(self.user, SearchQuery.from_text("Needle", provider_filter="project"), limit=1)
        self.assertEqual(results[0].object_id, str(exact.pk))

    def test_plugin_provider_schema_search_and_unload(self):
        class TestProvider(SearchProvider):
            key = "publication"
            label = "Publications"
            icon = "BookOpen"
            fields = (SearchField("title", "Title", ("name",)),)

            def visible_queryset(self, user):
                return Project.get_instances_for_user("view", user, Project.objects.all())

            def make_result(self, obj, *, score, match_reason):
                return SearchResult(self.key, str(obj.pk), obj.name, "", f"/app/projects/{obj.pk}",
                                    score, self.icon, match_reason)

        plugin = SimpleNamespace(get_search_providers=lambda user: (TestProvider(),))
        with patch("plugin.registry.registry.with_mixin", return_value=[plugin]):
            schema = self.client.get(reverse("api_v1:search-schema"))
            self.assertIn("publication", [item["key"] for item in schema.data["providers"]])
            response = self.client.get(reverse("api_v1:search"), {"q": "PreciseIT", "provider": "publication"})
            self.assertEqual([item["provider_key"] for item in response.data["results"]], ["publication"])
            self.assertEqual(response.data["counts"], {"publication": 1})
            merged = self.client.get(reverse("api_v1:search"), {"q": "PreciseIT", "limit": 8, "per_provider": 3})
            self.assertEqual({item["provider_key"] for item in merged.data["results"]}, {"project", "publication"})
        with patch("plugin.registry.registry.with_mixin", return_value=[]):
            self.assertNotIn("publication", [item["key"] for item in self.client.get(reverse("api_v1:search-schema")).data["providers"]])
            self.assertEqual(self.client.get(reverse("api_v1:search"), {"q": "PreciseIT", "provider": "publication"}).status_code, 400)

    def test_anonymous_search_and_schema_are_denied(self):
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get(reverse("api_v1:search")).status_code, (401, 403))
        self.assertIn(self.client.get(reverse("api_v1:search-schema")).status_code, (401, 403))
