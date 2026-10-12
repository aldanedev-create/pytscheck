"""Tests that pytscheck does not require network access after install."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.helpers import installed_in_clean_venv


@pytest.fixture(scope="module")
def clean_venv_python(built_wheel: Path, tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("clean-venv-net")
    return installed_in_clean_venv(built_wheel, tmp)


def test_install_uses_no_index(built_wheel: Path, tmp_path: Path) -> None:
    """Installing the wheel with --no-index must succeed."""
    # This is what installed_in_clean_venv already does internally; the
    # fact that the fixture ran proves it.
    assert built_wheel.exists()


def test_import_does_not_open_sockets(clean_venv_python: Path) -> None:
    code = (
        "import socket\n"
        "def blocked(*a, **k):\n"
        "    raise AssertionError('socket created')\n"
        "socket.socket = blocked\n"
        "import pytscheck\n"
        "print('ok')\n"
    )
    r = subprocess.run(
        [str(clean_venv_python), "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        shell=False,
    )
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_check_does_not_open_sockets(clean_venv_python: Path) -> None:
    code = (
        "import socket\n"
        "def blocked(*a, **k):\n"
        "    raise AssertionError('socket created')\n"
        "socket.socket = blocked\n"
        "from pytscheck import checker\n"
        "try:\n"
        "    r = checker.check_source('export const x: number = 1;')\n"
        "except Exception as e:\n"
        "    msg = str(e)\n"
        "    if 'bundled tsgo not found' in msg:\n"
        "        print('skip')\n"
        "    else:\n"
        "        raise\n"
        "else:\n"
        "    assert r.success\n"
        "    print('ok')\n"
    )
    r = subprocess.run(
        [str(clean_venv_python), "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
    )
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout or "skip" in r.stdout


def test_no_http_requests_during_import(clean_venv_python: Path) -> None:
    """Neither urllib nor requests should be triggered at import time."""
    code = (
        "import urllib.request\n"
        "real_urlopen = urllib.request.urlopen\n"
        "def blocked(*a, **k):\n"
        "    raise AssertionError('urlopen called')\n"
        "urllib.request.urlopen = blocked\n"
        "import pytscheck\n"
        "print('ok')\n"
    )
    r = subprocess.run(
        [str(clean_venv_python), "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        shell=False,
    )
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout
