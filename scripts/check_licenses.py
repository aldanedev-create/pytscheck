#!/usr/bin/env python3
"""Verify license and notice files are present and consistent.

Checks three things:

1. The repo has LICENSE and NOTICE.txt at the root.
2. The bundled binaries include their upstream LICENSE and NOTICE.txt.
3. The package metadata (pyproject.toml) declares the expected license.

Exit codes:

    0  clean
    1  missing or mismatched license file
    2  usage error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN_ROOT = REPO_ROOT / "src" / "pytscheck" / "bin"
PYPROJECT = REPO_ROOT / "pyproject.toml"

EXPECTED_SPDX = "Apache-2.0"
EXPECTED_LICENSE_SUBSTRINGS = ("Apache License", "Version 2.0")
NOTICE_REQUIRED_SUBSTRINGS = ("typescript", "apache")


@dataclass
class Finding:
    kind: str
    path: str
    detail: str = ""

    def __str__(self) -> str:
        if self.detail:
            return f"{self.kind:20s} {self.path}\n  {self.detail}"
        return f"{self.kind:20s} {self.path}"


def _check_root_files() -> list[Finding]:
    findings: list[Finding] = []
    license_path = REPO_ROOT / "LICENSE"
    notice_path = REPO_ROOT / "NOTICE.txt"

    if not license_path.exists():
        findings.append(Finding("missing", "LICENSE"))
    else:
        text = license_path.read_text(encoding="utf-8", errors="replace")
        for sub in EXPECTED_LICENSE_SUBSTRINGS:
            if sub not in text:
                findings.append(
                    Finding(
                        "license_mismatch",
                        "LICENSE",
                        f"missing substring: {sub!r}",
                    )
                )

    if not notice_path.exists():
        findings.append(Finding("missing", "NOTICE.txt"))
    else:
        text = notice_path.read_text(encoding="utf-8", errors="replace").lower()
        for sub in NOTICE_REQUIRED_SUBSTRINGS:
            if sub not in text:
                findings.append(
                    Finding(
                        "notice_mismatch",
                        "NOTICE.txt",
                        f"missing substring: {sub!r}",
                    )
                )

    return findings


def _check_pyproject() -> list[Finding]:
    findings: list[Finding] = []
    if not PYPROJECT.exists():
        findings.append(Finding("missing", "pyproject.toml"))
        return findings
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    license_field = data.get("project", {}).get("license")
    if isinstance(license_field, dict):
        value = license_field.get("text")
    else:
        value = license_field
    if value != EXPECTED_SPDX:
        findings.append(
            Finding(
                "metadata_mismatch",
                "pyproject.toml",
                f"license is {value!r}, expected {EXPECTED_SPDX!r}",
            )
        )
    return findings


def _check_bundled_binaries() -> list[Finding]:
    """For every platform dir that contains a tsgo binary, require LICENSE
    and NOTICE.txt to be present somewhere in that directory tree."""
    findings: list[Finding] = []
    if not BIN_ROOT.exists():
        return findings

    for platform_dir in sorted(BIN_ROOT.iterdir()):
        if not platform_dir.is_dir():
            continue
        # Skip the manifest file's sibling behavior
        binaries = list(platform_dir.rglob("tsgo")) + list(
            platform_dir.rglob("tsgo.exe")
        )
        if not binaries:
            continue
        license_files = list(platform_dir.rglob("LICENSE")) + list(
            platform_dir.rglob("LICENSE.txt")
        )
        notice_files = list(platform_dir.rglob("NOTICE.txt")) + list(
            platform_dir.rglob("NOTICE")
        )
        rel = platform_dir.relative_to(REPO_ROOT).as_posix()
        if not license_files:
            findings.append(
                Finding(
                    "missing_bundled",
                    f"{rel}/LICENSE",
                    "bundled binary present but no LICENSE alongside it",
                )
            )
        if not notice_files:
            findings.append(
                Finding(
                    "missing_bundled",
                    f"{rel}/NOTICE.txt",
                    "bundled binary present but no NOTICE.txt alongside it",
                )
            )
    return findings


def _check_notice_mentions_compiler() -> list[Finding]:
    """NOTICE.txt must name the bundled compiler."""
    findings: list[Finding] = []
    notice_path = REPO_ROOT / "NOTICE.txt"
    if not notice_path.exists():
        return findings
    text = notice_path.read_text(encoding="utf-8", errors="replace")
    # Should mention either "typescript" or "tsgo"
    if not re.search(r"\b(typescript|tsgo)\b", text, re.IGNORECASE):
        findings.append(
            Finding(
                "notice_incomplete",
                "NOTICE.txt",
                "does not mention the bundled TypeScript compiler",
            )
        )
    return findings


def run_checks() -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(_check_root_files())
    findings.extend(_check_pyproject())
    findings.extend(_check_bundled_binaries())
    findings.extend(_check_notice_mentions_compiler())
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_licenses",
        description="Verify license and notice files.",
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
                    "findings": [
                        {"kind": f.kind, "path": f.path, "detail": f.detail}
                        for f in findings
                    ],
                },
                indent=2,
            )
        )
    elif not args.quiet:
        if not findings:
            print("OK: licenses and notices are consistent")
        else:
            print(f"LICENSE CHECK FAILED: {len(findings)} issue(s)")
            for f in findings:
                print(str(f))

    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())