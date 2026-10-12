#!/usr/bin/env python3
"""Regenerate conformance/expected/ from a run against the pinned compiler.

Conformance cases live under `conformance/cases/`. Each case is a small
TypeScript file or project. The expected output (list of error codes and
positions) lives under `conformance/expected/`, one file per case.

Updating expected output is a deliberate act. This script:

1. Reads every case in `conformance/cases/`.
2. Runs the bundled tsgo against it (via pytscheck).
3. Writes the normalized diagnostic list to `conformance/expected/`.
4. Regenerates `conformance/manifest.json`.

By default it writes to a staging directory and requires `--apply` to
overwrite the real expected/ tree. That way a developer can diff the
proposed changes before committing them.

Exit codes:

    0  success (or no changes in --check mode)
    1  drift detected in --check mode, or a case failed to run
    2  usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFORMANCE = REPO_ROOT / "conformance"
CASES_DIR = CONFORMANCE / "cases"
EXPECTED_DIR = CONFORMANCE / "expected"
MANIFEST_PATH = CONFORMANCE / "manifest.json"
STAGING_DIR = CONFORMANCE / ".staging"

sys.path.insert(0, str(REPO_ROOT / "src"))


# ---------------------------------------------------------------------------
# Case model
# ---------------------------------------------------------------------------


@dataclass
class Case:
    name: str
    """Relative path of the case file, e.g. 'assignability/basic.ts'."""

    source_path: Path
    expected_path: Path

    @property
    def category(self) -> str:
        return Path(self.name).parts[0] if "/" in self.name else "root"


def discover_cases() -> list[Case]:
    if not CASES_DIR.exists():
        return []
    cases: list[Case] = []
    for src in sorted(CASES_DIR.rglob("*.ts")):
        rel = src.relative_to(CASES_DIR).as_posix()
        expected = (EXPECTED_DIR / rel).with_suffix(".json")
        cases.append(Case(name=rel, source_path=src, expected_path=expected))
    for src in sorted(CASES_DIR.rglob("tsconfig.json")):
        # Project cases: the case is the directory, the file is tsconfig.json
        rel_dir = src.parent.relative_to(CASES_DIR).as_posix()
        expected = (EXPECTED_DIR / rel_dir).with_suffix(".json")
        cases.append(
            Case(
                name=f"{rel_dir}/",  # trailing slash marks a project case
                source_path=src,
                expected_path=expected,
            )
        )
    return cases


# ---------------------------------------------------------------------------
# Run a case
# ---------------------------------------------------------------------------


def _run_case(case: Case) -> dict:
    """Run one case through pytscheck and return its normalized diagnostics."""
    from pytscheck import check_file, check_project

    if case.name.endswith("/"):
        result = check_project(case.source_path.parent, keep_raw=True)
    else:
        result = check_file(case.source_path, keep_raw=True)

    diags = [
        {
            "file": _relpath(d.file),
            "line": d.line,
            "column": d.column,
            "code": d.code,
            "category": d.category,
            "message": d.message,
        }
        for d in result.diagnostics
    ]
    return {
        "case": case.name,
        "success": result.success,
        "diagnostics": diags,
    }


def _relpath(file: str | None) -> str | None:
    """Normalize diagnostic file paths to be relative to the case dir."""
    if file is None:
        return None
    p = Path(file)
    try:
        return p.resolve().relative_to(CASES_DIR.resolve()).as_posix()
    except (ValueError, OSError):
        return p.name


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def _build_manifest(cases: list[Case]) -> dict:
    categories: dict[str, int] = {}
    for c in cases:
        categories[c.category] = categories.get(c.category, 0) + 1
    return {
        "version": 1,
        "case_count": len(cases),
        "categories": dict(sorted(categories.items())),
        "cases": [c.name for c in cases],
    }


# ---------------------------------------------------------------------------
# Write expected output
# ---------------------------------------------------------------------------


def _dump_expected(case: Case, payload: dict, outdir: Path) -> Path:
    rel = case.name.rstrip("/")
    out_path = (outdir / rel).with_suffix(".json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path


def _diff_expected(case: Case, new_payload: dict) -> str | None:
    """Return a summary of differences, or None if identical."""
    if not case.expected_path.exists():
        return "new case"
    old = json.loads(case.expected_path.read_text(encoding="utf-8"))
    if old == new_payload:
        return None

    old_codes = sorted((d.get("line"), d.get("code")) for d in old.get("diagnostics", []))
    new_codes = sorted((d.get("line"), d.get("code")) for d in new_payload.get("diagnostics", []))
    if old_codes == new_codes:
        return "diagnostics differ in message/file only"
    return f"diagnostics changed: {old_codes} -> {new_codes}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="update_conformance",
        description="Regenerate conformance/expected/ from the pinned compiler.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="overwrite conformance/expected/ (default: stage only)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify expected/ matches; exit 1 on drift",
    )
    parser.add_argument(
        "--case",
        action="append",
        metavar="NAME",
        help="update only the named case(s); may be repeated",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    cases = discover_cases()
    if not cases:
        print("no cases found under conformance/cases/", file=sys.stderr)
        if args.check:
            return 0  # nothing to check; not a failure
        return 1

    if args.case:
        wanted = set(args.case)
        cases = [c for c in cases if c.name in wanted or c.name.rstrip("/") in wanted]
        if not cases:
            print(f"no matching cases for {sorted(wanted)}", file=sys.stderr)
            return 2

    try:
        import pytscheck  # noqa: F401
    except ImportError:
        print(
            "pytscheck is not importable; pip install -e . before running",
            file=sys.stderr,
        )
        return 2

    results: list[dict] = []
    failures: list[str] = []

    outdir = EXPECTED_DIR if args.apply else STAGING_DIR
    outdir.mkdir(parents=True, exist_ok=True)

    for case in cases:
        try:
            payload = _run_case(case)
        except Exception as exc:
            failures.append(f"{case.name}: {exc}")
            continue

        diff = _diff_expected(case, payload)
        results.append(
            {
                "case": case.name,
                "changed": diff is not None,
                "diff": diff or "",
                "success": payload["success"],
                "diagnostic_count": len(payload["diagnostics"]),
            }
        )

        if args.check:
            continue

        _dump_expected(case, payload, outdir)

    if args.check:
        changed = [r for r in results if r["changed"]]
        if args.json:
            print(json.dumps({"changed": changed, "failures": failures}, indent=2))
        else:
            if not changed and not failures:
                print(f"OK: {len(cases)} cases match expected/")
                return 0
            for r in changed:
                print(f"DRIFT {r['case']}: {r['diff']}")
            for f in failures:
                print(f"ERROR {f}")
        return 1 if (changed or failures) else 0

    # The declarative case generator owns manifest.json. Updating outputs must
    # not replace that catalog with a different schema (or a filtered subset).

    if args.json:
        print(
            json.dumps(
                {
                    "outdir": str(outdir.relative_to(REPO_ROOT)),
                    "case_count": len(cases),
                    "changed": [r for r in results if r["changed"]],
                    "failures": failures,
                },
                indent=2,
            )
        )
        return 1 if failures else 0

    print(f"updated {len(cases)} case(s) into {outdir.relative_to(REPO_ROOT)}")
    changed = [r for r in results if r["changed"]]
    if changed:
        print(f"  {len(changed)} changed:")
        for r in changed:
            print(f"    {r['case']}: {r['diff']}")
    if failures:
        print(f"  {len(failures)} failed to run:")
        for f in failures:
            print(f"    {f}")

    if not args.apply:
        print()
        print("staged only. run with --apply to overwrite conformance/expected/")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
