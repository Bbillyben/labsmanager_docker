"""Focused checks for external Django apps owned by plugins."""

import io
import importlib
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TestCase

from labsmanager.plugin_model_apps import discover_model_apps, discover_plugin_static_dirs
from plugin import LabManagerPlugin
from plugin.helpers import get_plugins
from plugin.mixins import ModelMixin
from plugin.ui_assets import module_assets


class EarlyModelDiscoveryTests(SimpleTestCase):
    def make_plugin(self, root, directory="Demo", slug="demo", app="plugins.Demo.apps.DemoConfig",
                    label="demo_model", mixin="ModelMixin"):
        folder = root / directory
        folder.mkdir()
        (folder / "__init__.py").write_text("", encoding="utf-8")
        (folder / f"{directory}.py").write_text(
            f"class Demo({mixin}, LabManagerPlugin):\n"
            f"    NAME = 'Demo'\n    SLUG = {slug!r}\n    DJANGO_APP = {app!r}\n",
            encoding="utf-8",
        )
        (folder / "apps.py").write_text(
            f"class DemoConfig(AppConfig):\n"
            f"    name = 'plugins.{directory}'\n    label = {label!r}\n",
            encoding="utf-8",
        )
        (folder / "models.py").write_text("raise RuntimeError('models imported early')\n", encoding="utf-8")

    def test_non_model_plugin_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(sys, "path", list(sys.path)):
            root = Path(temp) / "plugins"
            root.mkdir()
            (root / "__init__.py").write_text("", encoding="utf-8")
            self.make_plugin(root, mixin="UrlsMixin")
            self.assertEqual(discover_model_apps(Path(temp), [root]), {})

    def test_model_app_is_found_without_importing_models(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(sys, "path", list(sys.path)):
            root = Path(temp) / "plugins"
            root.mkdir()
            (root / "__init__.py").write_text("", encoding="utf-8")
            self.make_plugin(root)
            app = discover_model_apps(Path(temp), [root])["demo"]
            self.assertEqual(app.app_config, "plugins.Demo.apps.DemoConfig")
            self.assertEqual(app.label, "demo_model")
            self.assertNotIn("plugins.Demo.models", sys.modules)

    def test_invalid_declaration_and_collisions_fail(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(sys, "path", list(sys.path)):
            root = Path(temp) / "plugins"
            root.mkdir()
            (root / "__init__.py").write_text("", encoding="utf-8")
            self.make_plugin(root, app="wrong.path.Config")
            with self.assertRaisesMessage(ImproperlyConfigured, "Invalid DJANGO_APP"):
                discover_model_apps(Path(temp), [root])
            (root / "Demo" / "Demo.py").write_text(
                "class Demo(ModelMixin, LabManagerPlugin):\n"
                "    NAME = 'Demo'\n    SLUG = 'demo'\n"
                "    DJANGO_APP = 'plugins.Demo.apps.DemoConfig'\n", encoding="utf-8")
            self.make_plugin(root, directory="Other", slug="other", app="plugins.Other.apps.DemoConfig")
            with self.assertRaisesMessage(ImproperlyConfigured, "Duplicate app label"):
                discover_model_apps(Path(temp), [root])
            (root / "Other" / "Other.py").write_text(
                "class Other(ModelMixin, LabManagerPlugin):\n"
                "    NAME = 'Other'\n    SLUG = 'demo'\n"
                "    DJANGO_APP = 'plugins.Other.apps.DemoConfig'\n", encoding="utf-8")
            with self.assertRaisesMessage(ImproperlyConfigured, "Duplicate plugin slug"):
                discover_model_apps(Path(temp), [root])

    def test_builtin_model_plugin_uses_one_python_identity(self):
        import plugin.builtin
        from plugin.registry import PluginsRegistry, registry

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "plugin" / "builtin"
            root.mkdir(parents=True)
            (root / "__init__.py").write_text("", encoding="utf-8")
            folder = root / "BuiltinModelFixture"
            folder.mkdir()
            (folder / "__init__.py").write_text("", encoding="utf-8")
            (folder / "BuiltinModelFixture.py").write_text(
                "from plugin import LabManagerPlugin\n"
                "from plugin.mixins import ModelMixin, UrlsMixin, UIContributionMixin, TokenMixin\n"
                "class BuiltinModelFixture(ModelMixin, UrlsMixin, UIContributionMixin, TokenMixin, LabManagerPlugin):\n"
                "    NAME = 'Builtin model fixture'\n"
                "    SLUG = 'builtin-model-fixture'\n"
                "    DJANGO_APP = 'plugin.builtin.BuiltinModelFixture.apps.BuiltinModelFixtureConfig'\n",
                encoding="utf-8",
            )
            (folder / "apps.py").write_text(
                "from django.apps import AppConfig\n"
                "class BuiltinModelFixtureConfig(AppConfig):\n"
                "    name = 'plugin.builtin.BuiltinModelFixture'\n"
                "    label = 'builtin_model_fixture'\n",
                encoding="utf-8",
            )
            (folder / "models.py").write_text(
                "from django.db import models\n"
                "class FixtureRecord(models.Model):\n"
                "    name = models.CharField(max_length=40)\n",
                encoding="utf-8",
            )
            migrations = folder / "migrations"
            migrations.mkdir()
            (migrations / "__init__.py").write_text("", encoding="utf-8")
            (migrations / "0001_initial.py").write_text(
                "from django.db import migrations, models\n"
                "class Migration(migrations.Migration):\n"
                "    initial = True\n"
                "    operations = [migrations.CreateModel(name='FixtureRecord', fields=["
                "('id', models.AutoField(primary_key=True, serialize=False)), "
                "('name', models.CharField(max_length=40))])]\n",
                encoding="utf-8",
            )
            dist = folder / "frontend" / "dist"
            (dist / "assets").mkdir(parents=True)
            (dist / "assets" / "main.js").write_text("export {};\n", encoding="utf-8")
            (dist / "manifest.json").write_text(json.dumps({"src/main.tsx": {
                "file": "assets/main.js", "name": "main", "isEntry": True,
            }}), encoding="utf-8")

            declaration = discover_model_apps(Path(temp))["builtin-model-fixture"]
            self.assertEqual(declaration.app_config, "plugin.builtin.BuiltinModelFixture.apps.BuiltinModelFixtureConfig")
            self.assertEqual(declaration.label, "builtin_model_fixture")
            self.assertEqual(discover_plugin_static_dirs(Path(temp)),
                             [("plugins/builtin-model-fixture", str(dist))])

            original_path = list(plugin.builtin.__path__)
            with patch.object(plugin.builtin, "__path__", [str(root), *original_path]), \
                    patch.object(settings, "PLUGIN_MODEL_APPS", {
                        **settings.PLUGIN_MODEL_APPS, declaration.slug: declaration,
                    }), patch.object(registry, "reload_plugins"):
                apps.set_installed_apps([*settings.INSTALLED_APPS, declaration.app_config])
                try:
                    model = apps.get_model("builtin_model_fixture", "FixtureRecord")
                    self.assertEqual(model.__module__, "plugin.builtin.BuiltinModelFixture.models")
                    with patch.object(settings, "PLUGIN_MODEL_APPS", {declaration.slug: declaration}), \
                            patch.object(PluginsRegistry, "plugin_dirs", return_value=["plugin.builtin"]):
                        plugins = PluginsRegistry().collect_plugins()
                    self.assertEqual(sum(item.SLUG == declaration.slug for item in plugins), 1)
                    fixture = next(item for item in plugins if item.SLUG == declaration.slug)
                    self.assertEqual(fixture.__module__, "plugin.builtin.BuiltinModelFixture.BuiltinModelFixture")
                    self.assertIs(model, importlib.import_module(model.__module__).FixtureRecord)
                    self.assertNotIn("BuiltinModelFixture.models", sys.modules)
                    self.assertNotIn("BuiltinModelFixture.BuiltinModelFixture", sys.modules)
                    self.assertIn(("builtin_model_fixture", "0001_initial"), MigrationLoader(None).graph.nodes)
                    self.assertTrue(module_assets(fixture(), "main")["module_url"].startswith(
                        "/static/plugins/builtin-model-fixture/assets/main.js"))
                finally:
                    apps.unset_installed_apps()
                    for name in list(sys.modules):
                        if name.startswith("plugin.builtin.BuiltinModelFixture"):
                            sys.modules.pop(name)

    def test_existing_builtin_plugin_keeps_its_mixins_and_module_name(self):
        import plugin.builtin
        from plugin.mixins import TokenMixin, UIContributionMixin, UrlsMixin

        plugins = get_plugins(plugin.builtin, LabManagerPlugin)
        builtin = next(item for item in plugins if item.SLUG == "icalexport")
        self.assertEqual(builtin.__module__, "plugin.builtin.ICalExport.ICalExport")
        self.assertTrue(all(issubclass(builtin, mixin) for mixin in
                            (TokenMixin, UIContributionMixin, UrlsMixin)))


class ModelExampleTests(TestCase):
    @classmethod
    def setUpClass(cls):
        if "modelexample" not in settings.PLUGIN_MODEL_APPS:
            raise RuntimeError("Run with LABSMANAGER_PLUGIN_DIR pointing at data/plugins and plugins enabled")
        super().setUpClass()

    def test_app_registry_plugin_registry_and_migration(self):
        from plugin import registry

        app = apps.get_app_config("model_example")
        self.assertEqual(app.name, "plugins.ModelExample")
        self.assertIn("plugins.ModelExample.apps.ModelExampleConfig", settings.INSTALLED_APPS)
        self.assertIsNotNone(app.get_model("ExampleRecord"))
        self.assertEqual(settings.PLUGIN_MODEL_APPS["modelexample"].label, app.label)
        out = io.StringIO()
        call_command("showmigrations", "model_example", stdout=out)
        self.assertIn("[X] 0001_initial", out.getvalue())
        executor = MigrationExecutor(connection)
        self.assertIn(("model_example", "0001_initial"), executor.loader.graph.nodes)
        self.assertEqual(executor.migration_plan([("model_example", "0001_initial")]), [])
        executor.loader.applied_migrations.pop(("model_example", "0001_initial"))
        self.assertEqual(len(executor.migration_plan([("model_example", "0001_initial")])), 1)
        self.assertTrue(any(issubclass(plugin, ModelMixin) and plugin.SLUG == "modelexample"
                            for plugin in registry.collect_plugins()))

    def test_example_record_crud(self):
        record_model = apps.get_model("model_example", "ExampleRecord")
        record = record_model.objects.create(name="Échantillon", description="Premier")
        self.assertEqual(str(record), "Échantillon")
        self.assertIsNotNone(record.created_at)
        self.assertEqual(record_model.objects.get(pk=record.pk).description, "Premier")
        record.name = "Modifié"
        record.save(update_fields=["name"])
        self.assertEqual(record_model.objects.get(pk=record.pk).name, "Modifié")
        record.delete()
        self.assertFalse(record_model.objects.filter(pk=record.pk).exists())
