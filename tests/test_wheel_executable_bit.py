"""The bundled compiler must be marked executable inside non-Windows wheels."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from release_check import check_wheel_contents  # noqa: E402


def _wheel(tmp_path: Path, mode: int) -> Path:
    wheel = tmp_path / "pytscheck-0.1.1-py3-none-manylinux_2_17_x86_64.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        for name in (
            "pytscheck/__init__.py",
            "pytscheck/py.typed",
            "pytscheck-0.1.1.dist-info/METADATA",
            "pytscheck-0.1.1.dist-info/RECORD",
            "pytscheck/bin/linux-amd64/lib/lib.d.ts",
        ):
            zf.writestr(name, "")
        info = zipfile.ZipInfo("pytscheck/bin/linux-amd64/lib/tsgo")
        info.external_attr = mode << 16
        zf.writestr(info, b"\x7fELF")
    return wheel


@pytest.mark.parametrize("mode,ok", [(0o100644, False), (0o100755, True)])
def test_wheel_requires_executable_compiler(tmp_path: Path, mode: int, ok: bool) -> None:
    check = check_wheel_contents(_wheel(tmp_path, mode))
    assert check.ok is ok
    if not ok:
        assert "not marked executable" in check.detail