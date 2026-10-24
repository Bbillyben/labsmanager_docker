"""Add the active plugin package release after the Python core environment."""

import platform
import re
import sys
import sysconfig
from pathlib import Path

LOADED_PACKAGE_PATH = None


def environment_id():
    values = (f"py{sys.version_info.major}{sys.version_info.minor}", platform.system().lower(),
              platform.machine().lower(), sys.implementation.cache_tag or "none",
              sysconfig.get_config_var("SOABI") or "none")
    return re.sub(r"[^A-Za-z0-9_.-]", "_", "-".join(values))


def bootstrap_package_path(root):
    global LOADED_PACKAGE_PATH
    link = Path(root).expanduser().resolve() / environment_id() / "active"
    if link.is_symlink():
        target = link.resolve()
        if target.is_dir() and target.parent == link.parent / "releases":
            LOADED_PACKAGE_PATH = str(target)
            if LOADED_PACKAGE_PATH not in sys.path:
                sys.path.append(LOADED_PACKAGE_PATH)
