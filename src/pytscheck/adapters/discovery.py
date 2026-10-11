"""Entry-point discovery for third-party adapters."""

from __future__ import annotations

from importlib.metadata import entry_points

from ..defaults import DEFAULT_ADAPTER_ENTRY_POINT_GROUP
from .base import CompilerAdapter
from .errors import AdapterDiscoveryError
from .registry import register_adapter


def discover_adapters(
    group: str = DEFAULT_ADAPTER_ENTRY_POINT_GROUP,
) -> tuple[str, ...]:
    """Discover and register all adapters advertised under ``group``.

    Returns the names of adapters that were newly registered.
    """
    registered: list[str] = []
    try:
        eps = entry_points(group=group)
    except Exception as exc:  # pragma: no cover - importlib.metadata is stable
        raise AdapterDiscoveryError(f"entry-point discovery failed: {exc}") from exc

    for ep in eps:
        try:
            obj = ep.load()
        except Exception as exc:
            raise AdapterDiscoveryError(
                f"failed to load adapter entry point {ep.name!r}: {exc}"
            ) from exc

        adapter = obj() if isinstance(obj, type) else obj
        if not isinstance(adapter, CompilerAdapter):
            raise AdapterDiscoveryError(
                f"entry point {ep.name!r} did not yield a CompilerAdapter"
            )
        register_adapter(adapter)
        registered.append(adapter.name)

    return tuple(registered)


__all__ = ["discover_adapters"]