"""Regression checks for subprocess limits using real executable scripts."""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

import pytest

from pytscheck.exceptions import CompilerExecutionError, CompilerTimeoutError
from pytscheck.runner import run
from tests.helpers import hide_file


@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group regression")
def test_timeout_stops_descendants(tsgo_binary: Path, tmp_path: Path) -> None:
    marker = tmp_path / "orphan-ran"
    script = tmp_path / "child-script"
    script.write_text(f'#!/bin/sh\n(sleep 0.5; touch "{marker}") &\nwait\n')
    script.chmod(0o755)
    started = time.monotonic()
    with hide_file(tsgo_binary):
        shutil.copy2(script, tsgo_binary)
        with pytest.raises(CompilerTimeoutError):
            run([], timeout=0.1)
    assert time.monotonic() - started < 3
    time.sleep(0.6)
    assert not marker.exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX executable-script regression")
def test_continuous_output_is_stopped_before_timeout(tsgo_binary: Path, tmp_path: Path) -> None:
    script = tmp_path / "output-script"
    script.write_text(f"#!{sys.executable}\nimport os\nwhile True: os.write(1, b'x' * 65536)\n")
    script.chmod(0o755)
    started = time.monotonic()
    with hide_file(tsgo_binary):
        shutil.copy2(script, tsgo_binary)
        with pytest.raises(CompilerExecutionError, match="stdout exceeded"):
            run([], timeout=5, max_stdout_bytes=1024)
    assert time.monotonic() - started < 3
