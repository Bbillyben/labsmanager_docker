"""Resolve a plugin's local Vite manifest to same-origin static URLs."""

import hashlib
import json
import re
from pathlib import Path

from django.conf import settings


ASSET = re.compile(r"^assets/[A-Za-z0-9_.-]+\.(?:js|css)$")


def module_assets(plugin, module):
    """Return immutable entry URLs; never accept a plugin supplied script URL."""
    dist = Path(plugin.path()) / "frontend" / "dist"
    manifest_file = dist / "manifest.json"
    if not manifest_file.is_file() or manifest_file.stat().st_size > 1024 * 1024:
        raise ValueError("Plugin UI manifest missing or too large")
    contents = manifest_file.read_bytes()
    manifest = json.loads(contents)
    if not isinstance(manifest, dict):
        raise ValueError("Invalid plugin UI manifest")
    entries = [value for value in manifest.values()
               if isinstance(value, dict) and value.get("isEntry") is True and value.get("name") == module]
    if len(entries) != 1:
        raise ValueError("Plugin UI entry missing or ambiguous")
    entry = entries[0]
    files = [entry.get("file"), *(entry.get("css") or [])]
    if not isinstance(entry.get("css", []), list) or not files or any(
        not isinstance(file, str) or not ASSET.fullmatch(file)
        or not (dist / file).is_file() or not (dist / file).resolve().is_relative_to(dist.resolve())
        for file in files
    ):
        raise ValueError("Invalid plugin UI asset")
    version = hashlib.sha256(contents).hexdigest()[:16]
    prefix = f"/{settings.STATIC_URL.strip('/')}/plugins/{plugin.slug}/"
    urls = [f"{prefix}{file}?v={version}" for file in files]
    return {"module_url": urls[0], "css_urls": urls[1:], "asset_version": version}
