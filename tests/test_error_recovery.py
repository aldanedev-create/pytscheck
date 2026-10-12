"""Tests that pytscheck recovers cleanly after failures."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path

import pytest

from pytscheck import checker
from pytscheck.exceptions import (
    CompilerExecutionError,
    CompilerNotFoundError,
    CompilerTimeoutError,
    PyTSCheckError,
)
from tests.helpers import hide_file, make_fake_tsgo


def test_recovers_after_missing_binary() -> None:
    from pytscheck.runner import binary_path

    try:
        original = binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    with hide_file(original), pytest.raises(CompilerNotFoundError):
        checker.check_source("const x = 1;")

    # After restoring the binary, a clean check must work.
    r = checker.check_source("export const x: number = 1;")
    assert r.success


def test_recovers_after_timeout(tmp_path: Path) -> None:
    from pytscheck.runner import binary_path

    try:
        original = binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    fake = make_fake_tsgo(tmp_path / "fake", behavior="hang")
    with hide_file(original):
        import shutil

        shutil.copy2(fake, original)
        original.chmod(0o755)
        with suppress(CompilerTimeoutError, CompilerExecutionError):
            checker.check_source("const x = 1;")

    # After the fake is removed, real checks must work again.
    r = checker.check_source("export const x: number = 1;")
    assert r.success


def test_recovers_after_crash(tmp_path: Path) -> None:
    from pytscheck.runner import binary_path

    try:
        original = binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    fake = make_fake_tsgo(tmp_path / "fake", behavior="crash")
    with hide_file(original):
        import shutil

        shutil.copy2(fake, original)
        original.chmod(0o755)
        with suppress(PyTSCheckError):
            checker.check_source("const x = 1;")

    r = checker.check_source("export const x: number = 1;")
    assert r.success


def test_recovers_after_unparsable_output(tmp_path: Path) -> None:
    from pytscheck.runner import binary_path

    try:
        original = binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    fake = make_fake_tsgo(tmp_path / "fake", behavior="garbage")
    with hide_file(original):
        import shutil

        shutil.copy2(fake, original)
        original.chmod(0o755)
        with suppress(PyTSCheckError):
            checker.check_source("const x = 1;")

    r = checker.check_source("export const x: number = 1;")
    assert r.success


def test_recovers_after_bad_file(tmp_path: Path, tsgo_binary: Path) -> None:
    from pytscheck.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError):
        checker.check_file(tmp_path / "nonexistent.ts")

    # A normal check should still work.
    r = checker.check_source("export const x: number = 1;")
    assert r.success


def test_no_temp_dir_leak_after_failure(tmp_path: Path) -> None:
    import glob
    import tempfile

    from pytscheck.runner import binary_path

    try:
        original = binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    before = set(glob.glob(tempfile.gettempdir() + "/pytscheck-*"))

    with hide_file(original), suppress(PyTSCheckError):
        checker.check_source("const x = 1;")

    after = set(glob.glob(tempfile.gettempdir() + "/pytscheck-*"))
    assert not (after - before)


def test_multiple_failures_do_not_accumulate_state(tmp_path: Path, tsgo_binary: Path) -> None:
    from pytscheck.exceptions import ConfigurationError

    for _ in range(5):
        with pytest.raises(ConfigurationError):
            checker.check_file(tmp_path / "missing.ts")

    r = checker.check_source("export const x: number = 1;")
    assert r.success
