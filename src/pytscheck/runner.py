"""Runs the bundled tsgo binary as a subprocess."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .defaults import (
    DEFAULT_MAX_STDERR_BYTES,
    DEFAULT_MAX_STDOUT_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
)
from .exceptions import (
    CompilerExecutionError,
    CompilerNotFoundError,
    CompilerTimeoutError,
)

_PLATFORM_DIRS: dict[tuple[str, str], str] = {
    ("win32", "amd64"): "windows-amd64",
    ("win32", "x86_64"): "windows-amd64",
    ("win32", "arm64"): "windows-arm64",
    ("linux", "x86_64"): "linux-amd64",
    ("linux", "amd64"): "linux-amd64",
    ("linux", "aarch64"): "linux-arm64",
    ("linux", "arm64"): "linux-arm64",
    ("darwin", "x86_64"): "darwin-amd64",
    ("darwin", "arm64"): "darwin-arm64",
}


@dataclass(frozen=True, slots=True)
class RunResult:
    """Raw result of a tsgo invocation."""

    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float
    argv: tuple[str, ...]


def _platform_dir() -> str:
    key = (sys.platform, os.uname().machine if hasattr(os, "uname") else "unknown")
    # os.uname is POSIX-only; on Windows fall back to environment.
    if sys.platform == "win32":
        arch = os.environ.get("PROCESSOR_ARCHITECTURE", "").lower()
        machine = {"amd64": "amd64", "arm64": "arm64", "x86": "x86_64"}.get(arch, "amd64")
        key = ("win32", machine)

    try:
        return _PLATFORM_DIRS[key]
    except KeyError as exc:
        from .exceptions import UnsupportedPlatformError

        raise UnsupportedPlatformError(
            f"no bundled tsgo binary for platform={sys.platform!r} arch={key[1]!r}"
        ) from exc


def binary_path() -> Path:
    """Locate the bundled tsgo executable for the current platform."""
    here = Path(__file__).resolve().parent
    platform_dir = _platform_dir()
    exe_name = "tsgo.exe" if sys.platform == "win32" else "tsgo"
    candidate = here / "bin" / platform_dir / "lib" / exe_name
    if not candidate.exists():
        raise CompilerNotFoundError(
            f"bundled tsgo not found at {candidate}. "
            f"Run `python scripts/build_binaries.py {platform_dir.replace('-', '_')}` "
            f"or reinstall pytscheck."
        )
    if sys.platform != "win32" and not os.access(candidate, os.X_OK):
        raise CompilerNotFoundError(
            f"bundled tsgo at {candidate} is not executable"
        )
    return candidate


def run(
    argv_tail: list[str],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_stdout_bytes: int = DEFAULT_MAX_STDOUT_BYTES,
    max_stderr_bytes: int = DEFAULT_MAX_STDERR_BYTES,
    cwd: Path | None = None,
) -> RunResult:
    """Invoke bundled tsgo with the given trailing arguments.

    Never uses a shell. Captures stdout and stderr separately. Enforces
    timeout and output-size limits.
    """
    exe = binary_path()
    argv = [str(exe), *argv_tail]

    start = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CompilerTimeoutError(
            f"tsgo exceeded {timeout}s timeout",
            stdout=_decode(exc.stdout),
            stderr=_decode(exc.stderr),
        ) from exc
    except OSError as exc:
        raise CompilerExecutionError(f"failed to launch tsgo: {exc}") from exc

    elapsed = time.monotonic() - start

    if len(proc.stdout) > max_stdout_bytes:
        raise CompilerExecutionError(
            f"tsgo stdout exceeded {max_stdout_bytes} bytes"
        )
    if len(proc.stderr) > max_stderr_bytes:
        raise CompilerExecutionError(
            f"tsgo stderr exceeded {max_stderr_bytes} bytes"
        )

    return RunResult(
        returncode=proc.returncode,
        stdout=_decode(proc.stdout),
        stderr=_decode(proc.stderr),
        elapsed_seconds=elapsed,
        argv=tuple(argv),
    )


def _decode(data: bytes | None) -> str:
    if not data:
        return ""
    return data.decode("utf-8", errors="replace")


__all__ = ["RunResult", "binary_path", "run"]