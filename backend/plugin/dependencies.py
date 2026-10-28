"""Read and install ordinary plugin requirements without importing plugin code."""

import fcntl
import importlib.metadata as metadata
import json
import logging
import os
import re
import shutil
import site
import subprocess
import sys
import sysconfig
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.utils.text import slugify
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from labsmanager import plugin_package_runtime as runtime
from labsmanager.plugin_model_apps import literal_metadata
from django.core.exceptions import ImproperlyConfigured


KEY = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PACKAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
RUNNING = {"queued", "running"}
environment_id = runtime.environment_id
logger = logging.getLogger("labsmanager")


def package_root():
    return Path(settings.LAB_PLUGIN_PACKAGES_ROOT).expanduser().resolve()


def environment_root():
    return package_root() / environment_id()


def active_path():
    link = environment_root() / "active"
    if not link.is_symlink():
        return None
    target = link.resolve()
    return target if target.is_dir() and target.parent == environment_root() / "releases" else None


@dataclass(frozen=True)
class Candidate:
    key: str
    directory: Path
    title: str

    @property
    def requirements_file(self):
        return self.directory / "requirements.txt"


def _static_identity(directory):
    """Read literal SLUG/NAME declarations; this never executes plugin code."""
    for source in sorted(directory.glob("*.py")):
        try:
            declarations = list(literal_metadata(source))
        except ImproperlyConfigured:
            continue
        for _, _, values in declarations:
            if isinstance(values.get("SLUG"), str) or isinstance(values.get("NAME"), str):
                name = values.get("SLUG") or values.get("NAME")
                return slugify(name), str(values.get("TITLE") or values.get("NAME") or directory.name)
    return slugify(directory.name), directory.name


def discover_candidates():
    from plugin.registry import registry
    found = {}
    for source in registry.plugin_dirs():
        if isinstance(source, str) and source.startswith("plugin."):
            directory = Path(settings.BASE_DIR).joinpath(*source.split("."))
        else:
            directory = Path(source)
        if not directory.is_dir():
            continue
        for child in directory.iterdir():
            if not child.is_dir() or child.name.startswith("_"):
                continue
            if not any(child.glob("*.py")):
                continue
            key, title = _static_identity(child)
            if KEY.fullmatch(key):
                found.setdefault(key, Candidate(key, child.resolve(), title))
    # Installed entry-point plugins can keep requirements beside their package.
    from plugin.helpers import get_entrypoints
    for entry in get_entrypoints():
        if entry.dist is None:
            continue
        module = entry.value.split(":", 1)[0].split(".", 1)[0]
        try:
            directory = Path(entry.dist.locate_file(module))
        except (OSError, ValueError):
            continue
        if directory.is_dir():
            key, title = _static_identity(directory)
            if KEY.fullmatch(key):
                found.setdefault(key, Candidate(key, directory.resolve(), title))
    return found


def parse_requirements(candidate):
    path = candidate.requirements_file
    if not path.exists():
        return [], []
    try:
        if path.stat().st_size > 65536:
            return [], ["requirements.txt exceeds 64 KiB"]
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return [], ["requirements.txt cannot be read as UTF-8"]
    parsed, errors = [], []
    for line_number, raw in enumerate(lines, 1):
        line = re.split(r"\s+#", raw, maxsplit=1)[0].strip()
        if not line or line.startswith("#"):
            continue
        if len(line) > 512 or line.startswith("-") or "/" in line or "\\" in line or "@" in line:
            errors.append(f"Line {line_number}: unsupported pip reference or option")
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement:
            errors.append(f"Line {line_number}: invalid requirement")
            continue
        if requirement.url or not PACKAGE.fullmatch(requirement.name):
            errors.append(f"Line {line_number}: unsupported direct reference")
            continue
        parsed.append(requirement)
    return parsed, errors


def _distributions(path=None):
    source = metadata.distributions() if path is None else metadata.distributions(path=path)
    return {canonicalize_name(dist.metadata["Name"]): dist for dist in source
            if dist.metadata.get("Name")}


def _core_paths():
    values = [sysconfig.get_paths().get("purelib"), sysconfig.get_paths().get("platlib")]
    values.extend(site.getsitepackages())
    return list(dict.fromkeys(str(Path(value)) for value in values if value))


def _on_disk():
    core = _distributions(_core_paths())
    managed = _distributions([str(active_path())]) if active_path() else {}
    return core, managed


def operation_state():
    path = environment_root() / "operation.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if data.get("state") in RUNNING and time.time() - data.get("updated", 0) > 1200:
        return {**data, "state": "failed", "message": "Installation process stopped or timed out."}
    return data


def _write_operation(data):
    root = environment_root()
    root.mkdir(parents=True, exist_ok=True)
    data = {**data, "updated": time.time()}
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=root, delete=False) as temporary:
        json.dump(data, temporary)
        temporary_name = temporary.name
    os.replace(temporary_name, root / "operation.json")


def diagnose(key, candidates=None):
    candidate = (candidates or discover_candidates()).get(key)
    if candidate is None:
        return None
    requirements, errors = parse_requirements(candidate)
    core, managed = _on_disk()
    loaded = _distributions()
    rows, missing, incompatible = [], False, False
    for requirement in requirements:
        if requirement.marker and not requirement.marker.evaluate():
            continue
        normalized = canonicalize_name(requirement.name)
        disk = core.get(normalized) or managed.get(normalized)
        loaded_dist = loaded.get(normalized)
        disk_version = disk.version if disk else None
        runtime_version = loaded_dist.version if loaded_dist else None
        state = "satisfied" if disk and requirement.specifier.contains(disk.version, prereleases=True) else "incompatible" if disk else "missing"
        missing |= state == "missing"
        incompatible |= state == "incompatible"
        rows.append({"name": requirement.name, "required": str(requirement.specifier) or "*",
                     "installed_version": runtime_version, "on_disk_version": disk_version, "state": state})
    compatibility_errors = []
    if rows and not (errors or missing or incompatible):
        try:
            _validate_environment(core, managed, requirements)
        except RuntimeError as exc:
            incompatible = True
            compatibility_errors.append(str(exc))
    operation = operation_state()
    restart_required = bool(active_path() and str(active_path()) != runtime.LOADED_PACKAGE_PATH
                            and any(row["installed_version"] != row["on_disk_version"] for row in rows))
    if errors:
        state = "invalid"
    elif operation.get("key") == key and operation.get("state") in RUNNING:
        state = operation["state"]
    elif incompatible:
        state = "failed" if operation.get("key") == key and operation.get("state") == "failed" else "incompatible"
    elif missing:
        state = "failed" if operation.get("key") == key and operation.get("state") == "failed" else "missing"
    elif restart_required and rows:
        state = "restart_required"
    else:
        state = "satisfied" if rows else "none"
    return {"key": key, "human_name": candidate.title, "state": state,
            "requirements": rows, "errors": errors + compatibility_errors, "restart_required": restart_required,
            "can_install": bool(rows) and not (errors or compatibility_errors) and state in ("missing", "incompatible", "failed"),
            "operation": operation if operation.get("key") == key else None}


def activation_ready(key):
    diagnostic = diagnose(key)
    return diagnostic is None or diagnostic["state"] in ("none", "satisfied")


def request_install(key):
    """Start a detached management command while holding a cross-process lock."""
    candidates = discover_candidates()
    if not KEY.fullmatch(key) or key not in candidates:
        raise ValueError("Unknown plugin")
    diagnostic = diagnose(key, candidates)
    if diagnostic["state"] in ("invalid", "none") or not diagnostic["can_install"]:
        raise ValueError("This plugin has no installable requirements")
    root = environment_root()
    try:
        root.mkdir(parents=True, exist_ok=True)
        lock = open(root / "install.lock", "a+")
    except OSError as exc:
        raise ValueError("Plugin package store is not writable") from exc
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        lock.close()
        raise ValueError("Another installation is running") from exc
    job_id = uuid.uuid4().hex
    _write_operation({"id": job_id, "key": key, "state": "queued", "message": "Installation queued."})
    command = [sys.executable, str(Path(settings.BASE_DIR) / "manage.py"),
               "install_plugin_dependencies", key, job_id]
    try:
        subprocess.Popen(command, cwd=settings.BASE_DIR, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, pass_fds=(lock.fileno(),))
    except OSError:
        _write_operation({"id": job_id, "key": key, "state": "failed", "message": "Installer could not start."})
        raise ValueError("Installer could not start") from None
    finally:
        lock.close()
    logger.info("Plugin dependency installation queued: %s (%s)", key, job_id)
    return diagnose(key, candidates)


# def _run_pip(args, timeout=600):
#     result = subprocess.run([sys.executable, "-m", "pip", "--disable-pip-version-check", *args],
#                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
#                             stderr=subprocess.DEVNULL, timeout=timeout, check=False)
#     if result.returncode:
#         raise RuntimeError("pip could not resolve or install compatible wheel packages")
def _run_pip(args, timeout=600):
    result = subprocess.run(
        [sys.executable, "-m", "pip", "--disable-pip-version-check", *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )

    if result.returncode:
        raise RuntimeError(
            f"pip failed (exit code {result.returncode}):\n"
            f"{result.stdout[-4000:]}"
        )


def _validate_environment(core, staged, requirements):
    overlap = set(core) & set(staged)
    if overlap:
        raise RuntimeError("Installation would override a core distribution: " + ", ".join(sorted(overlap)[:5]))
    combined = {**staged, **core}
    requested_extras = {}
    for requirement in requirements:
        if requirement.marker and not requirement.marker.evaluate():
            continue
        name = canonicalize_name(requirement.name)
        requested_extras.setdefault(name, set()).update(requirement.extras)
        dist = combined.get(name)
        if dist is None or not requirement.specifier.contains(dist.version, prereleases=True):
            raise RuntimeError("Required distributions were not installed consistently")
    for name, dist in combined.items():
        for raw in getattr(dist, "requires", None) or ():
            try:
                required = Requirement(raw)
            except InvalidRequirement:
                continue
            extras = {"", *requested_extras.get(name, set())}
            if required.marker and not any(required.marker.evaluate({"extra": extra}) for extra in extras):
                continue
            dependency = combined.get(canonicalize_name(required.name))
            if dependency is None or not required.specifier.contains(dependency.version, prereleases=True):
                raise RuntimeError("Installed distribution requirements are incompatible")


def install(key, job_id):
    """Run only from the detached management command; publish a new release atomically."""
    operation = operation_state()
    if operation.get("id") != job_id or operation.get("key") != key:
        raise RuntimeError("Unknown installation operation")
    _write_operation({"id": job_id, "key": key, "state": "running", "message": "Installing dependencies."})
    try:
        candidates = discover_candidates()
        if key not in candidates:
            raise RuntimeError("Plugin directory no longer exists")
        selected = []
        for candidate in candidates.values():
            if candidate.key != key:
                continue
            selected.append(candidate)
        from plugin.models import PluginConfig
        for config in PluginConfig.objects.filter(active=True):
            candidate = candidates.get(config.key)
            if candidate and candidate not in selected:
                selected.append(candidate)
        requirements = []
        for candidate in selected:
            parsed, errors = parse_requirements(candidate)
            if errors:
                raise RuntimeError("A selected plugin has invalid requirements")
            requirements.extend(parsed)
        core, previous = _on_disk()
        # Preserve installed packages when a plugin is deactivated. A changed
        # version requires an explicit operator cleanup rather than a surprise upgrade.
        frozen = [Requirement(f"{dist.metadata['Name']}=={dist.version}") for dist in previous.values()]
        requirements.extend(frozen)
        for requirement in requirements:
            dist = core.get(canonicalize_name(requirement.name))
            if dist and (not requirement.marker or requirement.marker.evaluate()) and not requirement.specifier.contains(dist.version, prereleases=True):
                raise RuntimeError("Plugin requirement conflicts with a core distribution")
        root = environment_root()
        releases = root / "releases"
        releases.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            temporary = Path(temporary)
            requested = temporary / "requirements.txt"
            requested.write_text("\n".join(str(item) for item in requirements) + "\n", encoding="utf-8")
            constraints = temporary / "core-constraints.txt"
            constraints.write_text("\n".join(f"{dist.metadata['Name']}=={dist.version}" for dist in core.values()) + "\n",
                                   encoding="utf-8")
            report = temporary / "report.json"
            _run_pip(["install", "--dry-run", "--report", str(report), "--only-binary=:all:",
                      "-c", str(constraints), "-r", str(requested)])
            planned = json.loads(report.read_text(encoding="utf-8")).get("install", [])
            stage = temporary / "stage"
            previous_release = active_path()
            if previous_release:
                shutil.copytree(previous_release, stage)
            else:
                stage.mkdir()
            for item in planned:
                name = item.get("metadata", {}).get("name", "")
                version = item.get("metadata", {}).get("version", "")
                if not PACKAGE.fullmatch(name) or not version or item.get("is_direct"):
                    raise RuntimeError("pip selected an unsupported distribution source")
                _run_pip(["install", "--target", str(stage), "--no-deps", "--only-binary=:all:", f"{name}=={version}"])
            staged = _distributions([str(stage)])
            if {canonicalize_name(item["metadata"]["name"]) for item in planned} | set(previous) != set(staged):
                raise RuntimeError("Staged distributions do not match pip resolution")
            _validate_environment(core, staged, requirements)
            release = releases / uuid.uuid4().hex
            os.replace(stage, release)
            next_link = root / f"active-{uuid.uuid4().hex}"
            try:
                next_link.symlink_to(release)
                os.replace(next_link, root / "active")
            finally:
                next_link.unlink(missing_ok=True)
        _write_operation({"id": job_id, "key": key, "state": "restart_required",
                          "message": "Installed. Restart all Django web and worker processes."})
        logger.info("Plugin dependency installation published: %s (%s)", key, job_id)
    except Exception as exc:
        _write_operation({"id": job_id, "key": key, "state": "failed", "message": str(exc)[-4000:]})
        logger.warning("Plugin dependency installation failed: %s (%s): %s", key, job_id, exc)
        raise
