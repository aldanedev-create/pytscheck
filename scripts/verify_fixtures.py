#!/usr/bin/env python3
"""Verify that tests/fixtures/ matches scripts/generate_fixtures.py.

This is the drift check for the fixture suite. It answers three questions:

1. Are all fixtures declared in the generator present on disk?
2. Do any on-disk fixtures differ from what the generator would produce?
3. Is MANIFEST.json consistent with both?

Exit codes:

    0  clean -- fixtures match the spec
    1  drift detected -- report which files differ
    2  usage error

The script never writes to disk. It only reports.

Usage:

    python scripts/verify_fixtures.py             # verify
    python scripts/verify_fixtures.py --quiet     # exit code only
    python scripts/verify_fixtures.py --json      # machine-readable report
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures"
MANIFEST_PATH = FIXTURES_ROOT / "MANIFEST.json"

# Import the generator's spec. This is safe: generate_fixtures.py does not
# write to disk at import time, and its main() is guarded by __main__.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
try:
    from generate_fixtures import (
        all_fixtures,
        build_manifest,
    )
except ImportError as exc:  # pragma: no cover - defensive
    print(f"error: cannot import generate_fixtures: {exc}", file=sys.stderr)
    raise SystemExit(2) from exc


# ---------------------------------------------------------------------------
# Report model
# ---------------------------------------------------------------------------


@dataclass
class Drift:
    """One discrepancy between the spec and the on-disk fixtures."""

    kind: str
    """'missing', 'modified', 'unexpected', 'manifest_missing',
    'manifest_mismatch', or 'manifest_extra'."""

    path: str
    """Path relative to tests/fixtures/."""

    detail: str = ""

    def __str__(self) -> str:
        if self.detail:
            return f"{self.kind:18s} {self.path}\n  {self.detail}"
        return f"{self.kind:18s} {self.path}"


@dataclass
class Report:
    drifts: list[Drift] = field(default_factory=list)
    checked: int = 0
    expected_total: int = 0
    on_disk_total: int = 0
    manifest_present: bool = False

    @property
    def clean(self) -> bool:
        return not self.drifts

    def to_json(self) -> dict:
        return {
            "clean": self.clean,
            "checked": self.checked,
            "expected_total": self.expected_total,
            "on_disk_total": self.on_disk_total,
            "manifest_present": self.manifest_present,
            "drift_count": len(self.drifts),
            "drifts": [{"kind": d.kind, "path": d.path, "detail": d.detail} for d in self.drifts],
        }


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def _iter_spec_fixtures() -> dict[str, str]:
    """Return {relpath: expected content} for every generated fixture."""
    return {f.relpath: f.content for f in all_fixtures()}


def _iter_generated_paths() -> set[str]:
    """Return the set of relpaths the generator claims ownership of."""
    return {f.relpath for f in all_fixtures() if f.generated}


def _iter_manifest_paths(manifest: dict) -> set[str]:
    return {entry["path"] for entry in manifest.get("fixtures", [])}


def _read_on_disk(relpath: str) -> str | None:
    p = FIXTURES_ROOT / relpath
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "<binary>"


def check_fixture_files(report: Report) -> None:
    """Compare every generator-declared fixture against the on-disk file."""
    spec = _iter_spec_fixtures()
    report.expected_total = len(spec)

    for relpath, expected_content in spec.items():
        report.checked += 1
        on_disk = _read_on_disk(relpath)
        if on_disk is None:
            report.drifts.append(
                Drift(
                    kind="missing",
                    path=relpath,
                    detail="declared by generator but not present on disk; "
                    "run scripts/generate_fixtures.py",
                )
            )
            continue
        if on_disk != expected_content:
            report.drifts.append(
                Drift(
                    kind="modified",
                    path=relpath,
                    detail=_diff_summary(expected_content, on_disk),
                )
            )


def check_for_unexpected_files(report: Report) -> None:
    """Warn about files under tests/fixtures/ not declared by the generator.

    Files under directories the generator owns are flagged as unexpected.
    Hand-authored files (those marked generated=False in the manifest or
    under known hand-authored paths) are allowed.
    """
    spec = _iter_spec_fixtures()
    spec_dirs = {Path(p).parent.as_posix() for p in spec}
    allowed_hand_authored = {"README.md", "MANIFEST.json"}

    on_disk: list[str] = []
    if not FIXTURES_ROOT.exists():
        return
    for p in FIXTURES_ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(FIXTURES_ROOT).as_posix()
        on_disk.append(rel)

    report.on_disk_total = len(on_disk)

    for rel in on_disk:
        if rel in spec:
            continue
        if rel in allowed_hand_authored:
            continue
        # Allow files under directories the generator owns only if they
        # are marked hand-authored in the spec.
        parent = Path(rel).parent.as_posix()
        if parent in spec_dirs or any(rel.startswith(d + "/") for d in spec_dirs):
            # It's a file in a directory we generate but not in the spec.
            report.drifts.append(
                Drift(
                    kind="unexpected",
                    path=rel,
                    detail="file present but not declared by the generator; "
                    "either add it to generate_fixtures.py or move it out "
                    "of a generated directory",
                )
            )


def check_manifest(report: Report, *, strict: bool) -> None:
    """Verify MANIFEST.json is present and consistent with the spec."""
    if not MANIFEST_PATH.exists():
        report.manifest_present = False
        report.drifts.append(
            Drift(
                kind="manifest_missing",
                path="MANIFEST.json",
                detail="run scripts/generate_fixtures.py --manifest",
            )
        )
        return

    report.manifest_present = True
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.drifts.append(
            Drift(
                kind="manifest_mismatch",
                path="MANIFEST.json",
                detail=f"invalid JSON: {exc}",
            )
        )
        return

    expected = build_manifest()
    expected_paths = _iter_manifest_paths(expected)
    actual_paths = _iter_manifest_paths(manifest)

    if expected_paths - actual_paths:
        for rel in sorted(expected_paths - actual_paths):
            report.drifts.append(
                Drift(
                    kind="manifest_mismatch",
                    path=rel,
                    detail="declared in spec but missing from MANIFEST.json",
                )
            )

    if actual_paths - expected_paths:
        for rel in sorted(actual_paths - expected_paths):
            report.drifts.append(
                Drift(
                    kind="manifest_extra",
                    path=rel,
                    detail="present in MANIFEST.json but not declared in spec",
                )
            )

    # Compare metadata for shared paths
    expected_by_path = {e["path"]: e for e in expected["fixtures"]}
    actual_by_path = {e["path"]: e for e in manifest.get("fixtures", [])}
    for rel in sorted(set(expected_by_path) & set(actual_by_path)):
        if strict and expected_by_path[rel] != actual_by_path[rel]:
            report.drifts.append(
                Drift(
                    kind="manifest_mismatch",
                    path=rel,
                    detail="metadata in MANIFEST.json differs from spec",
                )
            )

    if manifest.get("fixture_count") != len(actual_paths):
        report.drifts.append(
            Drift(
                kind="manifest_mismatch",
                path="MANIFEST.json",
                detail=(
                    f"fixture_count={manifest.get('fixture_count')} "
                    f"but {len(actual_paths)} entries found"
                ),
            )
        )


def _diff_summary(expected: str, actual: str) -> str:
    """Return a short human-readable summary of how the two strings differ."""
    exp_lines = expected.splitlines()
    act_lines = actual.splitlines()
    if len(exp_lines) != len(act_lines):
        return (
            f"line count differs: expected {len(exp_lines)}, "
            f"actual {len(act_lines)}; run scripts/generate_fixtures.py"
        )
    for i, (e, a) in enumerate(zip(exp_lines, act_lines, strict=False), start=1):
        if e != a:
            return f"first difference at line {i}: expected {e!r}, actual {a!r}"
    # Same lines, different bytes (trailing newline)
    if expected != actual:
        return "content differs (trailing bytes); run scripts/generate_fixtures.py"
    return "content differs"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def verify(*, strict: bool = False) -> Report:
    report = Report()
    if not FIXTURES_ROOT.exists():
        report.drifts.append(
            Drift(
                kind="manifest_missing",
                path="tests/fixtures/",
                detail="fixtures directory does not exist; "
                "run scripts/generate_fixtures.py --manifest",
            )
        )
        return report

    check_fixture_files(report)
    check_for_unexpected_files(report)
    check_manifest(report, strict=strict)
    return report


def _print_human(report: Report) -> None:
    if report.clean:
        print(f"OK: {report.checked} fixtures verified ({report.on_disk_total} files on disk)")
        return

    print(f"DRIFT DETECTED: {len(report.drifts)} issue(s)")
    print()
    for d in report.drifts:
        print(str(d))
    print()
    print("Run `python scripts/generate_fixtures.py --manifest` to fix generated-file drift.")
    print(
        "Hand-authored files must be added to scripts/generate_fixtures.py "
        "or moved out of generated directories."
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_fixtures",
        description="Verify tests/fixtures/ matches generate_fixtures.py.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print nothing; use exit code only",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a machine-readable JSON report",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="compare manifest metadata exactly, not just paths",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = verify(strict=args.strict)

    if args.json:
        print(json.dumps(report.to_json(), indent=2))
    elif not args.quiet:
        _print_human(report)

    return 0 if report.clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
