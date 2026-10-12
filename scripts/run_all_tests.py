#!/usr/bin/env python3
"""Run every test and release check, or one selected test stage."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGES = (
    "unit",
    "integration",
    "compatibility",
    "security",
    "fuzz",
    "conformance",
    "benchmarks",
    "wheel-install",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        action="append",
        choices=STAGES,
        help="run only this stage; repeat to select several",
    )
    args = parser.parse_args(argv)
    commands = {
        "unit": [
            "-m",
            "pytest",
            "tests",
            "--ignore=tests/integration",
            "--ignore=tests/compatibility",
            "--ignore=tests/security",
            "--ignore=tests/fuzz",
            "-q",
        ],
        **{name: ["-m", "pytest", f"tests/{name}", "-q"] for name in STAGES[1:5]},
        "conformance": ["conformance/run.py"],
        "benchmarks": ["benchmarks/run.py", "--json"],
        "wheel-install": ["scripts/release_check.py", "--wheel-only"],
    }
    for stage in args.only or STAGES:
        print(f"Running {stage}", flush=True)
        result = subprocess.run(
            [sys.executable, *commands[stage]], cwd=REPO_ROOT, check=False, shell=False
        )
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
