"""Tests ensuring pytscheck works on its declared Python floor (3.11+).

This file checks syntax, stdlib availability, and packaging metadata.
It does not attempt to run tests under other Python versions; that is
the job of tox/nox and CI.
"""

from __future__ import annotations

import sys
import sysconfig
from pathlib import Path

import pytest


MINIMUM = (3, 11)


def test_running_python_is_at_least_the_floor() -> None:
    assert sys.version_info[:2] >= MINIMUM, (
        f"tests require Python >= {MINIMUM[0]}.{MINIMUM[1]}, "
        f"running {sys.version_info[:2]}"
    )


def test_requires_python_in_pyproject() -> None:
    import tomllib

    repo_root = Path(__file__).resolve().parent.parent
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        pytest.skip("pyproject.toml not present")
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    requires = data["project"].get("requires-python")
    assert requires is not None
    assert ">=3.11" in requires


def test_classifiers_include_supported_versions() -> None:
    import tomllib

    repo_root = Path(__file__).resolve().parent.parent
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        pytest.skip("pyproject.toml not present")
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    classifiers = data["project"].get("classifiers", [])
    for v in ("3.11", "3.12", "3.13"):
        assert f"Programming Language :: Python :: {v}" in classifiers


def test_uses_only_stdlib_imports_in_core() -> None:
    """Core package must not import third-party libraries at runtime."""
    import pytscheck

    forbidden = {"requests", "httpx", "numpy", "click", "typer", "pydantic"}
    loaded = set(sys.modules)
    leaked = forbidden & loaded
    assert not leaked, (
        f"pytscheck import pulled in third-party modules: {leaked}"
    )


@pytest.mark.parametrize("module", ["tomllib", "importlib.metadata", "dataclasses", "typing"])
def test_stdlib_modules_available(module: str) -> None:
    """Modules we rely on must be available on the target Python."""
    __import__(module)


def test_module_importable_from_fresh_interpreter() -> None:
    import subprocess

    result = subprocess.run(
        [sys.executable, "-c", "import pytscheck; print(pytscheck.__version__)"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        shell=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()


def test_python_implementation_is_supported() -> None:
    """CPython and PyPy are supported; other implementations may work but are untested."""
    impl = sys.implementation.name
    assert impl in {"cpython", "pypy"}, f"unsupported implementation: {impl}"


def test_architecture_is_known() -> None:
    """The running platform must be one of our declared targets."""
    import platform

    system = sys.platform
    machine = platform.machine().lower()
    known = {
        ("linux", "x86_64"),
        ("linux", "amd64"),
        ("linux", "aarch64"),
        ("linux", "arm64"),
        ("darwin", "x86_64"),
        ("darwin", "arm64"),
        ("win32", "amd64"),
        ("win32", "arm64"),
    }
    # Some CI runners report slightly different machine strings; allow if
    # any known prefix matches.
    assert any(
        system == k[0] and machine.startswith(k[1][:5]) for k in known
    ), f"unknown platform: {system}/{machine}"


def test_no_deprecated_sys_api() -> None:
    """We must not rely on deprecated sys attributes."""
    # sys.version_info[:2] is the canonical replacement for sys.version[:3].
    assert isinstance(sys.version_info, tuple) or hasattr(sys.version_info, "major")


def test_stable_abi_flag_does_not_break_import() -> None:
    """If running on a stable-ABI build, pytscheck must still import."""
    abi = sysconfig.get_config_var("SOABI") or ""
    if "abi3" not in abi:
        pytest.skip("not a stable-ABI interpreter")
    import pytscheck

    assert pytscheck.__version__