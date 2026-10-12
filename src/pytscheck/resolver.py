"""Module resolution helpers.

Real resolution is performed by tsgo itself. This module only helps
pytscheck locate tsconfig and package.json files when it needs to reason
about a project before invoking the compiler.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .config import load_tsconfig
from .defaults import TSCONFIG_FILENAME
from .exceptions import ConfigurationError
from .paths import assert_inside, assert_no_null_bytes, normalize


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
    root = normalize(root)
    tsconfig = root / TSCONFIG_FILENAME
    package_json = root / "package.json"

    extends: str | None = None
    if tsconfig.is_file():
        try:
            cfg = load_tsconfig(tsconfig)
        except ConfigurationError as validation_error:
            # Projects accept TypeScript JSONC; preserve strings while removing comments.
            try:
                text = tsconfig.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise validation_error from exc
            text = re.sub(
                r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\r\n]*',
                lambda match: match[0] if match[0].startswith('"') else " ",
                text,
            )
            text = re.sub(
                r'"(?:\\.|[^"\\])*"|,\s*([}\]])',
                lambda match: match[0] if match[0].startswith('"') else match[1],
                text,
            )
            try:
                cfg = json.loads(text)
            except (json.JSONDecodeError, RecursionError) as exc:
                raise ConfigurationError(f"invalid JSONC in {tsconfig}: {exc}") from exc
            if not isinstance(cfg, dict):
                raise ConfigurationError(
                    f"{tsconfig}: top-level value must be an object"
                ) from validation_error
        raw = cfg.get("extends")
        if isinstance(raw, str):
            extends = raw
            # Guard against path traversal in a hostile tsconfig.
            assert_no_null_bytes(raw, what="tsconfig extends")
            candidate = normalize(root / raw)
            assert_inside(candidate, root, what="tsconfig extends target")

    return ResolvedProject(
        root=root,
        tsconfig=tsconfig if tsconfig.is_file() else None,
        package_json=package_json if package_json.is_file() else None,
        extends=extends,
    )


__all__ = ["ResolvedProject", "resolve_project"]
