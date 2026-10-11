"""Tests that pytscheck does not leak ambient environment state."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def _run_python(code: str, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    base_env = os.environ.copy()
    if env is not None:
        base_env.update(env)
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
        env=base_env,
    )


def test_import_ignores_nonexistent_node_modules() -> None:
    result = _run_python(
        "import pytscheck; print(pytscheck.__version__)",
        env={"NODE_PATH": "/nonexistent/path/for/pytscheck/tests"},
    )
    assert result.returncode == 0, result.stderr


def test_import_ignores_go_flags() -> None:
    result = _run_python(
        "import pytscheck; print(pytscheck.__version__)",
        env={"GOFLAGS": "-this-is-not-a-real-flag"},
    )
    assert result.returncode == 0, result.stderr


def test_import_ignores_node_options() -> None:
    result = _run_python(
        "import pytscheck; print(pytscheck.__version__)",
        env={"NODE_OPTIONS": "--require=/nonexistent/module"},
    )
    assert result.returncode == 0, result.stderr


def test_no_ts_node_env_leaks_in() -> None:
    result = _run_python(
        "import pytscheck; print(pytscheck.__version__)",
        env={
            "TS_NODE_PROJECT": "/nonexistent/tsconfig.json",
            "TS_NODE_TRANSPILE_ONLY": "true",
        },
    )
    assert result.returncode == 0, result.stderr


def test_checker_does_not_read_env_when_checking(tsgo_binary: Path, tmp_path: Path) -> None:
    """Checking must not depend on environment variables a caller sets."""
    from pytscheck import checker

    code = (
        "import os\n"
        "os.environ['NODE_PATH'] = '/nonexistent'\n"
        "os.environ['GOFLAGS'] = '-bad'\n"
        "from pytscheck import checker\n"
        "r = checker.check_source('export const x: number = 1;')\n"
        "assert r.success, [d.message for d in r.errors]\n"
        "print('ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_cwd_does_not_change_result(tsgo_binary: Path, tmp_path: Path) -> None:
    """The same source checked from different cwds must give the same Result."""
    from pytscheck import checker

    src = 'export const age: number = "twenty";'

    other = tmp_path / "other"
    other.mkdir()

    cwd_before = os.getcwd()
    try:
        os.chdir(tmp_path)
        r1 = checker.check_source(src)
        os.chdir(other)
        r2 = checker.check_source(src)
    finally:
        os.chdir(cwd_before)

    assert r1.success == r2.success
    assert [d.code for d in r1.errors] == [d.code for d in r2.errors]


def test_python_hashseed_does_not_affect_output(tsgo_binary: Path) -> None:
    """Deterministic diagnostics regardless of PYTHONHASHSEED."""
    code = (
        "from pytscheck import checker\n"
        "r = checker.check_source('export const age: number = \"twenty\";')\n"
        "print([d.code for d in r.errors])\n"
    )
    r1 = _run_python(code, env={"PYTHONHASHSEED": "0"})
    r2 = _run_python(code, env={"PYTHONHASHSEED": "42"})
    assert r1.returncode == 0, r1.stderr
    assert r2.returncode == 0, r2.stderr
    assert r1.stdout == r2.stdout


def test_locale_does_not_break_import() -> None:
    result = _run_python(
        "import pytscheck; print(pytscheck.__version__)",
        env={"LC_ALL": "C", "LANG": "C"},
    )
    assert result.returncode == 0, result.stderr


def test_path_environment_does_not_affect_binary_selection(tsgo_binary: Path) -> None:
    """The bundled binary is found via package path, not via PATH."""
    result = _run_python(
        "from pytscheck.runner import binary_path; print(binary_path())",
        env={"PATH": "/nonexistent"},
    )
    # The bundled binary should still resolve because we use __file__, not PATH.
    assert result.returncode == 0, result.stderr
    assert "tsgo" in result.stdout