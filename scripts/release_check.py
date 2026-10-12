#!/usr/bin/env python3
"""Pre-release validation gate.

This is the single command that must pass before tagging a release. It
runs the checks that matter, in the order that fails fastest:

    1.  version consistency       (version.py, pyproject.toml, manifest.json)
    2.  license consistency       (LICENSE, NOTICE.txt, pyproject metadata)
    3.  platform consistency      (runner.py, generate_manifest.py, docs)
    4.  fixtures drift            (tests/fixtures/ vs generate_fixtures.py)
    5.  manifest drift            (src/pytscheck/bin/manifest.json vs disk)
    6.  bundled binary present    (for the current platform)
    7.  unit + integration tests  (pytest)
    8.  conformance               (conformance/run.py)
    9.  sdist + wheel build       (python -m build)
    10. wheel contents            (structure sanity)
    11. clean-venv install        (offline, --no-index)

With `--wheel-only`, only stages 9-11 run. That is what
`run_all_tests.py --only wheel-install` invokes.

Exit codes:

    0  all checks passed; safe to release
    1  a check failed; do not release
    2  usage error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src" / "pytscheck"
PYPROJECT = REPO_ROOT / "pyproject.toml"
VERSION_PY = SRC / "version.py"
MANIFEST = SRC / "bin" / "manifest.json"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    elapsed: float = 0.0
    skipped: bool = False


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)
    dry_run: bool = False

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    def add(self, check: Check) -> None:
        self.checks.append(check)


def _run(
    cmd: list[str], *, cwd: Path = REPO_ROOT, timeout: float = 600.0
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=False,
    )


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def check_version_consistency() -> Check:
    start = time.monotonic()
    if not VERSION_PY.exists():
        return Check("version", False, f"{VERSION_PY} not found", time.monotonic() - start)
    vtext = VERSION_PY.read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', vtext, re.M)
    if m is None:
        return Check("version", False, "no __version__ in version.py", time.monotonic() - start)
    vpy = m.group(1)

    ptext = PYPROJECT.read_text(encoding="utf-8")
    data = tomllib.loads(ptext)
    pv = data.get("project", {}).get("version")
    if pv is None:
        # Dynamic version via hatch
        hatch = data.get("tool", {}).get("hatch", {})
        if "version" in hatch:
            return Check(
                "version",
                True,
                f"version from {hatch['version'].get('path', '?')} = {vpy}",
                time.monotonic() - start,
            )
        return Check("version", False, "no static or dynamic version", time.monotonic() - start)

    if pv != vpy:
        return Check(
            "version",
            False,
            f"version.py={vpy!r}, pyproject.toml={pv!r}",
            time.monotonic() - start,
        )
    return Check("version", True, vpy, time.monotonic() - start)


def check_licenses() -> Check:
    start = time.monotonic()
    proc = _run([sys.executable, "scripts/check_licenses.py", "--quiet"])
    return Check(
        "license",
        proc.returncode == 0,
        "" if proc.returncode == 0 else (proc.stdout + proc.stderr)[:500],
        time.monotonic() - start,
    )


def check_platforms() -> Check:
    start = time.monotonic()
    proc = _run([sys.executable, "scripts/check_platforms.py", "--quiet"])
    return Check(
        "platforms",
        proc.returncode == 0,
        "" if proc.returncode == 0 else (proc.stdout + proc.stderr)[:500],
        time.monotonic() - start,
    )


def check_fixtures() -> Check:
    start = time.monotonic()
    proc = _run([sys.executable, "scripts/verify_fixtures.py", "--quiet", "--strict"])
    return Check(
        "fixtures",
        proc.returncode == 0,
        "" if proc.returncode == 0 else (proc.stdout + proc.stderr)[:500],
        time.monotonic() - start,
    )


def check_manifest() -> Check:
    start = time.monotonic()
    if not MANIFEST.exists():
        return Check(
            "manifest",
            False,
            f"{MANIFEST.relative_to(REPO_ROOT)} not found",
            time.monotonic() - start,
            skipped=True,
        )
    proc = _run([sys.executable, "scripts/generate_manifest.py", "--check"])
    if proc.returncode == 0:
        return Check("manifest", True, "", time.monotonic() - start)
    return Check(
        "manifest",
        False,
        (proc.stdout + proc.stderr)[:500],
        time.monotonic() - start,
    )


def check_binary_present() -> Check:
    start = time.monotonic()
    try:
        sys.path.insert(0, str(SRC.parent))
        from pytscheck.runner import binary_path  # type: ignore[import-not-found]

        path = binary_path()
        return Check(
            "binary",
            True,
            str(path.relative_to(REPO_ROOT)),
            time.monotonic() - start,
        )
    except Exception as exc:
        return Check(
            "binary",
            False,
            f"no bundled binary for this platform: {exc}",
            time.monotonic() - start,
            skipped=True,
        )


def check_pytest() -> Check:
    start = time.monotonic()
    proc = _run(
        [sys.executable, "-m", "pytest", "-q", "--ignore=tests/compatibility"],
        timeout=1800.0,
    )
    elapsed = time.monotonic() - start
    if proc.returncode == 0:
        return Check("pytest", True, "", elapsed)
    return Check(
        "pytest",
        False,
        (proc.stdout + proc.stderr)[-1000:],
        elapsed,
    )


def check_conformance() -> Check:
    start = time.monotonic()
    runner = REPO_ROOT / "conformance" / "run.py"
    if not runner.exists():
        return Check(
            "conformance",
            True,
            "no conformance runner",
            time.monotonic() - start,
            skipped=True,
        )
    proc = _run([sys.executable, str(runner), "--check"], timeout=900.0)
    if proc.returncode == 0:
        return Check("conformance", True, "", time.monotonic() - start)
    return Check(
        "conformance",
        False,
        (proc.stdout + proc.stderr)[-500:],
        time.monotonic() - start,
    )


def check_sdist_and_wheel(distdir: Path) -> Check:
    start = time.monotonic()
    if distdir.exists():
        shutil.rmtree(distdir)
    proc = _run(
        [sys.executable, "-m", "build", "--outdir", str(distdir)],
        timeout=900.0,
    )
    elapsed = time.monotonic() - start
    if proc.returncode != 0:
        return Check(
            "build",
            False,
            (proc.stdout + proc.stderr)[-500:],
            elapsed,
        )
    sdists = list(distdir.glob("*.tar.gz"))
    wheels = list(distdir.glob("*.whl"))
    if not sdists:
        return Check("build", False, "no sdist produced", elapsed)
    if not wheels:
        return Check("build", False, "no wheel produced", elapsed)
    return Check("build", True, f"{len(sdists)} sdist, {len(wheels)} wheel", elapsed)


def check_wheel_contents(wheel: Path) -> Check:
    start = time.monotonic()
    try:
        with zipfile.ZipFile(wheel) as zf:
            names = zf.namelist()
    except zipfile.BadZipFile as exc:
        return Check("wheel-contents", False, str(exc), time.monotonic() - start)

    problems: list[str] = []
    if not any(n.endswith("pytscheck/__init__.py") for n in names):
        problems.append("missing pytscheck/__init__.py")
    if not any(n.endswith("pytscheck/py.typed") for n in names):
        problems.append("missing pytscheck/py.typed")
    if not any(".dist-info/METADATA" in n for n in names):
        problems.append("missing METADATA")
    if not any(".dist-info/RECORD" in n for n in names):
        problems.append("missing RECORD")
    if any("__pycache__" in n for n in names):
        problems.append("contains __pycache__")
    if any(n.endswith(".pyc") for n in names):
        problems.append("contains .pyc")
    if any(n.startswith("tests/") for n in names):
        problems.append("contains tests/")

    binaries = [n for n in names if n.endswith(("/tsgo", "/tsgo.exe"))]
    if len(binaries) != 1:
        problems.append(f"expected exactly one native compiler, found {len(binaries)}")
    if not any(n.endswith(".d.ts") for n in names):
        problems.append("missing bundled TypeScript libraries")
    if "py3-none-any" in wheel.name:
        problems.append("native compiler wheel must carry a platform tag")

    if problems:
        return Check(
            "wheel-contents",
            False,
            "; ".join(problems),
            time.monotonic() - start,
        )
    return Check("wheel-contents", True, f"{len(names)} entries", time.monotonic() - start)


def check_clean_install(wheel: Path) -> Check:
    start = time.monotonic()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        venv = tmp_path / "venv"
        proc = _run([sys.executable, "-m", "venv", str(venv)], timeout=120.0)
        if proc.returncode != 0:
            return Check(
                "clean-install",
                False,
                "failed to create venv",
                time.monotonic() - start,
            )
        if sys.platform == "win32":
            py = venv / "Scripts" / "python.exe"
        else:
            py = venv / "bin" / "python"

        proc = subprocess.run(
            [str(py), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
            capture_output=True,
            text=True,
            timeout=180.0,
            check=False,
            shell=False,
        )
        if proc.returncode != 0:
            return Check(
                "clean-install",
                False,
                (proc.stdout + proc.stderr)[-500:],
                time.monotonic() - start,
            )

        proc = subprocess.run(
            [
                str(py),
                "-c",
                (
                    "import pytscheck; from pytscheck import check; "
                    "r=check('export const x: number = 1;'); "
                    "assert r.success, r.diagnostics; "
                    "r=check('export const x: number = \"bad\";'); "
                    "assert any(d.code == 2322 for d in r.errors), r.diagnostics; "
                    "print(pytscheck.__version__)"
                ),
            ],
            cwd=tmp_path,
            env={k: ("" if k == "PATH" else v) for k, v in os.environ.items() if k != "PYTHONPATH"},
            capture_output=True,
            text=True,
            timeout=30.0,
            check=False,
            shell=False,
        )
        if proc.returncode != 0:
            return Check(
                "clean-install",
                False,
                (proc.stdout + proc.stderr)[-500:],
                time.monotonic() - start,
            )
        version = proc.stdout.strip()
        return Check("clean-install", True, version, time.monotonic() - start)


def check_no_node_required() -> Check:
    start = time.monotonic()
    if shutil.which("node") is None:
        return Check(
            "no-node",
            True,
            "node not installed; test is trivially satisfied",
            time.monotonic() - start,
            skipped=True,
        )
    return Check(
        "no-node",
        True,
        "node present; isolation is verified by tests/test_no_node_required.py",
        time.monotonic() - start,
        skipped=True,
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def run_all_checks(*, wheel_only: bool, distdir: Path) -> Report:
    report = Report()

    if not wheel_only:
        report.add(check_version_consistency())
        report.add(check_licenses())
        report.add(check_platforms())
        report.add(check_fixtures())
        report.add(check_manifest())
        report.add(check_binary_present())
        report.add(check_pytest())
        report.add(check_conformance())

    report.add(check_sdist_and_wheel(distdir))

    wheels = sorted(distdir.glob("*.whl"))
    if wheels:
        wheel = wheels[-1]
        report.add(check_wheel_contents(wheel))
        report.add(check_clean_install(wheel))

    report.add(check_no_node_required())
    return report


def _print_report(report: Report, *, as_json: bool) -> None:
    if as_json:
        print(
            json.dumps(
                {
                    "ok": report.ok,
                    "checks": [
                        {
                            "name": c.name,
                            "ok": c.ok,
                            "skipped": c.skipped,
                            "detail": c.detail,
                            "elapsed": c.elapsed,
                        }
                        for c in report.checks
                    ],
                },
                indent=2,
            )
        )
        return

    width = max((len(c.name) for c in report.checks), default=10)
    print("Release check")
    print()
    for c in report.checks:
        status = "SKIP" if c.skipped else ("OK  " if c.ok else "FAIL")
        detail = f"  {c.detail}" if c.detail else ""
        print(f"  {status}  {c.name:<{width}}{detail}")

    ok = sum(1 for c in report.checks if c.ok and not c.skipped)
    failed = sum(1 for c in report.checks if not c.ok)
    skipped = sum(1 for c in report.checks if c.skipped)
    print()
    print(f"  {ok} passed, {failed} failed, {skipped} skipped")
    print()
    if report.ok:
        print("RELEASE OK")
    else:
        print("RELEASE BLOCKED")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release_check",
        description="Pre-release validation gate.",
    )
    parser.add_argument(
        "--wheel-only",
        action="store_true",
        help="only run build + wheel contents + clean-install checks",
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=REPO_ROOT / "dist",
        help="where to place built artifacts (default: ./dist)",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = run_all_checks(wheel_only=args.wheel_only, distdir=args.dist_dir)
    _print_report(report, as_json=args.json)
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
