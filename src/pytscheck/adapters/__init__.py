"""Compiler-agnostic adapter system.

Adapters let external Python tools submit generated TypeScript and receive
diagnostics mapped back to their own source files. The pytscheck core never
imports a specific adapter; tools register theirs through the
``pytscheck.adapters`` entry-point group.
"""

from __future__ import annotations

from .base import CompilerAdapter
from .errors import (
    AdapterError,
    AdapterExtractionError,
    AdapterMappingError,
    AdapterProtocolError,
    AdapterRegistrationError,
)
from .registry import get_adapter, register_adapter, unregister_adapter
from .source_maps import remap_diagnostics
from .sources import collect_sources

__all__ = [
    "AdapterError",
    "AdapterExtractionError",
    "AdapterMappingError",
    "AdapterProtocolError",
    "AdapterRegistrationError",
    "CompilerAdapter",
    "collect_sources",
    "get_adapter",
    "register_adapter",
    "remap_diagnostics",
    "unregister_adapter",
]
