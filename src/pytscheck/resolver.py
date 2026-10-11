"""Module resolution helpers.

Real resolution is performed by tsgo itself. This module only helps
pytscheck locate tsconfig and package.json files when it needs to reason
about a project before invoking the compiler.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import TSCONFIG_FILENAME, load_tsconfig
from .paths import assert_inside


@dataclass(frozen=True, slots=True)
class ResolvedProject:
    root: Path
    tsconfig: Path | None
    package_json: Path | None
    extends: str | None


def _read_package_json(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def resolve_project(root: Path) -> ResolvedProject:
    """Inspect a project directory for tsconfig/package.json.

    Does not attempt to resolve ``extends`` chains; tsgo does that.
    """
    root = root.resolve()
    tsconfig = root / TSCONFIG_FILENAME
    package_json = root / "package.json"

    extends: str | None = None
    if tsconfig.is_file():
        cfg = load_tsconfig(tsconfig)
        raw = cfg.get("extends")
        if isinstance(raw, str):
            extends = raw
            # Guard against path traversal in a hostile tsconfig.
            candidate = (root / raw).resolve()
            assert_inside(candidate, root, what="tsconfig extends target")

    return ResolvedProject(
        root=root,
        tsconfig=tsconfig if tsconfig.is_file() else None,
        package_json=package_json if package_json.is_file() else None,
        extends=extends,
    )


__all__ = ["ResolvedProject", "resolve_project"]