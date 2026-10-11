"""Path normalization and safety helpers."""

from __future__ import annotations

import os
from pathlib import Path

from .exceptions import ConfigurationError


def normalize(path: str | os.PathLike[str]) -> Path:
    """Expand ``~`` and resolve to an absolute path."""
    return Path(path).expanduser().resolve()


def is_inside(child: Path, parent: Path) -> bool:
    """Return True if ``child`` is inside ``parent`` (after resolution)."""
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def assert_inside(child: Path, parent: Path, *, what: str = "path") -> None:
    """Raise :class:`ConfigurationError` if ``child`` escapes ``parent``."""
    if not is_inside(child, parent):
        raise ConfigurationError(
            f"{what} escapes its root: {child!s} is not under {parent!s}"
        )


def assert_no_null_bytes(value: str, *, what: str = "value") -> None:
    """Reject strings containing NUL, which are invalid in argv and paths."""
    if "\x00" in value:
        raise ConfigurationError(f"{what} contains a NUL byte")


__all__ = [
    "normalize",
    "is_inside",
    "assert_inside",
    "assert_no_null_bytes",
]