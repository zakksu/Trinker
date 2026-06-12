"""
TRINKER 3.0 - Plugin hook registry (extensibility stub).
"""

from __future__ import annotations

from typing import Any, Callable

from ..core.logger import logger

_HOOKS: dict[str, list[Callable[..., Any]]] = {}


def register(hook_name: str, callback: Callable[..., Any]) -> None:
    """Register a plugin callback for a named hook."""
    _HOOKS.setdefault(hook_name, []).append(callback)
    logger.debug("Plugin hook registered: %s", hook_name)


def emit(hook_name: str, **payload: Any) -> list[Any]:
    """Run all callbacks for a hook; returns non-None results."""
    results: list[Any] = []
    for cb in _HOOKS.get(hook_name, []):
        try:
            out = cb(**payload)
            if out is not None:
                results.append(out)
        except Exception as exc:
            logger.warning("Plugin hook %s failed: %s", hook_name, exc)
    return results


def list_hooks() -> list[str]:
    return sorted(_HOOKS.keys())
