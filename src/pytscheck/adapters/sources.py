"""SourceFile model and source-collection helpers."""

from __future__ import annotations

from .base import CompilerAdapter  # noqa: F401  (re-exported for symmetry)
from ..models import SourceFile


def collect_sources(adapter: CompilerAdapter, project_root: str) -> tuple[SourceFile, ...]:
    """Run an adapter's ``get_sources`` and validate the result."""
    from .errors import AdapterProtocolError

    sources = adapter.get_sources(project_root)

    seen: set[str] = set()
    for s in sources:
        if not isinstance(s, SourceFile):
            raise AdapterProtocolError(
                f"adapter {adapter.name!r} returned non-SourceFile: {type(s).__name__}"
            )
        if not s.path:
            raise AdapterProtocolError(
                f"adapter {adapter.name!r} returned a SourceFile with empty path"
            )
        if s.path in seen:
            raise AdapterProtocolError(
                f"adapter {adapter.name!r} returned duplicate source path: {s.path!r}"
            )
        seen.add(s.path)

    return tuple(sources)


__all__ = ["SourceFile", "collect_sources"]