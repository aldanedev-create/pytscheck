"""Source-map v3 decoding and diagnostic position translation."""

from __future__ import annotations

import json
import posixpath
from bisect import bisect_right
from dataclasses import dataclass, replace
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any
from urllib.parse import urljoin

from ..models import Diagnostic, RelatedInformation, SourceFile
from .errors import AdapterMappingError

_ALPHABET = {
    char: index
    for index, char in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")
}


@dataclass(frozen=True)
class _Position:
    column: int
    file: str | None
    line: int = 0
    original_column: int = 0


def _vlq(segment: str) -> list[int]:
    result = []
    value = shift = 0
    for char in segment:
        if char not in _ALPHABET or shift > 30:
            raise AdapterMappingError("invalid or excessive source-map VLQ value")
        digit = _ALPHABET[char]
        value |= (digit & 31) << shift
        if digit & 32:
            shift += 5
        else:
            magnitude = value >> 1
            result.append(-magnitude if value & 1 else magnitude)
            value = shift = 0
    if shift:
        raise AdapterMappingError("truncated source-map VLQ value")
    if len(result) not in (1, 4, 5):
        raise AdapterMappingError("source-map segment must contain 1, 4 or 5 fields")
    return result


def _source_path(source: str, source_root: str, virtual: str) -> str:
    source = source.replace("\\", "/")
    source_root = source_root.replace("\\", "/")
    if "://" in source or PureWindowsPath(source).drive:
        return source
    if "://" in source_root:
        joined = urljoin(source_root.rstrip("/") + "/", source)
        return joined if "://" in joined else source_root.rstrip("/") + "/" + source
    if PurePosixPath(source).is_absolute():
        return source
    return posixpath.normpath(
        posixpath.join(PurePosixPath(virtual).parent.as_posix(), source_root, source)
    )


def _decode(data: dict[str, Any], virtual: str, depth: int = 0) -> dict[int, list[_Position]]:
    if depth > 16:
        raise AdapterMappingError("indexed source-map nesting exceeds 16 levels")
    if "version" in data and (type(data["version"]) is not int or data["version"] != 3):
        raise AdapterMappingError("only source-map version 3 is supported")
    if "sections" in data:
        sections = data["sections"]
        if not isinstance(sections, list):
            raise AdapterMappingError("source-map sections must be a list")
        combined: dict[int, list[_Position]] = {}
        previous = (-1, -1)
        for section in sections:
            if not isinstance(section, dict) or not isinstance(section.get("offset"), dict):
                raise AdapterMappingError("invalid indexed source-map section")
            offset = section["offset"]
            line, column = offset.get("line"), offset.get("column")
            if type(line) is not int or type(column) is not int or min(line, column) < 0:
                raise AdapterMappingError("source-map section offset must be nonnegative integers")
            if (line, column) <= previous:
                raise AdapterMappingError("source-map sections must have increasing offsets")
            previous = line, column
            inner = section.get("map")
            if not isinstance(inner, dict):
                raise AdapterMappingError(
                    "indexed maps require inline maps; URL sections are unsupported"
                )
            decoded = _decode(inner, virtual, depth + 1)
            # A section boundary ends the previous section's mapping coverage.
            for old_line in list(combined):
                if old_line > line:
                    del combined[old_line]
            combined[line] = [entry for entry in combined.get(line, []) if entry.column < column]
            combined.setdefault(line, []).append(_Position(column, None))
            for inner_line, inner_positions in decoded.items():
                target_line = inner_line + line
                delta = column if inner_line == 0 else 0
                combined.setdefault(target_line, []).extend(
                    replace(position, column=position.column + delta)
                    for position in inner_positions
                )
        for group in combined.values():
            group.sort(key=lambda position: position.column)
        return combined
    mappings = data.get("mappings")
    if not isinstance(mappings, str):
        raise AdapterMappingError(f"source map for {virtual!r} is missing 'mappings' string")
    sources = data.get("sources", [])
    names = data.get("names", [])
    source_root = data.get("sourceRoot", "")
    if (
        not isinstance(source_root, str)
        or not isinstance(sources, list)
        or not all(isinstance(v, str) for v in sources)
    ):
        raise AdapterMappingError("sourceRoot must be a string and sources a list of strings")
    if not isinstance(names, list) or not all(isinstance(v, str) for v in names):
        raise AdapterMappingError("source-map names must be a list of strings")
    result: dict[int, list[_Position]] = {}
    source_index = original_line = original_column = name_index = count = 0
    for generated_line, encoded_line in enumerate(mappings.split(";")):
        generated_column = 0
        positions: list[_Position] = []
        for encoded in encoded_line.split(","):
            if not encoded:
                if encoded_line:
                    raise AdapterMappingError("empty source-map segment")
                continue
            count += 1
            if count > 500_000:
                raise AdapterMappingError("source map exceeds 500,000 segments")
            fields = _vlq(encoded)
            generated_column += fields[0]
            if generated_column < 0 or (positions and generated_column < positions[-1].column):
                raise AdapterMappingError("source-map generated columns must be ordered")
            if len(fields) == 1:
                positions.append(_Position(generated_column, None))
                continue
            source_index += fields[1]
            original_line += fields[2]
            original_column += fields[3]
            if not 0 <= source_index < len(sources) or min(original_line, original_column) < 0:
                raise AdapterMappingError("source-map original source/position is out of range")
            if len(fields) == 5:
                name_index += fields[4]
                if not 0 <= name_index < len(names):
                    raise AdapterMappingError("source-map name index is out of range")
            positions.append(
                _Position(
                    generated_column,
                    _source_path(sources[source_index], source_root, virtual),
                    original_line,
                    original_column,
                )
            )
        if positions:
            result[generated_line] = positions
    return result


def _load(raw: str, virtual: str) -> tuple[dict[str, Any], dict[int, list[_Position]]]:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, RecursionError, TypeError) as exc:
        raise AdapterMappingError(f"source map for {virtual!r} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AdapterMappingError("source map must be a JSON object")
    return data, _decode(data, virtual)


def _validate_source_map(raw: str, virtual_path: str) -> None:
    _load(raw, virtual_path)


def _key(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/")).as_posix()


def remap_diagnostics(
    diagnostics: tuple[Diagnostic, ...], sources: tuple[SourceFile, ...]
) -> tuple[Diagnostic, ...]:
    """Translate positions using same-line greatest-lower-bound v3 mappings.

    Coordinates are converted between compiler 1-based and source-map 0-based
    UTF-16 positions. Unmapped segments retain their generated locations.
    Legacy empty maps without sources retain filename-only remapping.
    """
    by_path = {_key(source.path): source for source in sources}
    maps: dict[str, tuple[dict[str, Any], dict[int, list[_Position]]]] = {}

    def position(file: str | None, line: int, column: int) -> tuple[str, int, int] | None:
        if file is None or _key(file) not in by_path:
            return None
        key = _key(file)
        source = by_path[key]
        if source.source_map is None:
            return (source.origin_path, line, column) if source.origin_path is not None else None
        if key not in maps:
            maps[key] = _load(source.source_map, source.path)
        data, decoded = maps[key]
        if not data.get("sources") and not data.get("sections") and not data.get("mappings"):
            return (source.origin_path, line, column) if source.origin_path is not None else None
        candidates = decoded.get(line - 1, [])
        index = bisect_right([entry.column for entry in candidates], column - 1) - 1
        if index < 0 or candidates[index].file is None:
            return None
        entry = candidates[index]
        assert entry.file is not None
        # A declared single-source origin is an explicit filename override.
        name = (
            source.origin_path
            if source.origin_path is not None and len(data.get("sources", [])) == 1
            else entry.file
        )
        return name, entry.line + 1, entry.original_column + 1

    def related(info: RelatedInformation) -> RelatedInformation:
        mapped = position(info.file, info.line, info.column)
        return replace(info, file=mapped[0], line=mapped[1], column=mapped[2]) if mapped else info

    result = []
    for diagnostic in diagnostics:
        mapped = position(diagnostic.file, diagnostic.line, diagnostic.column)
        changes: dict[str, Any] = {"related": tuple(related(info) for info in diagnostic.related)}
        if mapped:
            changes.update(
                file=mapped[0], line=mapped[1], column=mapped[2], origin_file=diagnostic.file
            )
            if diagnostic.end_line is not None and diagnostic.end_column is not None:
                end = position(diagnostic.file, diagnostic.end_line, diagnostic.end_column)
                changes.update(
                    end_line=end[1] if end and end[0] == mapped[0] else None,
                    end_column=end[2] if end and end[0] == mapped[0] else None,
                )
        result.append(replace(diagnostic, **changes))
    return tuple(result)


__all__ = ["remap_diagnostics"]
