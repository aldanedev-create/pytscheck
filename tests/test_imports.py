"""Tests that importing pytscheck is side-effect free."""

from __future__ import annotations

import subprocess
import sys

import pytest


def _run_isolated(code: str, *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=False,
    )


def test_import_does_not_launch_subprocess() -> None:
    code = (
        "import subprocess\n"
        "called = []\n"
        "real_run = subprocess.run\n"
        "def spy(*a, **k):\n"
        "    called.append((a, k))\n"
        "    return real_run(*a, **k)\n"
        "subprocess.run = spy\n"
        "import pytscheck\n"
        "assert not called, f'subprocess.run called during import: {called}'\n"
        "print('ok')\n"
    )
    result = _run_isolated(code)
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_import_does_not_create_sockets() -> None:
    code = (
        "import socket\n"
        "def blocked(*a, **k):\n"
        "    raise AssertionError('socket created during import')\n"
        "socket.socket = blocked\n"
        "import pytscheck\n"
        "print('ok')\n"
    )
    result = _run_isolated(code)
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_import_does_not_read_network_files() -> None:
    """No reads from /etc, ~/.ssh, or similar during import."""
    code = (
        "import builtins\n"
        "real_open = builtins.open\n"
        "def spy(path, *a, **k):\n"
        "    s = str(path)\n"
        "    if s.startswith(('/etc/', '/root/', '/home/')) and 'pytscheck' not in s:\n"
        "        raise AssertionError(f'unexpected open during import: {s}')\n"
        "    return real_open(path, *a, **k)\n"
        "builtins.open = spy\n"
        "import pytscheck\n"
        "print('ok')\n"
    )
    result = _run_isolated(code)
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_import_does_not_create_temp_files() -> None:
    code = (
        "import tempfile\n"
        "created = []\n"
        "real_mkdtemp = tempfile.mkdtemp\n"
        "def spy(*a, **k):\n"
        "    p = real_mkdtemp(*a, **k)\n"
        "    created.append(p)\n"
        "    return p\n"
        "tempfile.mkdtemp = spy\n"
        "import pytscheck\n"
        "assert not created, f'tempdirs created during import: {created}'\n"
        "print('ok')\n"
    )
    result = _run_isolated(code)
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_import_is_fast() -> None:
    """Import must not be dominated by subprocess or filesystem work."""
    import time

    code = (
        "import time\n"
        "t0 = time.perf_counter()\n"
        "import pytscheck\n"
        "t1 = time.perf_counter()\n"
        "print(f'{t1 - t0:.3f}')\n"
    )
    result = _run_isolated(code)
    assert result.returncode == 0, result.stderr
    elapsed = float(result.stdout.strip())
    # Generous threshold: real import should be well under a second.
    assert elapsed < 2.0, f"import took {elapsed:.3f}s"


def test_all_public_names_are_importable() -> None:
    import pytscheck

    for name in pytscheck.__all__:
        assert hasattr(pytscheck, name), f"missing public name: {name}"


def test_double_import_is_idempotent() -> None:
    import pytscheck as a
    import pytscheck as b

    assert a is b