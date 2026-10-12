"""Compiler configuration: tsconfig discovery and option validation."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .defaults import TSCONFIG_FILENAME
from .exceptions import ConfigurationError
from .paths import assert_no_null_bytes


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


def validate_options(options: CompilerOptions) -> None:
    """Reject malformed option containers before creating compiler arguments."""
    if not isinstance(options, CompilerOptions):
        raise ConfigurationError("options must be CompilerOptions")
    for name in ("strict", "no_emit", "skip_lib_check"):
        if not isinstance(getattr(options, name), bool):
            raise ConfigurationError(f"{name} must be a bool")
    for name in ("types", "lib"):
        value = getattr(options, name)
        if not isinstance(value, (tuple, list)):
            raise ConfigurationError(f"{name} must be a tuple or list of strings")
        for item in value:
            if not isinstance(item, str) or not item.strip() or "," in item:
                raise ConfigurationError(f"{name} entries must be non-empty individual names")
            _validate_option_text(item, name)
    for name in ("target", "module", "module_resolution"):
        value = getattr(options, name)
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                raise ConfigurationError(f"{name} must be a non-empty string or None")
            _validate_option_text(value, name)
    if not isinstance(options.extra, dict):
        raise ConfigurationError("extra must be a dictionary")
    for key, value in options.extra.items():
        if value is not None and not isinstance(value, (str, int, float, bool)):
            raise ConfigurationError("extra values must be strings, numbers, bools, or None")
        if isinstance(value, float) and not math.isfinite(value):
            raise ConfigurationError("extra numeric values must be finite")
        if not isinstance(key, str) or not key.strip():
            raise ConfigurationError("extra keys must be non-empty strings")
        _validate_option_text(key, "extra option key")
        if isinstance(value, str):
            _validate_option_text(value, f"value for {key}")
        bare = key[2:] if key.startswith("--") else key
        if (
            not bare
            or not bare[0].isalpha()
            or any(not (char.isalnum() or char == "-") for char in bare)
        ):
            raise ConfigurationError(f"invalid extra option key: {key!r}")


def _validate_option_text(value: str, what: str) -> None:
    assert_no_null_bytes(value, what=what)
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise ConfigurationError(f"{what} is not valid UTF-8") from exc
