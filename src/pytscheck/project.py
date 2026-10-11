"""Project-directory helpers."""

from __future__ import annotations

from pathlib import Path

from .config import find_tsconfig
from .defaults import DEFAULT_MAX_FILES_PER_PROJECT, TYPESCRIPT_EXTENSIONS
from .exceptions import ConfigurationError


def iter_typescript_files(root: Path, *, max_files: int = DEFAULT_MAX_FILES_PER_PROJECT) -> tuple[Path, ...]:
    """Yield .ts/.tsx/.mts/.cts files under ``root``, excluding node_modules."""
    found: list[Path] = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part == "node_modules" for part in path.parts):
            continue
        if path.suffix in TYPESCRIPT_EXTENSIONS:
            found.append(path)
        if len(found) > max_files:
            raise ConfigurationError(
                f"project exceeds {max_files} TypeScript files"
            )
    return tuple(sorted(found))


def describe_project(root: Path) -> dict[str, object]:
    """Return a small summary used in diagnostics and docs."""
    tsconfig = find_tsconfig(root)
    return {
        "root": str(root),
        "has_tsconfig": tsconfig is not None,
        "tsconfig_path": str(tsconfig) if tsconfig else None,
    }


__all__ = ["iter_typescript_files", "describe_project"]