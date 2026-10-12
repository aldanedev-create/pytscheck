"""Orchestrates runner -> parser -> results."""

from __future__ import annotations

import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from .config import CompilerOptions, find_tsconfig, validate_project_root
from .defaults import DEFAULT_MAX_SOURCE_BYTES
from .exceptions import AdapterExtractionError, CompilerExecutionError, ConfigurationError
from .models import Diagnostic, Result, SourceFile
from .options import options_to_argv
from .paths import assert_no_null_bytes, normalize
from .project import iter_typescript_files
from .protocol import parse_or_raise
from .resolver import resolve_project
from .results import build_result
from .runner import RunResult, run
from .version import COMPILER_VERSION

_Runner = Callable[..., RunResult]
_runner_override: ContextVar[_Runner | None] = ContextVar("pytscheck_runner", default=None)


@contextmanager
def _use_runner(runner: _Runner | None) -> Iterator[None]:
    token = _runner_override.set(runner)
    try:
        yield
    finally:
        _runner_override.reset(token)


def _run_tsgo_on_args(
    argv_tail: list[str],
    *,
    compiler_version: str = COMPILER_VERSION,
    keep_raw: bool = False,
    cwd: Path | None = None,
) -> Result:
    invoke = _runner_override.get() or run
    r = invoke(argv_tail, cwd=cwd)
    output = r.stdout + ("\n" + r.stderr if r.stderr else "")

    if r.returncode not in (0, 1, 2):
        raise CompilerExecutionError(
            f"tsgo exited abnormally with code {r.returncode}",
            returncode=r.returncode,
            stdout=r.stdout,
            stderr=r.stderr,
        )

    if r.returncode != 0 and not output.strip():
        raise CompilerExecutionError(
            f"tsgo exited with code {r.returncode} and produced no output",
            returncode=r.returncode,
            stdout=r.stdout,
            stderr=r.stderr,
        )

    diagnostics: tuple[Diagnostic, ...] = ()
    if output.strip():
        diagnostics = parse_or_raise(output, allow_unparsed=False)

    if r.returncode != 0 and not any(d.category == "error" for d in diagnostics):
        raise CompilerExecutionError(
            f"tsgo exited with code {r.returncode} without error diagnostics",
            returncode=r.returncode,
            stdout=r.stdout,
            stderr=r.stderr,
        )

    return build_result(
        list(diagnostics),
        compiler_version=compiler_version,
        elapsed_seconds=r.elapsed_seconds,
        raw_output=output if keep_raw else None,
    )


def check_source(
    source: str,
    *,
    filename: str = "input.ts",
    options: CompilerOptions | None = None,
    keep_raw: bool = False,
) -> Result:
    options = options or CompilerOptions()
    if len(source) > DEFAULT_MAX_SOURCE_BYTES:
        raise ConfigurationError(f"source exceeds {DEFAULT_MAX_SOURCE_BYTES} bytes")
    try:
        size = len(source.encode("utf-8"))
    except UnicodeError as exc:
        raise ConfigurationError("source is not valid UTF-8") from exc
    if size > DEFAULT_MAX_SOURCE_BYTES:
        raise ConfigurationError(f"source exceeds {DEFAULT_MAX_SOURCE_BYTES} bytes")
    assert_no_null_bytes(source, what="source")
    assert_no_null_bytes(filename, what="filename")
    if not filename or Path(filename).name != filename:
        raise ConfigurationError("filename must be a non-empty basename")
    with tempfile.TemporaryDirectory(prefix="pytscheck-") as tmp:
        tmp_path = Path(tmp).resolve()
        target = tmp_path / filename
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ConfigurationError(f"cannot write source {filename!r}: {exc}") from exc

        argv_tail = [*options_to_argv(options), "--ignoreConfig", str(target)]
        return _run_tsgo_on_args(argv_tail, keep_raw=keep_raw, cwd=tmp_path)


def check_file(
    path: str | Path,
    *,
    options: CompilerOptions | None = None,
    keep_raw: bool = False,
) -> Result:
    options = options or CompilerOptions()
    target = normalize(path)
    if not target.exists():
        raise ConfigurationError(f"file does not exist: {target}")

    try:
        with target.open("rb") as handle:
            size = 0
            while chunk := handle.read(64 * 1024):
                size += len(chunk)
                if size > DEFAULT_MAX_SOURCE_BYTES:
                    raise ConfigurationError(f"source exceeds {DEFAULT_MAX_SOURCE_BYTES} bytes")
                if b"\x00" in chunk:
                    raise ConfigurationError("source contains a NUL byte")
    except OSError as exc:
        raise ConfigurationError(f"cannot read source {target}: {exc}") from exc
    argv_tail = [*options_to_argv(options), "--ignoreConfig", str(target)]
    return _run_tsgo_on_args(argv_tail, keep_raw=keep_raw, cwd=target.parent)


def check_sources_virtual(
    sources: tuple[SourceFile, ...],
    *,
    options: CompilerOptions | None = None,
    keep_raw: bool = False,
) -> Result:
    """Check a set of virtual SourceFiles (used by the adapter path).

    Writes each source into a private temp directory, invokes tsgo once
    against the directory, and returns diagnostics whose ``file`` values
    are the *virtual* paths (remapping happens in the adapter layer).
    """
    from .adapters.sources import _validate_sources

    options = options or CompilerOptions()
    sources = _validate_sources(sources)
    if not sources:
        raise ConfigurationError("adapter returned no sources to check")

    with tempfile.TemporaryDirectory(prefix="pytscheck-adapter-") as tmp:
        tmp_path = Path(tmp).resolve()
        for src in sources:
            dest = tmp_path / src.path
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(src.text, encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise AdapterExtractionError(
                    f"cannot write virtual source {src.path!r}: {exc}"
                ) from exc

        argv_tail = [*options_to_argv(options), *(str(tmp_path / src.path) for src in sources)]
        return _run_tsgo_on_args(argv_tail, keep_raw=keep_raw, cwd=tmp_path)


def check_project(
    project_root: str | Path,
    *,
    options: CompilerOptions | None = None,
    keep_raw: bool = False,
) -> Result:
    options = options or CompilerOptions()
    root = validate_project_root(Path(project_root).expanduser().resolve())

    resolve_project(root)
    argv_tail = [*options_to_argv(options)]
    tsconfig = find_tsconfig(root)
    if tsconfig is not None:
        argv_tail += ["-p", str(tsconfig)]
    else:
        files = iter_typescript_files(root)
        if not files:
            raise ConfigurationError("project contains no TypeScript files")
        argv_tail.extend(str(p) for p in files)

    return _run_tsgo_on_args(argv_tail, keep_raw=keep_raw, cwd=root)


__all__ = ["check_file", "check_project", "check_source"]
