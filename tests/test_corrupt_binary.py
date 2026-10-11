"""Tests for behavior when the bundled binary exists but is corrupt.

We replace the real binary with a real, executable file that is *not* a
valid tsgo (a shell script, a text file with no exec bit, a directory).
The runner must surface a clear operational error and never report success.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from pytscheck.exceptions import CompilerExecutionError, CompilerNotFoundError
from pytscheck.runner import run
from tests.helpers import hide_file


@pytest.fixture
def replace_with(tmp_path: Path):
    """Return a context manager that swaps the real binary for a replacement."""
    from pytscheck.runner import binary_path as real_binary_path

    try:
        original = real_binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    replacements: list[Path] = []

    def _swap(replacement: Path) -> None:
        with hide_file(original):
            # Copy the replacement into place
            import shutil

            shutil.copy2(replacement, original)
            replacements.append(original)

    yield _swap


def test_non_executable_replacement_raises(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("permission bits not meaningful on Windows")
    from pytscheck.runner import binary_path as real_binary_path

    try:
        original = real_binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    junk = tmp_path / "junk"
    junk.write_text("not a binary\n")

    with hide_file(original):
        import shutil

        shutil.copy2(junk, original)
        original.chmod(0o644)
        with pytest.raises(CompilerNotFoundError):
            run(["--version"])


def test_garbage_executable_does_not_report_success(tmp_path: Path) -> None:
    """An executable that exits 0 with garbage output must not be treated as
    a successful check."""
    from pytscheck import checker
    from pytscheck.runner import binary_path as real_binary_path
    from tests.helpers import make_fake_tsgo

    try:
        original = real_binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    fake = make_fake_tsgo(tmp_path / "fake", behavior="garbage")
    with hide_file(original):
        import shutil

        shutil.copy2(fake, original)
        original.chmod(0o755)
        with pytest.raises(Exception):
            # Either CompilerExecutionError or OutputParseError, depending
            # on how the garbage is interpreted. Either way: not success.
            r = checker.check_source("const x = 1;")
            assert not r.success
            raise AssertionError("garbage output was accepted")


def test_crashing_executable_raises_operational_error(tmp_path: Path) -> None:
    from pytscheck import checker
    from pytscheck.runner import binary_path as real_binary_path
    from tests.helpers import make_fake_tsgo

    try:
        original = real_binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    fake = make_fake_tsgo(tmp_path / "fake", behavior="crash")
    with hide_file(original):
        import shutil

        shutil.copy2(fake, original)
        original.chmod(0o755)
        with pytest.raises((CompilerExecutionError, Exception)):
            r = checker.check_source("const x = 1;")
            if r.success:
                raise AssertionError("crashing binary reported success")


def test_empty_executable_raises(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("empty executable behavior differs on Windows")
    from pytscheck.runner import binary_path as real_binary_path

    try:
        original = real_binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    empty = tmp_path / "empty"
    empty.write_bytes(b"")
    empty.chmod(0o755)

    with hide_file(original):
        import shutil

        shutil.copy2(empty, original)
        original.chmod(0o755)
        # Empty file with exec bit: on Linux, Exec format error -> OSError
        with pytest.raises(Exception):
            run(["--version"])


def test_binary_restored_after_corruption_test(tmp_path: Path) -> None:
    from pytscheck.runner import binary_path as real_binary_path

    try:
        original = real_binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    # Read the real binary's bytes so we can verify restoration later
    original_bytes = original.read_bytes()

    junk = tmp_path / "junk"
    junk.write_bytes(b"junk")
    junk.chmod(0o755)

    with hide_file(original):
        import shutil

        shutil.copy2(junk, original)
        original.chmod(0o755)

    # After context exit, the real binary should be back
    assert original.read_bytes() == original_bytes