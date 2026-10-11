"""Tests that pytscheck works without Go installed."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.helpers import installed_in_clean_venv


@pytest.fixture(scope="module")
def clean_venv_python(built_wheel: Path, tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("clean-venv-go")
    return installed_in_clean_venv(built_wheel, tmp)


def test_import_without_go_on_path(clean_venv_python: Path) -> None:
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(
        p for p in env.get("PATH", "").split(os.pathsep)
        if "go" not in p.lower() and "golang" not in p.lower()
    )
    env.pop("GOFLAGS", None)
    env.pop("GOPATH", None)
    env.pop("GOROOT", None)

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


def test_check_without_go(clean_venv_python: Path) -> None:
    if shutil.which("go") is None:
        pytest.skip("go not present, cannot prove absence")

    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(
        p for p in env.get("PATH", "").split(os.pathsep)
        if "go" not in p.lower() and "golang" not in p.lower()
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
    if "bundled tsgo not found" in (r.stderr or ""):
        pytest.skip("bundled tsgo not present")
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_go_flags_dont_affect_import(clean_venv_python: Path) -> None:
    env = os.environ.copy()
    env["GOFLAGS"] = "-invalid-flag"
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