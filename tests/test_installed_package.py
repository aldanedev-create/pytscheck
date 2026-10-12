"""Tests the package as installed in a clean virtual environment."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers import installed_in_clean_venv


@pytest.fixture(scope="module")
def clean_venv_python(built_wheel: Path, tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("clean-venv")
    return installed_in_clean_venv(built_wheel, tmp)


def _run(
    py: Path, code: str, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    import os

    base_env = os.environ.copy()
    if env:
        base_env.update(env)
    return subprocess.run(
        [str(py), "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
        env=base_env,
    )


def test_package_imports_in_clean_venv(clean_venv_python: Path) -> None:
    r = _run(clean_venv_python, "import pytscheck; print(pytscheck.__version__)")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip()


def test_version_matches(clean_venv_python: Path) -> None:
    r = _run(clean_venv_python, "import pytscheck; print(pytscheck.__version__)")
    assert r.returncode == 0
    assert r.stdout.strip()


def test_no_optional_dependencies_required(clean_venv_python: Path) -> None:
    r = _run(clean_venv_python, "import pytscheck")
    assert r.returncode == 0, r.stderr


def test_public_api_available(clean_venv_python: Path) -> None:
    code = (
        "import pytscheck\n"
        "assert hasattr(pytscheck, 'check')\n"
        "assert hasattr(pytscheck, 'check_file')\n"
        "assert hasattr(pytscheck, 'check_project')\n"
        "print('ok')\n"
    )
    r = _run(clean_venv_python, code)
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_cli_available(clean_venv_python: Path) -> None:
    """The console script `pytscheck` must be on PATH in the venv."""
    if sys.platform == "win32":
        script = clean_venv_python.parent / "pytscheck.exe"
    else:
        script = clean_venv_python.parent / "pytscheck"
    assert script.exists(), f"console script not found at {script}"


def test_cli_runs(clean_venv_python: Path) -> None:
    if sys.platform == "win32":
        script = clean_venv_python.parent / "pytscheck.exe"
    else:
        script = clean_venv_python.parent / "pytscheck"
    r = subprocess.run(
        [str(script), "--version"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        shell=False,
    )
    assert r.returncode == 0, r.stderr
    assert "pytscheck" in r.stdout


def test_py_typed_marker_present(clean_venv_python: Path) -> None:
    code = (
        "import pytscheck, pathlib\n"
        "p = pathlib.Path(pytscheck.__file__).parent / 'py.typed'\n"
        "assert p.exists(), str(p)\n"
        "print('ok')\n"
    )
    r = _run(clean_venv_python, code)
    assert r.returncode == 0, r.stderr


def test_manifest_bundled(clean_venv_python: Path) -> None:
    code = (
        "import pytscheck, pathlib, json\n"
        "p = pathlib.Path(pytscheck.__file__).parent / 'bin' / 'manifest.json'\n"
        "assert p.exists(), str(p)\n"
        "json.loads(p.read_text())\n"
        "print('ok')\n"
    )
    r = _run(clean_venv_python, code)
    assert r.returncode == 0, r.stderr


def test_no_dev_dependencies_present(clean_venv_python: Path) -> None:
    r = _run(clean_venv_python, "import pytest")
    assert r.returncode != 0, "pytest should not be installed in clean venv"
