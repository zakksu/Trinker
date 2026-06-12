"""TRINKER 3.0 plugin hooks."""

from .registry import emit, list_hooks, register

__all__ = ["register", "emit", "list_hooks"]
