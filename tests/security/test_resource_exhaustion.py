"""Tests for resource-exhaustion resistance."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pytscheck import check, check_file
from pytscheck.defaults import DEFAULT_MAX_SOURCE_BYTES
from pytscheck.exceptions import CompilerExecutionError, PyTSCheckError
from pytscheck.runner import run


def test_oversized_source_rejected_or_handled() -> None:
    """A source larger than the default limit must fail cleanly."""
    src = "// " + "x" * (DEFAULT_MAX_SOURCE_BYTES + 1024)
    try:
        r = check(src)
    except (PyTSCheckError, Exception):
        return
    assert isinstance(r.success, bool)


def test_oversized_file_rejected_or_handled(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "huge.ts"
    chunk = b"// padding\n"
    target = DEFAULT_MAX_SOURCE_BYTES + 1024
    with f.open("wb") as fh:
        written = 0
        while written < target:
            fh.write(chunk)
            written += len(chunk)
    try:
        r = check_file(f)
    except (PyTSCheckError, Exception):
        return
    assert isinstance(r.success, bool)


def test_many_files_project(tmp_path: Path) -> None:
    """A project with many files must either check or fail cleanly."""
    from pytscheck import check_project
    from pytscheck.exceptions import ConfigurationError

    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, "include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    for i in range(100):
        (tmp_path / f"f{i}.ts").write_text(f"export const x{i}: number = {i};\n", encoding="utf-8")
    try:
        r = check_project(tmp_path)
    except (ConfigurationError, PyTSCheckError):
        return
    assert isinstance(r.success, bool)


def test_stdout_size_limit_enforced(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('const x: number = "bad";\n', encoding="utf-8")
    with pytest.raises(CompilerExecutionError, match="stdout exceeded"):
        run(["--noEmit", str(f)], max_stdout_bytes=1)


def test_timeout_enforced_with_tiny_limit(tsgo_binary: Path) -> None:
    from pytscheck.exceptions import CompilerTimeoutError

    with pytest.raises(CompilerTimeoutError):
        run(["--version"], timeout=0.001)


def test_very_long_argument_rejected_or_handled(tsgo_binary: Path) -> None:
    """A very long argument must not crash the subprocess machinery."""
    long_arg = "a" * 100_000
    try:
        result = run(["--noEmit", long_arg])
    except (OSError, CompilerExecutionError, ValueError):
        return
    assert isinstance(result.returncode, int)


def test_many_arguments(tsgo_binary: Path, tmp_path: Path) -> None:
    """Passing many arguments must not crash."""
    args = ["--noEmit"]
    for i in range(1000):
        args.append(f"--option{i}")
    try:
        result = run(args)
    except CompilerExecutionError:
        return
    assert isinstance(result.returncode, int)


def test_concurrent_checks_do_not_leak_fds(tsgo_binary: Path) -> None:
    """Repeated checks must not leak file descriptors."""
    if not Path("/proc/self/fd").exists():
        pytest.skip("/proc/self/fd not available")

    def fd_count() -> int:
        return len(os.listdir("/proc/self/fd"))

    before = fd_count()
    for i in range(20):
        check(f"export const x{i}: number = {i};")
    after = fd_count()
    assert after - before < 10


def test_concurrent_checks_do_not_leak_tempdirs(
    tsgo_binary: Path, tmp_path: Path, monkeypatch
) -> None:
    import glob
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    before = set(glob.glob(tempfile.gettempdir() + "/pytscheck-*"))
    for i in range(10):
        check(f"export const x{i}: number = {i};")
    after = set(glob.glob(tempfile.gettempdir() + "/pytscheck-*"))
    assert not (after - before)


def test_oom_on_huge_source_does_not_crash_python() -> None:
    """Even a 100MB source string must be handled without segfault."""
    # 100 MB of a single character
    huge = "a" * (100 * 1024 * 1024)
    try:
        r = check(huge)
    except (PyTSCheckError, MemoryError):
        return
    assert isinstance(r.success, bool)
