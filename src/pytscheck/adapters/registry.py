"""Explicit adapter registration and lookup."""

from __future__ import annotations

from .base import CompilerAdapter
from .errors import AdapterProtocolError, AdapterRegistrationError

_REGISTRY: dict[str, CompilerAdapter] = {}


def register_adapter(adapter: CompilerAdapter) -> None:
    """Register an adapter instance under its ``name``."""
    if not isinstance(adapter, CompilerAdapter) or not callable(adapter.get_sources):
        raise AdapterProtocolError(
            f"object does not satisfy CompilerAdapter protocol: {type(adapter).__name__}"
        )
    if not isinstance(adapter.name, str) or not adapter.name.strip():
        raise AdapterRegistrationError("adapter.name must be a non-empty string")
    if adapter.name in _REGISTRY:
        raise AdapterRegistrationError(f"adapter already registered: {adapter.name!r}")
    _REGISTRY[adapter.name] = adapter


def unregister_adapter(name: str) -> None:
    _REGISTRY.pop(name, None)


def get_adapter(name: str) -> CompilerAdapter:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise AdapterRegistrationError(f"no adapter registered under {name!r}") from exc


def registered_adapters() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


__all__ = [
    "get_adapter",
    "register_adapter",
    "registered_adapters",
    "unregister_adapter",
]
