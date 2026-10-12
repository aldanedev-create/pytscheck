"""Runs the bundled tsgo binary as a subprocess."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import tempfile
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
    ("darwin", "amd64"): "darwin-amd64",
    ("darwin", "arm64"): "darwin-arm64",
    ("darwin", "aarch64"): "darwin-arm64",
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
    if not candidate.is_file():
        download_target = {
            "linux-amd64": "linux-x64",
            "linux-arm64": "linux-arm64",
            "darwin-amd64": "darwin-x64",
            "darwin-arm64": "darwin-arm64",
            "windows-amd64": "win32-x64",
            "windows-arm64": "win32-arm64",
        }[platform_dir]
        raise CompilerNotFoundError(
            f"bundled tsgo not found at {candidate}. "
            f"Run `python scripts/build_binaries.py {download_target}` "
            f"or reinstall pytscheck."
        )
    if sys.platform != "win32" and not os.access(candidate, os.X_OK):
        raise CompilerNotFoundError(f"bundled tsgo at {candidate} is not executable")
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
    # Diagnostics must stay machine-readable even when FORCE_COLOR is set.
    argv = [str(exe), *argv_tail, "--pretty", "false"]

    start = time.monotonic()
    # Files avoid inherited pipe handles keeping communicate() alive after a
    # timeout. Poll their sizes during execution; read only bounded data.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            proc = subprocess.Popen(
                argv,
                cwd=str(cwd) if cwd else None,
                stdout=stdout,
                stderr=stderr,
                shell=False,
                start_new_session=os.name == "posix",
            )
        except OSError as exc:
            raise CompilerExecutionError(f"failed to launch tsgo: {exc}") from exc
        try:
            while True:
                for stream, limit, name in (
                    (stdout, max_stdout_bytes, "stdout"),
                    (stderr, max_stderr_bytes, "stderr"),
                ):
                    if os.fstat(stream.fileno()).st_size > limit:
                        raise CompilerExecutionError(f"tsgo {name} exceeded {limit} bytes")
                remaining = timeout - (time.monotonic() - start)
                if remaining <= 0:
                    stdout.seek(0)
                    stderr.seek(0)
                    raise CompilerTimeoutError(
                        f"tsgo exceeded {timeout}s timeout",
                        stdout=_decode(
                            stdout.read(min(max_stdout_bytes, os.fstat(stdout.fileno()).st_size))
                        ),
                        stderr=_decode(
                            stderr.read(min(max_stderr_bytes, os.fstat(stderr.fileno()).st_size))
                        ),
                    )
                try:
                    proc.wait(timeout=min(0.02, remaining))
                except subprocess.TimeoutExpired:
                    continue
                # Recheck sizes after completion, including very fast producers.
                for stream, limit, name in (
                    (stdout, max_stdout_bytes, "stdout"),
                    (stderr, max_stderr_bytes, "stderr"),
                ):
                    if os.fstat(stream.fileno()).st_size > limit:
                        raise CompilerExecutionError(f"tsgo {name} exceeded {limit} bytes")
                break
        finally:
            if os.name == "posix":
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(proc.pid, signal.SIGKILL)
            elif proc.poll() is None:
                proc.kill()
            proc.wait()
        stdout.seek(0)
        stderr.seek(0)
        return RunResult(
            returncode=proc.returncode,
            stdout=_decode(stdout.read(min(max_stdout_bytes, os.fstat(stdout.fileno()).st_size))),
            stderr=_decode(stderr.read(min(max_stderr_bytes, os.fstat(stderr.fileno()).st_size))),
            elapsed_seconds=time.monotonic() - start,
            argv=tuple(argv),
        )


def _decode(data: bytes | None) -> str:
    if not data:
        return ""
    return data.decode("utf-8", errors="replace")


__all__ = ["RunResult", "binary_path", "run"]
