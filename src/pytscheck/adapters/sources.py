"""Validate and normalize virtual adapter source inputs."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import PurePosixPath, PureWindowsPath

from ..defaults import DEFAULT_MAX_FILES_PER_PROJECT, DEFAULT_MAX_SOURCE_BYTES
from ..models import SourceFile
from .base import CompilerAdapter
from .errors import AdapterProtocolError
from .source_maps import _validate_source_map


def _path_key(path: PurePosixPath) -> str:
    value = path.as_posix()
    return value.casefold() if sys.platform in {"win32", "darwin"} else value


def collect_sources(adapter: CompilerAdapter, project_root: str) -> tuple[SourceFile, ...]:
    """Validate inputs before writing, including portable path collisions."""
    if not isinstance(adapter.name, str) or not adapter.name.strip():
        raise AdapterProtocolError("adapter.name must be a non-empty string")
    if not callable(adapter.get_sources):
        raise AdapterProtocolError("adapter.get_sources must be callable")
    return _validate_sources(adapter.get_sources(project_root))


def _validate_sources(sources: object) -> tuple[SourceFile, ...]:
    """Validate even lower-level virtual checks before any file is written."""
    if not isinstance(sources, (list, tuple)):
        raise AdapterProtocolError("adapter must return a list or tuple of SourceFile objects")
    if len(sources) > DEFAULT_MAX_FILES_PER_PROJECT:
        raise AdapterProtocolError(f"adapter exceeds {DEFAULT_MAX_FILES_PER_PROJECT} sources")
    seen: set[str] = set()
    result: list[SourceFile] = []
    for source in sources:
        if not isinstance(source, SourceFile):
            raise AdapterProtocolError("adapter returned a non-SourceFile object")
        if not isinstance(source.path, str) or not source.path:
            raise AdapterProtocolError("adapter returned an empty path or non-string source path")
        path = PurePosixPath(source.path.replace("\\", "/"))
        if (
            "\x00" in source.path
            or path.is_absolute()
            or PureWindowsPath(source.path).drive
            or ".." in path.parts
            or str(path) == "."
        ):
            raise AdapterProtocolError(f"unsafe source path: {source.path!r}")
        for part in path.parts:
            stem = part.split(".")[0].upper()
            if (
                part.endswith((" ", "."))
                or any(c in part for c in '<>:"|?*')
                or stem in {"CON", "PRN", "AUX", "NUL"}
                or stem in {f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)}
            ):
                raise AdapterProtocolError(f"non-portable source path: {source.path!r}")
        key = _path_key(path)
        if key in seen:
            raise AdapterProtocolError(f"duplicate source path: {source.path!r}")
        seen.add(key)
        if not isinstance(source.text, str) or "\x00" in source.text:
            raise AdapterProtocolError("adapter source text must be a string without NUL bytes")
        if len(source.text) > DEFAULT_MAX_SOURCE_BYTES:
            raise AdapterProtocolError(f"adapter source exceeds {DEFAULT_MAX_SOURCE_BYTES} bytes")
        try:
            size = len(source.text.encode("utf-8"))
        except UnicodeError as exc:
            raise AdapterProtocolError("adapter source text is not valid UTF-8") from exc
        if size > DEFAULT_MAX_SOURCE_BYTES:
            raise AdapterProtocolError(f"adapter source exceeds {DEFAULT_MAX_SOURCE_BYTES} bytes")
        if source.origin_path is not None and not isinstance(source.origin_path, str):
            raise AdapterProtocolError("origin_path must be a string or None")
        if source.source_map is not None and not isinstance(source.source_map, str):
            raise AdapterProtocolError("source_map must be a string or None")
        if source.source_map is not None:
            if len(source.source_map) > DEFAULT_MAX_SOURCE_BYTES:
                raise AdapterProtocolError("source_map exceeds the source-size limit")
            try:
                map_size = len(source.source_map.encode("utf-8"))
            except UnicodeError as exc:
                raise AdapterProtocolError("source_map is not valid UTF-8") from exc
            if map_size > DEFAULT_MAX_SOURCE_BYTES:
                raise AdapterProtocolError("source_map exceeds the source-size limit")
            _validate_source_map(source.source_map, source.path)
        result.append(replace(source, path=path.as_posix()))
    # Detect files that would have to be directories for another source.
    for source in result:
        for parent in PurePosixPath(source.path).parents:
            if _path_key(parent) in seen:
                raise AdapterProtocolError(
                    f"source path conflicts with a directory: {source.path!r}"
                )
    return tuple(result)


__all__ = ["SourceFile", "collect_sources"]
