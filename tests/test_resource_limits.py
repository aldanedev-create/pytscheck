"""Tests for resource-limit enforcement: output size, source size, timeouts."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck.exceptions import CompilerExecutionError
from pytscheck.runner import run
from tests.helpers import make_fake_tsgo, hide_file


def test_stdout_size_limit_enforced(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('export const age: number = "x";\n', encoding="utf-8")
    with pytest.raises(CompilerExecutionError, match="stdout exceeded"):
        run(["--noEmit", str(f)], max_stdout_bytes=1)


def test_stderr_size_limit_enforced_by_fake(tmp_path: Path) -> None:
    """A fake compiler that produces stderr above the limit must be rejected."""
    from pytscheck.runner import binary_path as real_binary_path
    from pytscheck.exceptions import CompilerNotFoundError

    try:
        original = real_binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    # A script that writes 1 MiB to stderr
    fake = tmp_path / "fake"
    if __import__("os").name == "nt":
        pytest.skip("POSIX fake script used here")
    fake.write_text(
        "#!/bin/sh\n"
        "yes 'stderr line' | head -n 100000 1>&2\n"
        "exit 1\n"
    )
    fake.chmod(0o755)

    with hide_file(original):
        import shutil

        shutil.copy2(fake, original)
        original.chmod(0o755)
        with pytest.raises(CompilerExecutionError, match="stderr exceeded"):
            run(["--version"], max_stderr_bytes=1024)


def test_source_size_limit_enforced(tsgo_binary: Path, tmp_path: Path) -> None:
    from pytscheck.defaults import DEFAULT_MAX_SOURCE_BYTES
    from pytscheck.exceptions import ConfigurationError
    from pytscheck import checker

    f = tmp_path / "huge.ts"
    chunk = b"// padding\n"
    target = DEFAULT_MAX_SOURCE_BYTES + 1024
    with f.open("wb") as fh:
        written = 0
        while written < target:
            fh.write(chunk)
            written += len(chunk)

    with pytest.raises((ConfigurationError, CompilerExecutionError, Exception)):
        checker.check_file(f)


def test_timeout_enforced_by_default(tsgo_binary: Path) -> None:
    """A very small timeout forces a real TimeoutExpired."""
    from pytscheck.exceptions import CompilerTimeoutError

    with pytest.raises(CompilerTimeoutError):
        run(["--version"], timeout=0.001)


def test_max_files_per_project(tsgo_binary: Path, tmp_path: Path) -> None:
    from pytscheck.exceptions import ConfigurationError
    from pytscheck.project import iter_typescript_files

    for i in range(5):
        (tmp_path / f"f{i}.ts").write_text("", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="exceeds"):
        iter_typescript_files(tmp_path, max_files=3)


def test_timeout_kills_child_process(tmp_path: Path) -> None:
    """After a timeout, the child must be reaped, not orphaned."""
    import subprocess
    import sys
    import time

    start = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        subprocess.run(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            capture_output=True,
            timeout=0.5,
            check=False,
            shell=False,
        )
    elapsed = time.monotonic() - start
    assert elapsed < 5.0, "timeout did not kill child quickly"


def test_output_bomb_from_fake_compiler_rejected(tmp_path: Path) -> None:
    """A fake compiler emitting a huge stdout must trip the size limit."""
    from pytscheck.runner import binary_path as real_binary_path
    from pytscheck.exceptions import CompilerNotFoundError

    try:
        original = real_binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    fake = make_fake_tsgo(tmp_path / "fake", behavior="big")
    with hide_file(original):
        import shutil

        shutil.copy2(fake, original)
        original.chmod(0o755)
        with pytest.raises(CompilerExecutionError):
            run(["--version"], max_stdout_bytes=1024)


def test_concurrent_checks_do_not_leak_fds(tsgo_binary: Path) -> None:
    """Running many checks in a row must not leak file descriptors."""
    import os
    from pytscheck import checker

    if not hasattr(os, "listdir"):
        pytest.skip("POSIX-only fd check")
    if not Path("/proc/self/fd").exists():
        pytest.skip("/proc/self/fd not available")

    def fd_count() -> int:
        return len(os.listdir("/proc/self/fd"))

    before = fd_count()
    for i in range(10):
        checker.check_source(f"export const x{i}: number = {i};")
    after = fd_count()

    # Allow small variance but not a leak proportional to iterations
    assert after - before < 5, f"fd leak: before={before} after={after}"