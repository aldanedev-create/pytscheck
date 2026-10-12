"""Compiler configuration: tsconfig discovery and option validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .defaults import TSCONFIG_FILENAME
from .exceptions import ConfigurationError


@dataclass(frozen=True, slots=True)
class CompilerOptions:
    """Resolved compiler options passed to tsgo.

    This is a *narrow* view: only the flags pytscheck invokes directly.
    tsconfig-driven options are honored by pointing tsgo at the project
    directory and letting it read ``tsconfig.json`` itself.
    """

    strict: bool = True
    no_emit: bool = True
    skip_lib_check: bool = False
    types: tuple[str, ...] = ()
    lib: tuple[str, ...] = ()
    target: str | None = None
    module: str | None = None
    module_resolution: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def find_tsconfig(project_root: Path) -> Path | None:
    """Return ``project_root/tsconfig.json`` if it exists."""
    candidate = project_root / TSCONFIG_FILENAME
    return candidate if candidate.is_file() else None


def load_tsconfig(path: Path) -> dict[str, Any]:
    """Load and lightly validate a tsconfig.json.

    TypeScript's tsconfig accepts JSONC (comments + trailing commas).
    We do a strict JSON parse for now; JSONC support is a Phase-3 TODO.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ConfigurationError(f"cannot read {path}: {exc}") from exc

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ConfigurationError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigurationError(f"{path}: top-level value must be an object")
    return data


def validate_project_root(path: Path) -> Path:
    """Ensure a project directory exists and is a directory."""
    path = path.expanduser().resolve()
    if not path.exists():
        raise ConfigurationError(f"project path does not exist: {path}")
    if not path.is_dir():
        raise ConfigurationError(f"project path is not a directory: {path}")
    return path


__all__ = [
    "CompilerOptions",
    "find_tsconfig",
    "load_tsconfig",
    "validate_project_root",
]
