"""
TRINKER - Load user plugins from data/plugins/ directories.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from ..core.config import DATA_DIR
from ..core.logger import logger

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def load_plugins() -> int:
    """Import *.py plugins that call register(). Returns count loaded."""
    search_dirs = [
        _PROJECT_ROOT / "data" / "plugins",
        DATA_DIR / "plugins",
    ]
    loaded = 0
    for directory in search_dirs:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.py")):
            if path.name.startswith("_"):
                continue
            if _load_plugin_file(path):
                loaded += 1
    if loaded:
        logger.info("Loaded %d plugin(s).", loaded)
    return loaded


def _load_plugin_file(path: Path) -> bool:
    module_name = f"trinker_plugin_{path.stem}"
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return False
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        logger.debug("Plugin loaded: %s", path.name)
        return True
    except Exception as exc:
        logger.warning("Plugin failed to load (%s): %s", path.name, exc)
        return False
