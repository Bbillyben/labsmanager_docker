"""Focused tests for pre-import diagnostics and atomic plugin package publication."""

import fcntl
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from plugin.dependencies import (Candidate, _validate_environment, _write_operation, diagnose, discover_candidates,
                                 environment_root, install, parse_requirements, request_install)
from plugin.models import PluginConfig
from plugin.registry import registry
from plugin.serializers import PluginActivateSerializer


class DependencyServiceTests(SimpleTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.override = override_settings(LAB_PLUGIN_PACKAGES_ROOT=str(self.root / "packages"))
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.plugins = self.root / "samples"
        self.folder = self.plugins / "BrokenPlugin"
        self.folder.mkdir(parents=True)
        (self.folder / "BrokenPlugin.py").write_text(
            "from missing_python_module import Missing\nclass BrokenPlugin:\n    NAME='BrokenPlugin'\n    SLUG='broken'\n",
            encoding="utf-8",
        )
        self.candidate = Candidate("broken", self.folder, "BrokenPlugin")

    def test_discovery_never_imports_plugin_and_no_requirements(self):
        with patch.object(registry, "plugin_dirs", return_value=[self.plugins]), patch(
            "plugin.helpers.get_entrypoints", return_value=[]
        ):
            found = discover_candidates()
        self.assertIn("broken", found)
        self.assertEqual(parse_requirements(found["broken"]), ([], []))
        with patch("plugin.dependencies.discover_candidates", return_value=found):
            self.assertEqual(diagnose("broken")["state"], "none")

    def test_satisfied_missing_incompatible_and_invalid(self):
        (self.folder / "requirements.txt").write_text("example>=2,<3\n", encoding="utf-8")
        with patch("plugin.dependencies._on_disk", return_value=({}, {})), patch(
            "plugin.dependencies._distributions", return_value={}
        ):
            self.assertEqual(diagnose("broken", {"broken": self.candidate})["state"], "missing")
        dist = SimpleNamespace(version="2.5", metadata={"Name": "example"})
        with patch("plugin.dependencies._on_disk", return_value=({"example": dist}, {})), patch(
            "plugin.dependencies._distributions", return_value={"example": dist}
        ):
            self.assertEqual(diagnose("broken", {"broken": self.candidate})["state"], "satisfied")
        dist.version = "1.0"
        with patch("plugin.dependencies._on_disk", return_value=({"example": dist}, {})), patch(
            "plugin.dependencies._distributions", return_value={"example": dist}
        ):
            self.assertEqual(diagnose("broken", {"broken": self.candidate})["state"], "incompatible")
        for line in ("-r other.txt", "example @ https://example.test/a.whl", "../local", "not a valid requirement !"):
            (self.folder / "requirements.txt").write_text(line + "\n", encoding="utf-8")
            self.assertTrue(parse_requirements(self.candidate)[1], line)

    def test_atomic_success_failure_and_environment_fingerprint(self):
        (self.folder / "requirements.txt").write_text("example==2.0\n", encoding="utf-8")
        root = environment_root()
        releases = root / "releases"
        releases.mkdir(parents=True)
        old = releases / "old"
        old.mkdir()
        (root / "active").symlink_to(old)
        _write_operation({"id": "job", "key": "broken", "state": "queued"})
        dist = SimpleNamespace(version="2.0", metadata={"Name": "example"}, requires=[])

        def fake_pip(arguments, timeout=600):
            if "--report" in arguments:
                Path(arguments[arguments.index("--report") + 1]).write_text(
                    json.dumps({"install": [{"metadata": {"name": "example", "version": "2.0"}}]}),
                    encoding="utf-8",
                )

        with patch("plugin.dependencies.discover_candidates", return_value={"broken": self.candidate}), patch(
            "plugin.models.PluginConfig.objects.filter", return_value=[]
        ), patch("plugin.dependencies._on_disk", return_value=({}, {})), patch(
            "plugin.dependencies._distributions", return_value={"example": dist}
        ), patch("plugin.dependencies._validate_environment"), patch("plugin.dependencies._run_pip", side_effect=fake_pip):
            install("broken", "job")
        self.assertNotEqual((root / "active").resolve(), old)
        self.assertTrue(old.is_dir())
        published = (root / "active").resolve()
        _write_operation({"id": "fail", "key": "broken", "state": "queued"})
        with patch("plugin.dependencies.discover_candidates", return_value={"broken": self.candidate}), patch(
            "plugin.models.PluginConfig.objects.filter", return_value=[]
        ), patch("plugin.dependencies._on_disk", return_value=({}, {})), patch(
            "plugin.dependencies._run_pip", side_effect=RuntimeError("pip failed")
        ):
            with self.assertRaisesRegex(RuntimeError, "pip failed"):
                install("broken", "fail")
        self.assertEqual((root / "active").resolve(), published)
        self.assertIn("py", root.name)

    def test_concurrent_installation_is_refused(self):
        (self.folder / "requirements.txt").write_text("missing-package==1\n", encoding="utf-8")
        root = environment_root()
        root.mkdir(parents=True)
        with open(root / "install.lock", "a+") as lock, patch(
            "plugin.dependencies.discover_candidates", return_value={"broken": self.candidate}
        ), patch("plugin.dependencies._on_disk", return_value=({}, {})), patch(
            "plugin.dependencies._distributions", return_value={}
        ):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, "Another installation"):
                request_install("broken")

    def test_new_release_keeps_already_managed_distributions(self):
        (self.folder / "requirements.txt").write_text("example==2.0\n", encoding="utf-8")
        root = environment_root()
        previous_release = root / "releases" / "previous"
        previous_release.mkdir(parents=True)
        (previous_release / "existing-package.txt").write_text("kept", encoding="utf-8")
        (root / "active").symlink_to(previous_release)
        _write_operation({"id": "next", "key": "broken", "state": "queued"})
        dist = SimpleNamespace(version="2.0", metadata={"Name": "example"}, requires=[])

        def fake_pip(arguments, timeout=600):
            Path(arguments[arguments.index("--report") + 1]).write_text('{"install": []}', encoding="utf-8")

        with patch("plugin.dependencies.discover_candidates", return_value={"broken": self.candidate}), patch(
            "plugin.models.PluginConfig.objects.filter", return_value=[]
        ), patch("plugin.dependencies._on_disk", return_value=({}, {"example": dist})), patch(
            "plugin.dependencies._distributions", return_value={"example": dist}
        ), patch("plugin.dependencies._run_pip", side_effect=fake_pip):
            install("broken", "next")
        self.assertEqual(((root / "active").resolve() / "existing-package.txt").read_text(encoding="utf-8"), "kept")

    def test_conflicting_plugins_and_core_override_are_rejected(self):
        from packaging.requirements import Requirement
        core = SimpleNamespace(version="1.0", metadata={"Name": "example"}, requires=[])
        staged = SimpleNamespace(version="2.0", metadata={"Name": "example"}, requires=[])
        with self.assertRaisesRegex(RuntimeError, "override a core distribution"):
            _validate_environment({"example": core}, {"example": staged}, [Requirement("example>=2")])
        with self.assertRaisesRegex(RuntimeError, "not installed consistently"):
            _validate_environment({}, {"example": staged}, [Requirement("example>=2"), Requirement("example<2")])

    def test_new_release_requires_restart_in_current_process(self):
        (self.folder / "requirements.txt").write_text("example==2.0\n", encoding="utf-8")
        root = environment_root()
        release = root / "releases" / "new"
        release.mkdir(parents=True)
        (root / "active").symlink_to(release)
        disk = SimpleNamespace(version="2.0", metadata={"Name": "example"})
        with patch("plugin.dependencies._on_disk", return_value=({}, {"example": disk})), patch(
            "plugin.dependencies._distributions", return_value={}
        ), patch("labsmanager.plugin_package_runtime.LOADED_PACKAGE_PATH", None):
            result = diagnose("broken", {"broken": self.candidate})
        self.assertEqual(result["state"], "restart_required")
        self.assertFalse(result["can_install"])

    def test_old_failed_operation_does_not_block_ready_plugin(self):
        (self.folder / "requirements.txt").write_text("example==2.0\n", encoding="utf-8")
        _write_operation({"id": "old", "key": "broken", "state": "failed", "message": "Earlier failure"})
        dist = SimpleNamespace(version="2.0", metadata={"Name": "example"})
        with patch("plugin.dependencies._on_disk", return_value=({"example": dist}, {})), patch(
            "plugin.dependencies._distributions", return_value={"example": dist}
        ):
            result = diagnose("broken", {"broken": self.candidate})
        self.assertEqual(result["state"], "satisfied")
        self.assertFalse(result["can_install"])

    def test_transitive_conflict_blocks_activation_after_environment_change(self):
        (self.folder / "requirements.txt").write_text("example==2.0\n", encoding="utf-8")
        dist = SimpleNamespace(version="2.0", metadata={"Name": "example"}, requires=["shared>=3"])
        shared = SimpleNamespace(version="2.0", metadata={"Name": "shared"}, requires=[])
        installed = {"example": dist, "shared": shared}
        with patch("plugin.dependencies._on_disk", return_value=(installed, {})), patch(
            "plugin.dependencies._distributions", return_value=installed
        ):
            result = diagnose("broken", {"broken": self.candidate})
        self.assertEqual(result["state"], "incompatible")
        self.assertFalse(result["can_install"])


class DependencyAdminTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user("package-admin", is_staff=True)
        self.reader = get_user_model().objects.create_user("package-reader")
        self.client = APIClient()
        self.config = PluginConfig.objects.create(key="broken", name="Broken")

    def test_install_is_staff_only_and_uses_post(self):
        endpoint = "/api/v1/settings/admin/plugins/broken/dependencies/install/"
        self.client.force_login(self.reader)
        self.assertEqual(self.client.post(endpoint).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(endpoint).status_code, 405)
        with patch("settings.admin_api_v1.request_install", return_value={"state": "queued"}) as start:
            self.assertEqual(self.client.post(endpoint).status_code, 202)
            start.assert_called_once_with("broken")
        csrf_client = APIClient(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin)
        self.assertEqual(csrf_client.post(endpoint).status_code, 403)

    def test_activation_is_blocked_before_registry_reload(self):
        with patch("plugin.dependencies.activation_ready", return_value=False):
            serializer = PluginActivateSerializer()
            with self.assertRaises(Exception):
                serializer.update(self.config, {"active": True})
            with self.assertRaises(DjangoValidationError):
                self.config.activate(True)
        self.assertFalse(PluginConfig.objects.get(pk=self.config.pk).active)
