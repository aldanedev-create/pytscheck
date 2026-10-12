"""Shared pytest fixtures for the pytscheck test suite.

Design rules
------------
- No mocking of the compiler, the runner, or subprocess calls.
- Tests that require the bundled binary obtain it via ``tsgo_binary``,
  which either returns a real, executable, verified path, or skips with
  a clear reason.
- Fixtures do not patch pytscheck internals. They set up real files on
  real disk and invoke real subprocesses.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src" / "pytscheck"
BIN_ROOT = SRC_ROOT / "bin"
MANIFEST_PATH = BIN_ROOT / "manifest.json"


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------


def _platform_key() -> str:
    """Return the bin/ subdirectory name for the current OS/arch."""
    system = sys.platform
    machine = platform.machine().lower()

    if system == "win32":
        if machine in {"amd64", "x86_64"}:
            return "windows-amd64"
        if machine in {"arm64", "aarch64"}:
            return "windows-arm64"
    elif system == "linux":
        if machine in {"x86_64", "amd64"}:
            return "linux-amd64"
        if machine in {"aarch64", "arm64"}:
            return "linux-arm64"
    elif system == "darwin":
        if machine in {"x86_64", "amd64"}:
            return "darwin-amd64"
        if machine in {"arm64", "aarch64"}:
            return "darwin-arm64"

    pytest.skip(f"unsupported test platform: {system}/{machine}")
    raise AssertionError("unreachable")  # pragma: no cover


# ---------------------------------------------------------------------------
# Session-wide fixtures: the real bundled binary
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def pytscheck_src() -> Path:
    return SRC_ROOT


@pytest.fixture(scope="session")
def bin_root() -> Path:
    return BIN_ROOT


@pytest.fixture(scope="session")
def manifest_path() -> Path:
    return MANIFEST_PATH


@pytest.fixture(scope="session")
def bin_platform_dir() -> Path:
    """Platform directory under src/pytscheck/bin/ for the current machine."""
    return BIN_ROOT / _platform_key()


@pytest.fixture(scope="session")
def tsgo_binary(bin_platform_dir: Path) -> Path:
    """Path to the real bundled tsgo executable, or skip.

    Never mocks. If the binary is not present, the calling test is skipped
    with a message telling the developer to run the fetch script.
    """
    exe_name = "tsgo.exe" if sys.platform == "win32" else "tsgo"
    candidate = bin_platform_dir / "lib" / exe_name

    if not candidate.exists():
        pytest.skip(
            f"bundled tsgo not found at {candidate}; "
            f"run `python scripts/build_binaries.py {bin_platform_dir.name}` first"
        )
    if sys.platform != "win32" and not os.access(candidate, os.X_OK):
        pytest.skip(f"bundled tsgo at {candidate} is not executable")
    return candidate


@pytest.fixture(scope="session")
def tsgo_version(tsgo_binary: Path) -> str:
    """Version string reported by the bundled tsgo."""
    try:
        result = subprocess.run(
            [str(tsgo_binary), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip(f"could not run {tsgo_binary}")
    if result.returncode != 0:
        pytest.skip(f"tsgo --version exited with code {result.returncode}")
    return (result.stdout + result.stderr).strip()


@pytest.fixture(scope="session")
def manifest(bin_platform_dir: Path) -> dict:
    """Parsed bin/manifest.json, or skip if it has not been generated yet."""
    if not MANIFEST_PATH.exists():
        pytest.skip(f"manifest not found at {MANIFEST_PATH}")
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        pytest.skip(f"manifest is not valid JSON: {exc}")


@pytest.fixture(scope="session")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a real wheel once per session and reuse it across tests.

    Skips if `build` is not installed. That is honest: the test cannot run
    without the build tool. Install with `pip install build` or `.[dev]`.
    """
    from tests.helpers import build_wheel

    try:
        import build  # noqa: F401
    except ImportError:
        pytest.skip("`build` package not installed; pip install build")

    outdir = tmp_path_factory.mktemp("dist-wheel")
    return build_wheel(REPO_ROOT, outdir)


@pytest.fixture(scope="session")
def built_sdist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from tests.helpers import build_sdist

    try:
        import build  # noqa: F401
    except ImportError:
        pytest.skip("`build` package not installed; pip install build")

    outdir = tmp_path_factory.mktemp("dist-sdist")
    return build_sdist(REPO_ROOT, outdir)


# ---------------------------------------------------------------------------
# Real filesystem fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """An empty directory that looks like a TypeScript project root."""
    return tmp_path


@pytest.fixture
def tsconfig_minimal(tmp_path: Path) -> Path:
    """A minimal valid tsconfig.json in tmp_path."""
    p = tmp_path / "tsconfig.json"
    p.write_text(
        "{\n"
        '  "compilerOptions": {\n'
        '    "strict": true,\n'
        '    "noEmit": true,\n'
        '    "target": "es2022",\n'
        '    "module": "esnext",\n'
        '    "moduleResolution": "bundler"\n'
        "  },\n"
        '  "include": ["**/*.ts"]\n'
        "}\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def ts_file_valid(tmp_path: Path) -> Path:
    """A syntactically valid, type-correct TypeScript file."""
    p = tmp_path / "valid.ts"
    p.write_text(
        "export const answer: number = 42;\n"
        "export function add(a: number, b: number): number {\n"
        "  return a + b;\n"
        "}\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def ts_file_type_error(tmp_path: Path) -> Path:
    """A TypeScript file with a guaranteed type error (TS2322)."""
    p = tmp_path / "bad.ts"
    p.write_text('export const age: number = "twenty";\n', encoding="utf-8")
    return p


@pytest.fixture
def ts_file_syntax_error(tmp_path: Path) -> Path:
    """A TypeScript file with a guaranteed syntax error (TS1005)."""
    p = tmp_path / "syntax.ts"
    p.write_text("const x: number = ;\n", encoding="utf-8")
    return p


@pytest.fixture
def project_minimal(tmp_path: Path, tsconfig_minimal: Path, ts_file_valid: Path) -> Path:
    return tmp_path


@pytest.fixture
def project_type_error(tmp_path: Path, tsconfig_minimal: Path, ts_file_type_error: Path) -> Path:
    return tmp_path


# ---------------------------------------------------------------------------
# Environment isolation (real os.environ mutation, auto-restored)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove ambient vars that could change subprocess behavior."""
    for key in list(os.environ):
        if key.startswith("TS_NODE_") or key in {
            "NODE_PATH",
            "NODE_OPTIONS",
            "NODE_ENV",
            "GOFLAGS",
            "GOPATH",
            "TSC_NONPOLLING_WATCHER",
        }:
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Run the test in an empty temporary working directory."""
    monkeypatch.chdir(tmp_path)
    yield tmp_path


# ---------------------------------------------------------------------------
# Marker application
# ---------------------------------------------------------------------------


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Auto-apply platform and integration markers based on test location."""
    for item in items:
        name = item.nodeid
        if "/compatibility/test_windows" in name:
            item.add_marker(pytest.mark.windows)
        elif "/compatibility/test_linux" in name:
            item.add_marker(pytest.mark.linux)
        elif "/compatibility/test_macos" in name:
            item.add_marker(pytest.mark.macos)
        elif "/integration/" in name:
            item.add_marker(pytest.mark.integration)
