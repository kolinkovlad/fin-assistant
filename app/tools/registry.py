# app/tools/registry.py
from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType
from typing import Dict

from .base import BaseTool

_registry: Dict[str, BaseTool] = {}  # name → instance
_DISCOVERED = False

def get(name: str) -> BaseTool:
    _ensure_populated()
    try:
        return _registry[name]
    except KeyError as exc:
        available = ', '.join(_registry) or '∅'
        raise KeyError(
            f'Tool “{name}” not found. Currently registered: [{available}]'
        ) from exc


def all_tools() -> Dict[str, BaseTool]:
    _ensure_populated()
    return _registry


def register(tool: BaseTool) -> None:
    if tool.name in _registry:
        raise ValueError(f'Tool {tool.name!r} already registered')
    _registry[tool.name] = tool


def _ensure_populated() -> None:
    global _DISCOVERED
    if _DISCOVERED:
        return
    _auto_discover_modules()
    _DISCOVERED = True


def _auto_discover_modules() -> None:
    """
    Import every sub-module under app.tools.* so that each
    module-level `register()` call executes exactly once.
    """
    pkg = importlib.import_module(__name__.rsplit('.', 1)[0])  # → app.tools
    for _loader, mod_name, _is_pkg in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + '.'):
        _import_safely(mod_name)


def _import_safely(mod_name: str) -> ModuleType | None:
    try:
        return importlib.import_module(mod_name)
    except Exception as exc:  # keep your app alive if one tool is broken
        import logging
        logging.getLogger(__name__).warning(
            'Failed to import %s during tool discovery: %s', mod_name, exc
        )
        return None
