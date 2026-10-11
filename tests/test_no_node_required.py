"""Tests that pytscheck works without Node.js installed."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers import installed_in_clean_venv


@pytest.fixture(scope="module")
def clean_venv_python(built_wheel: Path, tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("clean-venv-node")
    return installed_in_clean_venv(built_wheel, tmp)


def test_node_is_not_required() -> None:
    """Verify no `node` binary is needed. This documents the intent even if
    the CI runner happens to have node installed."""
    # Not a strict environment check; the test in a clean venv below is the
    # real assertion. This one exists so that we notice if pytscheck ever
    # shells out to node at import time.
    import pytscheck

    assert pytscheck.__version__


def test_import_without_node_on_path(clean_venv_python: Path) -> None:
    env = os.environ.copy()
    # Remove node from PATH entirely
    env["PATH"] = os.pathsep.join(
        p for p in env.get("PATH", "").split(os.pathsep)
        if "node" not in p.lower()
    )
    r = subprocess.run(
        [str(clean_venv_python), "-c", "import pytscheck; print('ok')"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        shell=False,
        env=env,
    )
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_check_without_node(clean_venv_python: Path, tmp_path: Path) -> None:
    if shutil.which("node") is None:
        pytest.skip("node not present, cannot prove absence")

    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(
        p for p in env.get("PATH", "").split(os.pathsep)
        if "node" not in p.lower()
    )
    code = (
        "from pytscheck import checker\n"
        "r = checker.check_source('export const x: number = 1;')\n"
        "assert r.success, [d.message for d in r.errors]\n"
        "print('ok')\n"
    )
    r = subprocess.run(
        [str(clean_venv_python), "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
        env=env,
    )
    # If the bundled binary is not present (Phase 0 not run), skip.
    if "bundled tsgo not found" in (r.stderr or ""):
        pytest.skip("bundled tsgo not present")
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout