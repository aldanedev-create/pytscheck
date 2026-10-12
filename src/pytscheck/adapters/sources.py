"""SourceFile model and source-collection helpers."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

from ..models import SourceFile
from .base import CompilerAdapter


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
        if not isinstance(s.path, str):
            raise AdapterProtocolError(
                f"adapter {adapter.name!r} returned a non-string source path"
            )
        if not s.path:
            raise AdapterProtocolError(
                f"adapter {adapter.name!r} returned a SourceFile with empty path"
            )
        normalized_path = PurePosixPath(s.path.replace("\\", "/"))
        if (
            "\x00" in s.path
            or normalized_path.is_absolute()
            or PureWindowsPath(s.path).drive
            or ".." in normalized_path.parts
        ):
            raise AdapterProtocolError(
                f"adapter {adapter.name!r} returned unsafe source path: {s.path!r}"
            )
        if s.path in seen:
            raise AdapterProtocolError(
                f"adapter {adapter.name!r} returned duplicate source path: {s.path!r}"
            )
        seen.add(s.path)

    return tuple(sources)


__all__ = ["SourceFile", "collect_sources"]
