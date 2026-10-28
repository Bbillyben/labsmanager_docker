"""The browser may load only built assets owned by the local plugin."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from labsmanager.plugin_model_apps import discover_plugin_static_dirs
from plugin.ui_assets import module_assets


class LocalPlugin:
    slug = "alpha"

    def __init__(self, path):
        self._path = path

    def path(self):
        return self._path


class ModuleAssetTests(SimpleTestCase):
    def test_manifest_maps_hashed_js_and_css_to_same_origin(self):
        with tempfile.TemporaryDirectory() as temp:
            dist = Path(temp) / "frontend" / "dist"
            (dist / "assets").mkdir(parents=True)
            (dist / "assets" / "main-abc.js").write_text("export const Page = () => null", encoding="utf-8")
            (dist / "assets" / "main-abc.css").write_text(".demo {}", encoding="utf-8")
            manifest = {"src/main.tsx": {"file": "assets/main-abc.js", "name": "main",
                                         "isEntry": True, "css": ["assets/main-abc.css"]}}
            (dist / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            first = module_assets(LocalPlugin(temp), "main")
            self.assertTrue(first["module_url"].startswith("/static/plugins/alpha/assets/main-abc.js?v="))
            self.assertTrue(first["css_urls"][0].startswith("/static/plugins/alpha/assets/main-abc.css?v="))
            self.assertEqual(module_assets(LocalPlugin(temp), "main"), first)
            manifest["src/main.tsx"]["file"] = "assets/main-new.js"
            (dist / "assets" / "main-new.js").write_text("export const Page = () => 1", encoding="utf-8")
            (dist / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertNotEqual(module_assets(LocalPlugin(temp), "main")["module_url"], first["module_url"])

    def test_manifest_cannot_point_outside_collected_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            dist = Path(temp) / "frontend" / "dist"
            dist.mkdir(parents=True)
            manifest = {"src/main.tsx": {"file": "https://example.com/bad.js", "name": "main", "isEntry": True}}
            (dist / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesMessage(ValueError, "Invalid plugin UI asset"):
                module_assets(LocalPlugin(temp), "main")
            manifest["src/main.tsx"]["file"] = "../secret.js"
            (dist / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesMessage(ValueError, "Invalid plugin UI asset"):
                module_assets(LocalPlugin(temp), "main")

    def test_static_discovery_includes_plugins_without_django_models(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "plugins"
            plugin = root / "NoModel"
            dist = plugin / "frontend" / "dist"
            dist.mkdir(parents=True)
            (root / "__init__.py").write_text("", encoding="utf-8")
            (plugin / "NoModel.py").write_text(
                "class NoModel(LabManagerPlugin):\n    NAME = 'NoModel'\n    SLUG = 'no-model'\n",
                encoding="utf-8",
            )
            (dist / "manifest.json").write_text("{}", encoding="utf-8")
            self.assertIn(("plugins/no-model", str(dist)), discover_plugin_static_dirs(Path(temp), [root]))
            with patch("labsmanager.plugin_model_apps.source_directories", return_value=[
                (root, "plugin.builtin"), (root, "plugins"),
            ]):
                with self.assertRaisesMessage(ImproperlyConfigured, "Duplicate or invalid plugin static slug"):
                    discover_plugin_static_dirs(Path(temp))
