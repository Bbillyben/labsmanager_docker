"""Find model-bearing plugin apps before Django populates its app registry.

Only literal declarations are read. This module must not import plugin code or
the Django ORM: settings imports it before ``django.setup()``.
"""

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.text import slugify


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$")


@dataclass(frozen=True)
class ModelApp:
    """Literal Django app identity discovered from plugin source before setup."""

    slug: str
    app_config: str
    name: str
    label: str
    directory: Path


def literal_metadata(source):
    """Yield class names, direct bases, and literal assignments from source.

    The AST scan deliberately avoids importing plugin code before Django's
    app registry exists. Nonliteral or inherited declarations are ignored.

    Raises:
        ImproperlyConfigured: The source cannot be read or parsed.
    """
    try:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    except (OSError, SyntaxError, UnicodeError) as exc:
        raise ImproperlyConfigured(f"Cannot read plugin declaration {source}: {exc}") from exc
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        bases = {base.id for base in node.bases if isinstance(base, ast.Name)}
        values = {}
        for statement in node.body:
            if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Constant):
                for target in statement.targets:
                    if isinstance(target, ast.Name):
                        values[target.id] = statement.value.value
        yield node.name, bases, values


def source_directories(base_dir, external_dirs=()):
    """Return builtin, sample, and configured external plugin roots.

    Existing external roots add their parent to ``sys.path`` so Django can
    import their AppConfigs and models by the same package name as the normal
    registry. Changing this list requires a process restart.
    """
    roots = [
        (Path(base_dir) / "plugin" / "builtin", "plugin.builtin"),
        (Path(base_dir) / "plugin" / "samples", "plugin.samples"),
    ]
    for raw in external_dirs:
        path = Path(raw).expanduser().resolve()
        if path.is_dir():
            roots.append((path, path.name))
            # Django imports AppConfig and models from the persistent volume.
            # A process restart is required after changing this list.
            if str(path.parent) not in sys.path:
                sys.path.insert(1, str(path.parent))
    return roots


def discover_model_apps(base_dir, external_dirs=()):
    """Discover ModelMixin apps and reject conflicting Django identities.

    Only direct ModelMixin inheritance and literal plugin/AppConfig metadata
    qualify. Package names, app labels, and plugin slugs must remain stable
    after migrations are applied. Both builtin and external roots use their
    full import paths; duplicate copies fail discovery.

    Returns:
        Mapping from normalized plugin slug to ``ModelApp`` metadata.

    Raises:
        ImproperlyConfigured: A model plugin has an invalid or duplicate
            declaration, app name, label, or plugin slug.
    """
    found, names, labels, plugin_slugs = {}, {}, {}, {}
    for root, package in source_directories(base_dir, external_dirs):
        if not root.is_dir():
            continue
        for directory in sorted(root.iterdir()):
            if not directory.is_dir() or directory.name.startswith("_"):
                continue
            for source in sorted(directory.glob("*.py")):
                try:
                    declarations = list(literal_metadata(source))
                except ImproperlyConfigured:
                    # A broken unrelated plugin was historically skipped by the
                    # normal registry; only model declarations must fail early.
                    if "ModelMixin" in source.read_text(encoding="utf-8", errors="ignore"):
                        raise
                    continue
                for _, bases, values in declarations:
                    if "LabManagerPlugin" in bases:
                        key = values.get("SLUG") or values.get("NAME")
                        if isinstance(key, str) and key.strip():
                            plugin_slugs.setdefault(slugify(key.lower()), []).append(source)
                    if "ModelMixin" not in bases:
                        continue
                    slug_value = values.get("SLUG") or values.get("NAME")
                    app_config = values.get("DJANGO_APP")
                    if not isinstance(slug_value, str) or not slug_value.strip() or not isinstance(app_config, str):
                        raise ImproperlyConfigured(f"ModelMixin requires literal SLUG/NAME and DJANGO_APP in {source}")
                    slug = slugify(slug_value.lower())
                    if (not slug or not IDENTIFIER.fullmatch(package.split('.')[-1])
                            or not (root / "__init__.py").is_file()
                            or not IDENTIFIER.fullmatch(directory.name)
                            or not (directory / "__init__.py").is_file()):
                        raise ImproperlyConfigured(f"Invalid model plugin slug or package: {directory}")
                    expected = f"{package}.{directory.name}"
                    module, separator, config_class = app_config.rpartition(".")
                    if not separator or module != f"{expected}.apps" or not IDENTIFIER.fullmatch(config_class):
                        raise ImproperlyConfigured(f"Invalid DJANGO_APP for {slug}: expected {expected}.apps.<AppConfig>")
                    config_file = directory / "apps.py"
                    configs = [(name, values) for name, bases, values in literal_metadata(config_file)
                               if name == config_class and "AppConfig" in bases]
                    if len(configs) != 1:
                        raise ImproperlyConfigured(f"Missing AppConfig {app_config}")
                    config_values = configs[0][1]
                    name, label = config_values.get("name"), config_values.get("label")
                    if name != expected or not isinstance(label, str) or not IDENTIFIER.fullmatch(label):
                        raise ImproperlyConfigured(f"AppConfig {app_config} needs literal name={expected!r} and a valid label")
                    for value, owner, kind in ((slug, found, "plugin slug"), (name, names, "app name"),
                                               (label, labels, "app label")):
                        if value in owner:
                            raise ImproperlyConfigured(f"Duplicate {kind} {value!r}: {owner[value]} and {directory}")
                    app = ModelApp(slug, app_config, name, label, directory)
                    found[slug] = app
                    names[name] = directory
                    labels[label] = directory
    for slug, sources in plugin_slugs.items():
        if slug in found and len(sources) > 1:
            raise ImproperlyConfigured(f"Duplicate plugin slug {slug!r}: {', '.join(map(str, sources))}")
    return found


def discover_plugin_static_dirs(base_dir, external_dirs=()):
    """List built plugin UI directories for Django static-file discovery.

    Plugins need a ``frontend/dist/manifest.json`` and literal plugin identity.
    Duplicate static slugs are rejected independently of ModelMixin usage.
    """
    locations = []
    seen = set()
    for root, _ in source_directories(base_dir, external_dirs):
        if not root.is_dir():
            continue
        for directory in sorted(root.iterdir()):
            dist = directory / "frontend" / "dist"
            if not directory.is_dir() or not (dist / "manifest.json").is_file():
                continue
            for source in sorted(directory.glob("*.py")):
                try:
                    declarations = list(literal_metadata(source))
                except ImproperlyConfigured:
                    continue
                for _, bases, values in declarations:
                    if "LabManagerPlugin" not in bases:
                        continue
                    identity = values.get("SLUG") or values.get("NAME")
                    if not isinstance(identity, str):
                        continue
                    slug = slugify(identity.lower())
                    if not slug or slug in seen:
                        raise ImproperlyConfigured(f"Duplicate or invalid plugin static slug: {slug!r}")
                    seen.add(slug)
                    locations.append((f"plugins/{slug}", str(dist)))
    return locations
