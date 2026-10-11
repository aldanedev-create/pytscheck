"""Tests that temporary files and directories are cleaned up."""

from __future__ import annotations

import glob
import os
import tempfile
import time
from pathlib import Path

import pytest

from pytscheck import check, check_file, check_project


def _pytscheck_tmpdirs() -> set[str]:
    return set(glob.glob(os.path.join(tempfile.gettempdir(), "pytscheck-*")))


def test_check_cleans_tempdirs(tsgo_binary: Path) -> None:
    before = _pytscheck_tmpdirs()
    check("export const x: number = 1;")
    after = _pytscheck_tmpdirs()
    assert not (after - before), f"leaked: {after - before}"


def test_check_with_error_cleans_tempdirs(tsgo_binary: Path) -> None:
    before = _pytscheck_tmpdirs()
    check('const x: number = "bad";')
    after = _pytscheck_tmpdirs()
    assert not (after - before)


def test_check_file_cleans_tempdirs(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "a.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    before = _pytscheck_tmpdirs()
    check_file(f)
    after = _pytscheck_tmpdirs()
    assert not (after - before)


def test_check_project_cleans_tempdirs(tsgo_binary: Path, tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    (tmp_path / "a.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    before = _pytscheck_tmpdirs()
    check_project(tmp_path)
    after = _pytscheck_tmpdirs()
    assert not (after - before)


def test_failed_check_cleans_tempdirs(tsgo_binary: Path) -> None:
    from pytscheck.exceptions import PyTSCheckError

    before = _pytscheck_tmpdirs()
    try:
        check("const x: number = ;")
    except PyTSCheckError:
        pass
    after = _pytscheck_tmpdirs()
    assert not (after - before)


def test_missing_binary_cleans_tempdirs() -> None:
    from pytscheck.exceptions import PyTSCheckError
    from pytscheck.runner import binary_path
    from tests.helpers import hide_file

    try:
        original = binary_path()
    except Exception:
        pytest.skip("no binary")

    before = _pytscheck_tmpdirs()
    with hide_file(original):
        try:
            check("const x = 1;")
        except PyTSCheckError:
            pass
    after = _pytscheck_tmpdirs()
    assert not (after - before)


def test_concurrent_checks_all_clean(tsgo_binary: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    before = _pytscheck_tmpdirs()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda i: check(f"export const x{i} = 1;"), range(10)))
    after = _pytscheck_tmpdirs()
    assert not (after - before)


def test_adapter_check_cleans_tempdirs(tsgo_binary: Path, tmp_path: Path) -> None:
    from pytscheck import check_project
    from pytscheck.models import SourceFile

    class A:
        @property
        def name(self) -> str:
            return "cleanup-test"

        def get_sources(self, project_root: str) -> list[SourceFile]:
            return [SourceFile(path="x.ts", text="export const x: number = 1;\n")]

    before = _pytscheck_tmpdirs()
    check_project(tmp_path, adapter=A())
    after = _pytscheck_tmpdirs()
    assert not (after - before)


def test_cleanup_happens_even_on_early_exit(tsgo_binary: Path) -> None:
    """If the caller exits mid-check (exception), tempdirs are still cleaned."""
    from pytscheck.exceptions import PyTSCheckError

    before = _pytscheck_tmpdirs()
    try:
        check("const x: number = ;")
    except PyTSCheckError:
        pass
    time.sleep(0.1)  # give the context manager a chance to finalize
    after = _pytscheck_tmpdirs()
    assert not (after - before)


def test_no_tempdir_on_validation_error() -> None:
    """A validation error should not create a tempdir at all."""
    from pytscheck.exceptions import ConfigurationError

    before = _pytscheck_tmpdirs()
    try:
        check("const x = 1;", filename="a\x00b.ts")
    except ConfigurationError:
        pass
    after = _pytscheck_tmpdirs()
    assert not (after - before)