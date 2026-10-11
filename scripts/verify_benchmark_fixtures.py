#!/usr/bin/env python3
"""Verify benchmarks/fixtures/ matches generate_benchmark_fixtures.py.

Exit codes:
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
FIXTURES_ROOT = REPO_ROOT / "benchmarks" / "fixtures"
MANIFEST_PATH = FIXTURES_ROOT / "MANIFEST.json"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
try:
    from generate_benchmark_fixtures import (  # type: ignore[import-not-found]
        all_fixtures,
        build_manifest,
    )
except ImportError as exc:
    print(f"error: cannot import generate_benchmark_fixtures: {exc}",
          file=sys.stderr)
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
    return {f.relpath: f.content for f in all_fixtures()}


def check_files(report: Report) -> None:
    spec = _spec()
    for relpath, expected in spec.items():
        report.checked += 1
        p = FIXTURES_ROOT / relpath
        if not p.exists():
            report.drifts.append(
                Drift("missing", relpath,
                      "run scripts/generate_benchmark_fixtures.py --manifest")
            )
        elif p.read_text(encoding="utf-8") != expected:
            report.drifts.append(
                Drift("modified", relpath,
                      "content differs from generator spec")
            )


def check_unexpected(report: Report) -> None:
    spec = _spec()
    allowed = {"MANIFEST.json", "README.md"}
    if not FIXTURES_ROOT.exists():
        return
    files = [p for p in FIXTURES_ROOT.rglob("*") if p.is_file()]
    report.on_disk_total = len(files)
    for p in files:
        rel = p.relative_to(FIXTURES_ROOT).as_posix()
        if rel in spec or rel in allowed:
            continue
        report.drifts.append(
            Drift("unexpected", rel, "not declared by the generator")
        )


def check_manifest(report: Report) -> None:
    if not MANIFEST_PATH.exists():
        report.drifts.append(
            Drift("manifest_missing", "MANIFEST.json",
                  "run scripts/generate_benchmark_fixtures.py --manifest")
        )
        return
    try:
        actual = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.drifts.append(
            Drift("manifest_mismatch", "MANIFEST.json", f"invalid JSON: {exc}")
        )
        return
    expected = build_manifest()
    if actual.get("fixture_count") != expected["fixture_count"]:
        report.drifts.append(
            Drift(
                "manifest_mismatch",
                "MANIFEST.json",
                f"fixture_count={actual.get('fixture_count')} "
                f"expected {expected['fixture_count']}",
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify_benchmark_fixtures",
        description="Drift check for benchmarks/fixtures/.",
    )
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = Report()
    check_files(report)
    check_unexpected(report)
    check_manifest(report)

    if args.json:
        print(json.dumps({
            "clean": report.clean,
            "checked": report.checked,
            "on_disk_total": report.on_disk_total,
            "drift_count": len(report.drifts),
            "drifts": [
                {"kind": d.kind, "path": d.path, "detail": d.detail}
                for d in report.drifts
            ],
        }, indent=2))
    elif not args.quiet:
        if report.clean:
            print(
                f"OK: {report.checked} benchmark fixtures verified "
                f"({report.on_disk_total} files on disk)"
            )
        else:
            print(f"DRIFT DETECTED: {len(report.drifts)} issue(s)")
            print()
            for d in report.drifts:
                print(str(d))

    return 0 if report.clean else 1


if __name__ == "__main__":
    raise SystemExit(main())