"""Public API surface.

This module is the *only* recommended import path for end users:

    from pytscheck.api import check, check_file, check_project

or, once Phase 2 lands and the bundled binary is guaranteed:

    from pytscheck import check, check_file, check_project

The functions here are thin orchestrators. All real work lives in
:mod:`pytscheck.checker` (invocation), :mod:`pytscheck.protocol` (parsing),
and — when an adapter is supplied — :mod:`pytscheck.adapters`.

Design rules enforced here:

- Unknown keyword arguments are rejected, not silently ignored.
- Adapter failures raise :class:`AdapterError` subclasses; they never
  surface as type errors.
- Operational failures (missing binary, timeout, unparsable output) raise
  :class:`PyTSCheckError` subclasses; they never return ``Result(success=True)``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .config import CompilerOptions
from .exceptions import ConfigurationError
from .models import Result
from .paths import normalize

if TYPE_CHECKING:  # pragma: no cover - import for typing only
    from .adapters.base import CompilerAdapter

__all__ = [
    "check",
    "check_file",
    "check_project",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _coerce_options(
    options: CompilerOptions | dict[str, Any] | None,
) -> CompilerOptions:
    """Accept either a CompilerOptions instance or a plain dict of overrides."""
    if options is None:
        return CompilerOptions()
    if isinstance(options, CompilerOptions):
        return options
    if isinstance(options, dict):
        return CompilerOptions(**options)
    raise ConfigurationError(
        f"options must be CompilerOptions, dict, or None; got {type(options).__name__}"
    )


def _check_adapter(
    adapter: CompilerAdapter,
    project_root: Path,
    *,
    options: CompilerOptions,
    keep_raw: bool,
) -> Result:
    """Run the adapter-aware project path.

    Kept in a helper so `import pytscheck` does not eagerly pull adapter
    modules when the caller never uses them.
    """
    from .adapters.compatibility import check_protocol_version
    from .adapters.errors import AdapterError, AdapterExtractionError
    from .adapters.source_maps import remap_diagnostics
    from .adapters.sources import collect_sources
    from .checker import check_sources_virtual

    check_protocol_version(adapter)

    # Adapter failures must not be confused with type errors.
    try:
        sources = collect_sources(adapter, str(project_root))
    except AdapterError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise AdapterExtractionError(
            f"adapter {adapter.name!r} raised during source collection: {exc}"
        ) from exc

    result = check_sources_virtual(
        sources,
        options=options,
        keep_raw=keep_raw,
    )

    if any(s.origin_path is not None for s in sources):
        remapped = remap_diagnostics(result.diagnostics, sources)
        # Rebuild the Result with remapped diagnostics preserving everything else.
        from .diagnostics import count_errors

        result = Result(
            success=count_errors(remapped) == 0,
            diagnostics=remapped,
            compiler_version=result.compiler_version,
            elapsed_seconds=result.elapsed_seconds,
            raw_output=result.raw_output,
        )

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check(
    source: str,
    *,
    filename: str = "input.ts",
    options: CompilerOptions | dict[str, Any] | None = None,
    keep_raw: bool = False,
) -> Result:
    """Type-check an in-memory TypeScript source string.

    Args:
        source: The TypeScript source text.
        filename: Virtual filename used for diagnostics. Defaults to
            ``"input.ts"``. Only the basename is used; path separators are
            not honored.
        options: Optional :class:`~pytscheck.config.CompilerOptions` or a
            plain dict of its fields.
        keep_raw: If True, the raw compiler output is attached to the
            :class:`~pytscheck.models.Result`.

    Returns:
        A :class:`~pytscheck.models.Result` whose ``errors`` and
        ``warnings`` are tuples of :class:`~pytscheck.models.Diagnostic`.

    Raises:
        ConfigurationError: invalid ``filename`` or ``options``.
        CompilerNotFoundError: the bundled binary is missing.
        CompilerTimeoutError: tsgo exceeded the timeout.
        CompilerExecutionError: tsgo crashed or produced no parsable output.
        OutputParseError: tsgo output could not be parsed.

    Example:
        >>> from pytscheck.api import check
        >>> result = check('const age: number = "twenty";')
        >>> result.success
        False
        >>> bool(result.errors)
        True
    """
    if "\x00" in source:
        raise ConfigurationError("source contains a NUL byte")
    if "\x00" in filename:
        raise ConfigurationError("filename contains a NUL byte")
    if "/" in filename or "\\" in filename:
        raise ConfigurationError(f"filename must be a bare basename, got {filename!r}")

    opts = _coerce_options(options)

    from .checker import check_source

    return check_source(
        source,
        filename=filename,
        options=opts,
        keep_raw=keep_raw,
    )


def check_file(
    path: str | Path,
    *,
    options: CompilerOptions | dict[str, Any] | None = None,
    keep_raw: bool = False,
) -> Result:
    """Type-check a single TypeScript file on disk.

    Args:
        path: Path to a ``.ts``, ``.tsx``, ``.mts``, ``.cts``, or ``.d.ts`` file.
        options: See :func:`check`.
        keep_raw: See :func:`check`.

    Returns:
        A :class:`~pytscheck.models.Result`.

    Raises:
        ConfigurationError: the path does not exist or is not a file.
        (plus everything :func:`check` raises)
    """
    target = normalize(path)
    if not target.exists():
        raise ConfigurationError(f"file does not exist: {target}")
    if not target.is_file():
        raise ConfigurationError(f"path is not a file: {target}")

    opts = _coerce_options(options)

    from .checker import check_file as _check_file

    return _check_file(target, options=opts, keep_raw=keep_raw)


def check_project(
    project_root: str | Path,
    *,
    options: CompilerOptions | dict[str, Any] | None = None,
    adapter: "CompilerAdapter | None" = None,  # noqa: UP037 -- Preserve the frozen public annotation.
    keep_raw: bool = False,
) -> Result:
    """Type-check a TypeScript project directory.

    If ``adapter`` is supplied, the adapter is asked for the sources to
    check and diagnostics are remapped back to the adapter's original files.
    Otherwise the directory is checked directly via its ``tsconfig.json``
    (or, if none exists, by walking for ``.ts`` / ``.tsx`` files).

    Args:
        project_root: Directory containing the project.
        options: See :func:`check`.
        adapter: An object satisfying the
            :class:`~pytscheck.adapters.base.CompilerAdapter` protocol.
        keep_raw: See :func:`check`.

    Returns:
        A :class:`~pytscheck.models.Result`. When an adapter is used,
        diagnostic ``file`` values point at the adapter's ``origin_path``
        and ``origin_file`` records the virtual path.

    Raises:
        ConfigurationError: the directory does not exist or is not a directory.
        AdapterError: the adapter failed to extract or map sources.
        (plus everything :func:`check` raises)
    """
    root = normalize(project_root)
    if not root.exists():
        raise ConfigurationError(f"project path does not exist: {root}")
    if not root.is_dir():
        raise ConfigurationError(f"project path is not a directory: {root}")

    opts = _coerce_options(options)

    if adapter is not None:
        return _check_adapter(
            adapter,
            root,
            options=opts,
            keep_raw=keep_raw,
        )

    from .checker import check_project as _check_project

    return _check_project(root, options=opts, keep_raw=keep_raw)
