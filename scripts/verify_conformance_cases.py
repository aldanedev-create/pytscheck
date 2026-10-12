#!/usr/bin/env python3
"""Verify conformance/cases/ matches generate_conformance_cases.py.

Runs in CI as a drift check. Same shape as verify_fixtures.py:

    0  clean
    1  drift
    2  usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_ROOT = REPO_ROOT / "conformance" / "cases"
MANIFEST_PATH = REPO_ROOT / "conformance" / "manifest.json"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
try:
    from generate_conformance_cases import (  # type: ignore[import-not-found]
        all_cases,
        build_manifest,
    )
except ImportError as exc:
    print(f"error: cannot import generate_conformance_cases: {exc}", file=sys.stderr)
    raise SystemExit(2) from exc


@dataclass
class Drift:
    kind: str
    path: str
    detail: str = ""

    def __str__(self) -> str:
        if self.detail:
            return f"{self.kind:18s} {self.path}\n  {self.detail}"
        return f"{self.kind:18s} {self.path}"


@dataclass
class Report:
    drifts: list[Drift] = field(default_factory=list)
    checked: int = 0
    on_disk_total: int = 0

    @property
    def clean(self) -> bool:
        return not self.drifts


def _spec() -> dict[str, str]:
    return {c.relpath: c.content for c in all_cases()}


def _read(relpath: str) -> str | None:
    p = CASES_ROOT / relpath
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")


def check_files(report: Report) -> None:
    spec = _spec()
    for relpath, expected in spec.items():
        report.checked += 1
        actual = _read(relpath)
        if actual is None:
            report.drifts.append(
                Drift(
                    "missing",
                    relpath,
                    "declared by generator but not on disk; run "
                    "scripts/generate_conformance_cases.py --manifest",
                )
            )
        elif actual != expected:
            report.drifts.append(
                Drift(
                    "modified",
                    relpath,
                    "content differs from generator spec",
                )
            )


def check_unexpected(report: Report) -> None:
    spec = _spec()
    allowed_hand_authored = {"README.md"}
    if not CASES_ROOT.exists():
        return
    files = [p for p in CASES_ROOT.rglob("*") if p.is_file()]
    report.on_disk_total = len(files)
    for p in files:
        rel = p.relative_to(CASES_ROOT).as_posix()
        if rel in spec or rel in allowed_hand_authored:
            continue
        report.drifts.append(
            Drift(
                "unexpected",
                rel,
                "not declared by the generator",
            )
        )


def check_manifest(report: Report) -> None:
    if not MANIFEST_PATH.exists():
        report.drifts.append(
            Drift(
                "manifest_missing",
                "manifest.json",
                "run scripts/generate_conformance_cases.py --manifest",
            )
        )
        return
    try:
        actual = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.drifts.append(Drift("manifest_mismatch", "manifest.json", f"invalid JSON: {exc}"))
        return
    expected = build_manifest()
    if actual.get("case_count") != expected["case_count"]:
        report.drifts.append(
            Drift(
                "manifest_mismatch",
                "manifest.json",
                f"case_count={actual.get('case_count')} expected {expected['case_count']}",
            )
        )
    actual_paths = {c["path"] for c in actual.get("cases", [])}
    expected_paths = {c["path"] for c in expected["cases"]}
    for rel in sorted(expected_paths - actual_paths):
        report.drifts.append(Drift("manifest_mismatch", rel, "missing from manifest"))
    for rel in sorted(actual_paths - expected_paths):
        report.drifts.append(Drift("manifest_extra", rel, "present in manifest but not in spec"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify_conformance_cases",
        description="Drift check for conformance/cases/.",
    )
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = Report()
    check_files(report)
    check_unexpected(report)
    check_manifest(report)

    if args.json:
        print(
            json.dumps(
                {
                    "clean": report.clean,
                    "checked": report.checked,
                    "on_disk_total": report.on_disk_total,
                    "drift_count": len(report.drifts),
                    "drifts": [
                        {"kind": d.kind, "path": d.path, "detail": d.detail} for d in report.drifts
                    ],
                },
                indent=2,
            )
        )
    elif not args.quiet:
        if report.clean:
            print(
                f"OK: {report.checked} conformance cases verified "
                f"({report.on_disk_total} files on disk)"
            )
        else:
            print(f"DRIFT DETECTED: {len(report.drifts)} issue(s)")
            print()
            for d in report.drifts:
                print(str(d))
            print()
            print("Run `python scripts/generate_conformance_cases.py --manifest` to fix.")

    return 0 if report.clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
