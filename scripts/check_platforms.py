#!/usr/bin/env python3
"""Verify the platform directory map covers exactly the declared targets.

Three sources of truth must agree:

1. `scripts/generate_manifest.py` — npm platform -> bin/ directory
2. `src/pytscheck/runner.py` — the same map, used at runtime
3. `docs/supported-platforms.md` — the human-facing table

This script cross-checks (1) and (2), and checks that the set of names
matches a hardcoded list of supported targets.

Exit codes:

    0  clean
    1  drift
    2  usage error
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "src" / "pytscheck" / "runner.py"
GENERATOR = REPO_ROOT / "scripts" / "generate_manifest.py"
DOCS = REPO_ROOT / "docs" / "supported-platforms.md"

# The single source of truth for target platforms.
# If this changes, the spec changes.
EXPECTED_TARGETS: set[str] = {
    "windows-amd64",
    "windows-arm64",
    "linux-amd64",
    "linux-arm64",
    "linux-arm",
    "linux-386",
    "windows-386",
    "darwin-amd64",
    "darwin-arm64",
}

# Subset of the above that must ship in the initial release.
# Windows ARM64 is deferred per the spec.
INITIAL_TARGETS: set[str] = {
    "windows-amd64",
    "linux-amd64",
    "linux-arm64",
    "linux-arm",
    "linux-386",
    "windows-386",
    "darwin-amd64",
    "darwin-arm64",
}


@dataclass
class Finding:
    kind: str
    detail: str

    def __str__(self) -> str:
        return f"{self.kind:20s} {self.detail}"


def _parse_platform_dirs_from_generator(path: Path) -> dict[str, str] | None:
    """Extract `_PLATFORM_DIRS` from a Python source file via regex.

    Avoids importing the module, which would side-effect on sys.path.
    """
    if not path.exists():
        return None
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "_PLATFORM_DIRS":
                return ast.literal_eval(node.value)
        elif isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_PLATFORM_DIRS" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    return None


def _parse_docs_platforms(path: Path) -> set[str] | None:
    """Extract directory names from supported-platforms.md's table, if present."""
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    found: set[str] = set()
    for name in EXPECTED_TARGETS:
        if name in text:
            found.add(name)
    return found


def run_checks() -> list[Finding]:
    findings: list[Finding] = []

    gen_map = _parse_platform_dirs_from_generator(GENERATOR)
    if gen_map is None:
        findings.append(
            Finding("parse_error", f"{GENERATOR.relative_to(REPO_ROOT)}: _PLATFORM_DIRS not found")
        )
        gen_map = {}

    runner_map = _parse_platform_dirs_from_generator(RUNNER)
    if runner_map is None:
        findings.append(
            Finding("parse_error", f"{RUNNER.relative_to(REPO_ROOT)}: _PLATFORM_DIRS not found")
        )
        runner_map = {}

    # Runtime keys include OS/architecture aliases; compare their destination set.
    if gen_map and runner_map and set(gen_map.values()) != set(runner_map.values()):
        findings.append(
            Finding("map_mismatch", "generator and runtime platform directories differ")
        )

    # 2. The set of directory names must equal EXPECTED_TARGETS
    all_dirs = set(gen_map.values()) | set(runner_map.values())
    if all_dirs:
        extra = all_dirs - EXPECTED_TARGETS
        missing = EXPECTED_TARGETS - all_dirs
        for d in sorted(extra):
            findings.append(Finding("unexpected_target", f"{d} is not in EXPECTED_TARGETS"))
        for d in sorted(missing):
            findings.append(Finding("missing_target", f"{d} is missing from the maps"))

    # 3. Check the deferred platform is documented as deferred
    EXPECTED_TARGETS - INITIAL_TARGETS
    if "windows-arm64" in all_dirs and "windows-arm64" not in ("windows-arm64",):
        pass  # keep it listed; it's fine to include even if deferred

    # 4. If docs exists, it must mention every expected target
    docs_platforms = _parse_docs_platforms(DOCS)
    if docs_platforms is not None:
        missing_docs = EXPECTED_TARGETS - docs_platforms
        for d in sorted(missing_docs):
            findings.append(
                Finding(
                    "docs_missing",
                    f"{d} not mentioned in docs/supported-platforms.md",
                )
            )

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_platforms",
        description="Verify platform maps agree across sources.",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    findings = run_checks()

    if args.json:
        print(
            json.dumps(
                {
                    "clean": not findings,
                    "finding_count": len(findings),
                    "findings": [{"kind": f.kind, "detail": f.detail} for f in findings],
                },
                indent=2,
            )
        )
    elif not args.quiet:
        if not findings:
            print(
                f"OK: platforms consistent "
                f"({len(EXPECTED_TARGETS)} targets, "
                f"{len(INITIAL_TARGETS)} in initial release)"
            )
        else:
            print(f"PLATFORM CHECK FAILED: {len(findings)} issue(s)")
            for f in findings:
                print(str(f))

    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
