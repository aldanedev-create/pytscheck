"""Tests for checking multiple projects in parallel."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

from pytscheck import checker


def _process_check(project: Path) -> bool:
    return checker.check_project(project).success


def _make_project(root: Path, i: int, bad: bool) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, "include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    value = '"bad"' if bad else str(i)
    (root / f"file{i}.ts").write_text(
        f"export const x: number = {value};\n",
        encoding="utf-8",
    )
    return root


def test_thread_parallel_projects(tsgo_binary: Path, tmp_path: Path) -> None:
    projects = [_make_project(tmp_path / f"p{i}", i, bad=(i % 2 == 1)) for i in range(4)]

    def do_check(p: Path) -> bool:
        return checker.check_project(p).success

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(do_check, projects))

    assert results == [True, False, True, False]


def test_process_parallel_projects(tsgo_binary: Path, tmp_path: Path) -> None:
    projects = [_make_project(tmp_path / f"p{i}", i, bad=(i % 2 == 1)) for i in range(4)]

    with ProcessPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(_process_check, projects))

    assert results == [True, False, True, False]


def test_many_projects_scales(tsgo_binary: Path, tmp_path: Path) -> None:
    projects = [_make_project(tmp_path / f"p{i}", i, bad=False) for i in range(12)]

    def do_check(p: Path) -> bool:
        return checker.check_project(p).success

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(do_check, projects))
    assert all(results)


def test_parallel_projects_do_not_share_state(tsgo_binary: Path, tmp_path: Path) -> None:
    """Each check must use its own workspace; no cross-contamination."""
    p_ok = _make_project(tmp_path / "ok", 0, bad=False)
    p_bad = _make_project(tmp_path / "bad", 1, bad=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(checker.check_project, p) for p in (p_ok, p_bad) * 4]
        results = [f.result() for f in futures]

    successes = [r.success for r in results]
    assert successes.count(True) == 4
    assert successes.count(False) == 4
