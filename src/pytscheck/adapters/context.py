"""Optional framework-independent context for generated project checking."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeclarationResource:
    """Declarations shipped by a Python package, optionally exposed as a module.

    ``resource`` is a package-relative file or directory. Resources may come
    from ordinary installations or zip importers; no Node installation is needed.
    """

    package: str
    resource: str = "types"
    module: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectContext:
    """Opt into project configuration, real files and declaration resources.

    Paths are relative to the root passed to ``check_project`` unless absolute.
    Caller options override ``compiler_options``, which override tsconfig.
    Generated paths must not overwrite an existing project file.
    """

    tsconfig: str | Path | None = None
    inherit_tsconfig: bool = True
    include_project_files: bool = True
    declaration_paths: tuple[str | Path, ...] = ()
    declaration_resources: tuple[DeclarationResource, ...] = ()
    compiler_options: dict[str, object] = field(default_factory=dict)
    max_workspace_files: int = 100_000
    max_workspace_bytes: int = 512 * 1024 * 1024
