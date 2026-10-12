#!/usr/bin/env python3
"""Build all platform distributions, validate them, and upload with Twine."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLATFORMS = (
    "linux-x64",
    "linux-arm64",
    "win32-x64",
    "win32-arm64",
    "darwin-x64",
    "darwin-arm64",
)


def package_version() -> str:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = metadata["project"]["version"]
    module = ast.parse((ROOT / "src/pytscheck/version.py").read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets
        ):
            if ast.literal_eval(node.value) != version:
                raise ValueError("pyproject.toml and src/pytscheck/version.py versions differ")
            return str(version)
    raise ValueError("cannot locate package __version__")


def command(*args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run([sys.executable, "-m", *args], cwd=ROOT, env=env, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository", choices=("pypi", "testpypi"), default="pypi", help="upload destination"
    )
    parser.add_argument("--build-only", action="store_true", help="build/check without uploading")
    args = parser.parse_args(argv)
    try:
        version = package_version()
        for module in ("build", "twine"):
            if importlib.util.find_spec(module) is None:
                raise ValueError("Install tools first: python -m pip install --upgrade build twine")
        # Keep old artifacts intact and prevent stale versions entering an upload.
        release_root = ROOT / "build" / "releases"
        release_root.mkdir(parents=True, exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix=f"{version}-", dir=release_root))
        print(f"Building pytscheck {version} into {output}", flush=True)
        for platform in PLATFORMS:
            print(f"Building {platform}", flush=True)
            command(
                "build",
                "--wheel",
                "--outdir",
                str(output),
                env={**os.environ, "PYTSCHECK_BUILD_PLATFORM": platform},
            )
        command("build", "--sdist", "--outdir", str(output))
        wheels = sorted(output.glob("*.whl"))
        sources = sorted(output.glob("*.tar.gz"))
        if len(wheels) != len(PLATFORMS) or len(sources) != 1:
            raise ValueError("expected exactly six wheels and one source archive")
        if any(not path.name.startswith(f"pytscheck-{version}-") for path in wheels):
            raise ValueError("wheel version does not match the intended release")
        if sources[0].name != f"pytscheck-{version}.tar.gz":
            raise ValueError("source archive version does not match the intended release")
        from release_check import check_wheel_contents

        for wheel in wheels:
            check = check_wheel_contents(wheel)
            if not check.ok:
                raise ValueError(f"invalid wheel {wheel.name}: {check.detail}")
        artifacts = [str(path) for path in [*wheels, *sources]]
        command("twine", "check", "--strict", *artifacts)
        print(f"Validated seven distributions: {output}", flush=True)
        if args.build_only:
            return 0
        print(f"Uploading to {args.repository}; Twine will request your API token.", flush=True)
        command("twine", "upload", "--repository", args.repository, *artifacts)
        print(f"Published pytscheck {version} to {args.repository}", flush=True)
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"Publication stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
