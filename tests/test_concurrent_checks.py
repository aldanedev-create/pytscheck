"""Tests for concurrent invocation of the checker.

Real threads, real subprocesses, real binary. No synchronization stubs.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from pytscheck import checker


def test_many_concurrent_checks_all_succeed(tsgo_binary: Path) -> None:
    """16 threads each check a valid source; all must return success."""
    def do_check(i: int) -> bool:
        r = checker.check_source(f"export const x{i}: number = {i};")
        return r.success

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(do_check, i) for i in range(16)]
        results = [f.result() for f in as_completed(futures)]
    assert all(results), results


def test_concurrent_checks_produce_consistent_results(tsgo_binary: Path) -> None:
    """The same input checked concurrently yields identical diagnostics."""
    src = 'const age: number = "twenty";'

    def do_check(_i: int):
        return checker.check_source(src)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = [f.result() for f in [pool.submit(do_check, i) for i in range(8)]]

    first = results[0]
    for r in results[1:]:
        assert r.success == first.success
        assert [d.code for d in r.errors] == [d.code for d in first.errors]


def test_concurrent_checks_do_not_interfere(tsgo_binary: Path) -> None:
    """Mixed valid/invalid sources under load must not corrupt each other."""
    def do_check(i: int):
        if i % 2 == 0:
            r = checker.check_source(f"export const x{i}: number = {i};")
            return ("ok", r.success)
        r = checker.check_source(f'export const x{i}: number = "bad";')
        return ("bad", r.success)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(do_check, i) for i in range(20)]
        results = [f.result() for f in as_completed(futures)]

    for kind, success in results:
        if kind == "ok":
            assert success is True
        else:
            assert success is False


def test_concurrent_file_checks(tsgo_binary: Path, tmp_path: Path) -> None:
    files = []
    for i in range(8):
        p = tmp_path / f"f{i}.ts"
        p.write_text(f"export const x: number = {i};\n", encoding="utf-8")
        files.append(p)

    def do_check(p: Path) -> bool:
        return checker.check_file(p).success

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(do_check, files))
    assert all(results)


def test_concurrent_checks_release_tempdirs(tsgo_binary: Path) -> None:
    """No temp directories should leak after concurrent checks."""
    import glob
    import tempfile

    before = set(glob.glob(tempfile.gettempdir() + "/pytscheck-*"))

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda i: checker.check_source(f"export const y{i} = 1;"), range(8)))

    after = set(glob.glob(tempfile.gettempdir() + "/pytscheck-*"))
    # No *new* leaked temp dirs
    assert not (after - before), sorted(after - before)