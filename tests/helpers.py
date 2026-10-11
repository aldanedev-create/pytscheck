"""Helpers used across the test suite.

These do real work: they run real entry points, parse real output, and
manipulate real files. They do not stub anything.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any

from pytscheck.models import Diagnostic


# ---------------------------------------------------------------------------
# CLI invocation
# ---------------------------------------------------------------------------


def run_cli(argv: list[str]) -> tuple[int, str, str]:
    """Run ``pytscheck`` in-process and capture stdout/stderr.

    Uses the real ``main`` from :mod:`pytscheck.__main__`. Does not mock
    anything; whatever the CLI does on the current machine, this captures.
    """
    from pytscheck.__main__ import main

    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = main(argv)
        except SystemExit as exc:
            code = int(exc.code) if exc.code is not None else 0
    return code, out.getvalue(), err.getvalue()


def run_cli_subprocess(argv: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run ``python -m pytscheck`` as a real subprocess.

    Used by tests that need to verify process-level behavior: exit codes,
    stderr routing, environment isolation.
    """
    return subprocess.run(
        [sys.executable, "-m", "pytscheck", *argv],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
    )


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------


def parse_cli_json(stdout: str) -> dict[str, Any]:
    """Parse the JSON emitted by ``pytscheck ... --json``."""
    return json.loads(stdout)


def diagnostic_to_dict(d: Diagnostic) -> dict[str, Any]:
    """Convert a Diagnostic to the dict shape used in CLI --json output."""
    return {
        "file": d.file,
        "origin_file": d.origin_file,
        "line": d.line,
        "column": d.column,
        "end_line": d.end_line,
        "end_column": d.end_column,
        "code": d.code,
        "category": d.category,
        "message": d.message,
    }


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------


def write_bytes(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def file_has_executable_bit(path: Path) -> bool:
    """True on POSIX if the file has any executable bit set. Always True on Windows."""
    if os.name == "nt":
        return True
    return bool(path.stat().st_mode & 0o111)


def make_big_ts_source(n_lines: int) -> str:
    """Generate a syntactically valid .ts source with ``n_lines`` lines."""
    lines = ["export const values: number[] = ["]
    lines += [f"  {i}," for i in range(n_lines)]
    lines.append("];")
    return "\n".join(lines) + "\n"


def make_project_with_errors(root: Path, n_files: int, errors_per_file: int = 1) -> list[Path]:
    """Write ``n_files`` .ts files each with ``errors_per_file`` type errors."""
    (root / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}}\n',
        encoding="utf-8",
    )
    paths: list[Path] = []
    for i in range(n_files):
        lines = [f'export const bad_{i}_{j}: number = "s";' for j in range(errors_per_file)]
        p = root / f"file_{i}.ts"
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        paths.append(p)
    return paths



    def make_fake_tsgo(path: Path, *, behavior: str = "echo") -> Path:
   
    import os
    import sys

    path.parent.mkdir(parents=True, exist_ok=True)

    if os.name == "nt":
        # Batch file: not fully portable but adequate for tests.
        body = _fake_tsgo_windows_body(behavior)
        path.write_text(body, encoding="utf-8")
    else:
        body = _fake_tsgo_posix_body(behavior)
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)

    return path



    def build_wheel(repo_root: Path, outdir: Path) -> Path:
    """Build a real wheel via `python -m build`. Returns the .whl path.

    Skips are handled by the caller. Raises RuntimeError if the build fails.
    """
    import subprocess
    import sys

    outdir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(outdir)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
        shell=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"wheel build failed (exit {result.returncode}):\n{result.stderr}"
        )
    wheels = sorted(outdir.glob("*.whl"))
    if not wheels:
        raise RuntimeError(f"no wheel found in {outdir} after build")
    return wheels[-1]


def build_sdist(repo_root: Path, outdir: Path) -> Path:
    """Build a real sdist via `python -m build`."""
    import subprocess
    import sys

    outdir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--outdir", str(outdir)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
        shell=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"sdist build failed (exit {result.returncode}):\n{result.stderr}"
        )
    sdists = sorted(outdir.glob("*.tar.gz"))
    if not sdists:
        raise RuntimeError(f"no sdist found in {outdir} after build")
    return sdists[-1]


def list_wheel_members(wheel: Path) -> list[str]:
    """Return the sorted member names of a wheel (a zip file)."""
    import zipfile

    with zipfile.ZipFile(wheel) as zf:
        return sorted(zf.namelist())


def read_metadata_from_wheel(wheel: Path) -> str:
    """Return the text of the wheel's METADATA file."""
    import zipfile

    with zipfile.ZipFile(wheel) as zf:
        for name in zf.namelist():
            if name.endswith(".dist-info/METADATA"):
                return zf.read(name).decode("utf-8")
    raise FileNotFoundError(f"no METADATA in {wheel}")


def read_license_from_wheel(wheel: Path) -> bytes | None:
    """Return the wheel's LICENSE file bytes, if present."""
    import zipfile

    with zipfile.ZipFile(wheel) as zf:
        for name in zf.namelist():
            if name.endswith("/LICENSE") or name.endswith(".dist-info/LICENSE"):
                return zf.read(name)
    return None


def read_manifest_json_from_wheel(wheel: Path) -> dict:
    """Return the parsed bin/manifest.json bundled in the wheel."""
    import json
    import zipfile

    with zipfile.ZipFile(wheel) as zf:
        for name in zf.namelist():
            if name.endswith("pytscheck/bin/manifest.json"):
                return json.loads(zf.read(name).decode("utf-8"))
    raise FileNotFoundError(f"no manifest.json in {wheel}")


def installed_in_clean_venv(wheel: Path, tmp_path: Path) -> Path:
    """Create a real venv, install the wheel with --no-index, return python path.

    Never touches the network. Raises RuntimeError if install fails.
    """
    import subprocess
    import sys

    venv_dir = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        check=True,
        capture_output=True,
        timeout=120,
    )
    if sys.platform == "win32":
        py = venv_dir / "Scripts" / "python.exe"
    else:
        py = venv_dir / "bin" / "python"

    result = subprocess.run(
        [str(py), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        shell=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pip install failed (exit {result.returncode}):\n{result.stderr}"
        )
    return py


def _fake_tsgo_posix_body(behavior: str) -> str:
    if behavior == "echo":
        return '#!/bin/sh\necho "$@"\nexit 0\n'
    if behavior == "error":
        return (
            '#!/bin/sh\n'
            'echo "fake.ts(1,1): error TS9999: fake error" 1>&2\n'
            'exit 1\n'
        )
    if behavior == "hang":
        return '#!/bin/sh\nsleep 3600\n'
    if behavior == "crash":
        # SIGSEGV kills the process; the shell reports it via the exit code.
        return '#!/bin/sh\nkill -SEGV $$\n'
    if behavior == "garbage":
        return '#!/bin/sh\necho "this is not a diagnostic line"\nexit 0\n'
    if behavior == "big":
        return '#!/bin/sh\nyes "line of output" | head -n 1000000\n'
    raise ValueError(f"unknown fake behavior: {behavior}")


def _fake_tsgo_windows_body(behavior: str) -> str:
    if behavior == "echo":
        return "@echo off\necho %*\r\nexit /b 0\r\n"
    if behavior == "error":
        return (
            "@echo off\r\n"
            "echo fake.ts(1,1): error TS9999: fake error 1>&2\r\n"
            "exit /b 1\r\n"
        )
    if behavior == "hang":
        return "@echo off\r\n:loop\r\ngoto loop\r\n"
    if behavior == "crash":
        return "@echo off\r\nexit /b 139\r\n"
    if behavior == "garbage":
        return "@echo off\r\necho this is not a diagnostic line\r\nexit /b 0\r\n"
    if behavior == "big":
        return (
            "@echo off\r\n"
            "for /L %%i in (1,1,100000) do echo line of output\r\n"
        )
    raise ValueError(f"unknown fake behavior: {behavior}")


def make_fake_tsgo_on_path(
    path: Path, *, behavior: str = "echo"
) -> tuple[Path, Path]:
    """Create a fake tsgo directory with a `lib/` subdirectory containing
    the fake binary. Returns (platform_dir, binary_path).
    """
    platform_dir = path / "fake-platform"
    lib = platform_dir / "lib"
    lib.mkdir(parents=True, exist_ok=True)
    exe_name = "tsgo.exe" if __import__("os").name == "nt" else "tsgo"
    binary = lib / exe_name
    make_fake_tsgo(binary, behavior=behavior)
    return platform_dir, binary


# ---------------------------------------------------------------------------
# Context managers
# ---------------------------------------------------------------------------


@contextmanager
def without_module(module_name: str):
    """Temporarily remove a module from sys.modules for import-behavior tests."""
    saved = sys.modules.pop(module_name, None)
    try:
        yield
    finally:
        sys.modules.pop(module_name, None)
        if saved is not None:
            sys.modules[module_name] = saved


@contextmanager
def hide_file(path: Path):
    """Temporarily move a file out of the way, restoring it afterward.

    Used by tests that need to verify behavior when a real file is missing
    (e.g., the bundled binary). The file is restored even if the block raises.
    """
    hidden = path.with_suffix(path.suffix + ".hidden-by-test")
    if hidden.exists():
        raise RuntimeError(f"refusing to hide: {hidden} already exists")
    if path.exists():
        path.rename(hidden)
    try:
        yield hidden
    finally:
        if hidden.exists():
            hidden.rename(path)