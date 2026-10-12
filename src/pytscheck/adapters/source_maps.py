"""Source-map parsing and diagnostic remapping.

Phase-3 scope. The public entry point ``remap_diagnostics`` currently
supports the common case: a source map that maps ``SourceFile.path`` back
to ``SourceFile.origin_path`` line-for-line. Full VLQ mapping is a
follow-up; the interface stays the same.
"""

from __future__ import annotations

import json
from dataclasses import replace

from ..models import Diagnostic, SourceFile
from .errors import AdapterMappingError


def remap_diagnostics(
    diagnostics: tuple[Diagnostic, ...],
    sources: tuple[SourceFile, ...],
) -> tuple[Diagnostic, ...]:
    """Rewrite diagnostic file/line/column to original files where possible."""
    # Map virtual path -> SourceFile
    by_path: dict[str, SourceFile] = {s.path: s for s in sources}

    remapped: list[Diagnostic] = []
    for d in diagnostics:
        if d.file is None or d.file not in by_path:
            remapped.append(d)
            continue

        src = by_path[d.file]
        if src.origin_path is None:
            remapped.append(d)
            continue

        # Phase-3 TODO: apply real source-map lookups when src.source_map is set.
        # For now, if a source map is present, parse it to fail loudly on
        # malformed input rather than silently producing wrong positions.
        if src.source_map is not None:
            _validate_source_map(src.source_map, src.path)

        remapped.append(
            replace(
                d,
                file=src.origin_path,
                origin_file=src.path,
            )
        )

    return tuple(remapped)


def _validate_source_map(raw: str, virtual_path: str) -> None:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AdapterMappingError(
            f"source map for {virtual_path!r} is not valid JSON: {exc.msg}"
        ) from exc
    if not isinstance(data, dict) or "mappings" not in data:
        raise AdapterMappingError(f"source map for {virtual_path!r} is missing 'mappings'")


__all__ = ["remap_diagnostics"]
