"""Run the compiler conformance suite.

Reads conformance/cases/ and conformance/expected/, runs the bundled
tsgo compiler on every case via pytscheck, and compares the diagnostics
against the expected output.

This script NEVER writes. To regenerate expected output, use
scripts/update_conformance.py.

Exit codes:

    0  every case matched
    1  one or more cases differed, failed to run, or had no expected output
    2  usage error
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFORMANCE = REPO_ROOT / "conformance"
CASES_DIR = CONFORMANCE / "cases"
EXPECTED_DIR = CONFORMANCE / "expected"
MANIFEST_PATH = CONFORMANCE / "manifest.json"

sys.path.insert(0, str(REPO_ROOT / "src"))


# ---------------------------------------------------------------------------
# Case model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Case:
    name: str
    """Relative path, e.g. 'assignability/basic.ts', or 'projects/foo/'."""

    source_path: Path
    expected_path: Path

    @property
    def category(self) -> str:
        parts = Path(self.name.rstrip("/")).parts
        return parts[0] if len(parts) > 1 else "root"

    @property
    def is_project(self) -> bool:
        return self.name.endswith("/")


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


@dataclass
class CaseResult:
    case: Case
    status: str
    """One of: 'pass', 'fail', 'error', 'missing-expected'."""

    expected: dict | None = None
    actual: dict | None = None
    message: str = ""
    elapsed: float = 0.0

    @property
    def ok(self) -> bool:
        return self.status == "pass"


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_cases() -> list[Case]:
    """Walk cases/ and return one Case per .ts file or per project directory."""
    if not CASES_DIR.exists():
        return []

    cases: list[Case] = []

    # Individual .ts files
    for src in sorted(CASES_DIR.rglob("*.ts")):
        if src.name == "tsconfig.json":
            continue
        rel = src.relative_to(CASES_DIR).as_posix()
        expected = (EXPECTED_DIR / rel).with_suffix(".json")
        cases.append(Case(name=rel, source_path=src, expected_path=expected))

    # Project directories (identified by a tsconfig.json inside them)
    seen_dirs: set[Path] = set()
    for tsconfig in sorted(CASES_DIR.rglob("tsconfig.json")):
        d = tsconfig.parent
        if d in seen_dirs:
            continue
        seen_dirs.add(d)
        # Skip if this directory has no .ts files under it
        if not any(d.rglob("*.ts")):
            continue
        rel = d.relative_to(CASES_DIR).as_posix() + "/"
        expected = (EXPECTED_DIR / rel.rstrip("/")).with_suffix(".json")
        cases.append(Case(name=rel, source_path=tsconfig, expected_path=expected))

    return cases


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _relpath(file: str | None) -> str | None:
    """Normalize a diagnostic file path to be relative to cases/."""
    if file is None:
        return None
    p = Path(file)
    try:
        return p.resolve().relative_to(CASES_DIR.resolve()).as_posix()
    except (ValueError, OSError):
        # Diagnostic file was a temp path or an absolute path we cannot
        # relativize; fall back to the basename.
        return p.name


def _normalize_diagnostics(diagnostics: list) -> list[dict]:
    """Convert Diagnostic objects to a canonical dict form for comparison."""
    out: list[dict] = []
    for d in diagnostics:
        out.append(
            {
                "file": _relpath(d.file),
                "line": d.line,
                "column": d.column,
                "code": d.code,
                "category": d.category,
                "message": d.message,
            }
        )
    return out


def _normalize_expected(payload: dict) -> list[dict]:
    """Extract the diagnostics from an expected .json into canonical form."""
    diags = payload.get("diagnostics", [])
    out: list[dict] = []
    for d in diags:
        out.append(
            {
                "file": d.get("file"),
                "line": d.get("line"),
                "column": d.get("column"),
                "code": d.get("code"),
                "category": d.get("category"),
                "message": d.get("message"),
            }
        )
    return out


def _diff_diagnostics(expected: list[dict], actual: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (missing, extra) diagnostics as multiset differences.

    Compare as multisets so ordering differences do not cause failures.
    """
    from collections import Counter

    def key(d: dict) -> tuple:
        return (
            d.get("file"),
            d.get("line"),
            d.get("column"),
            d.get("code"),
            d.get("category"),
            d.get("message"),
        )

    exp_counter = Counter(key(d) for d in expected)
    act_counter = Counter(key(d) for d in actual)

    missing: list[dict] = []
    for k, count in exp_counter.items():
        if act_counter.get(k, 0) < count:
            # Find one example of this diagnostic in expected
            for d in expected:
                if key(d) == k:
                    missing.append(d)
                    break

    extra: list[dict] = []
    for k, count in act_counter.items():
        if exp_counter.get(k, 0) < count:
            for d in actual:
                if key(d) == k:
                    extra.append(d)
                    break

    return missing, extra


# ---------------------------------------------------------------------------
# Running a case
# ---------------------------------------------------------------------------


def run_case(case: Case) -> CaseResult:
    """Run one case and compare its output to the expected .json."""
    start = time.monotonic()

    if not case.expected_path.exists():
        return CaseResult(
            case=case,
            status="missing-expected",
            message=(
                f"no expected output at {case.expected_path.relative_to(REPO_ROOT)}; "
                f"run scripts/update_conformance.py --case {case.name.rstrip('/')} --apply"
            ),
            elapsed=time.monotonic() - start,
        )

    try:
        expected_payload = json.loads(case.expected_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return CaseResult(
            case=case,
            status="error",
            message=f"invalid expected JSON: {exc}",
            elapsed=time.monotonic() - start,
        )

    try:
        from pytscheck import check_file, check_project

        if case.is_project:
            result = check_project(case.source_path.parent)
        else:
            result = check_file(case.source_path)
    except Exception as exc:
        return CaseResult(
            case=case,
            status="error",
            message=f"check failed: {type(exc).__name__}: {exc}",
            expected=expected_payload,
            elapsed=time.monotonic() - start,
        )

    actual_payload = {
        "case": case.name,
        "success": result.success,
        "diagnostics": _normalize_diagnostics(list(result.diagnostics)),
    }

    expected_diags = _normalize_expected(expected_payload)
    actual_diags = _normalize_expected(actual_payload)

    # Success flag check
    if expected_payload.get("success") != actual_payload["success"]:
        return CaseResult(
            case=case,
            status="fail",
            expected=expected_payload,
            actual=actual_payload,
            message=(
                f"success differs: expected "
                f"{expected_payload.get('success')}, got {actual_payload['success']}"
            ),
            elapsed=time.monotonic() - start,
        )

    missing, extra = _diff_diagnostics(expected_diags, actual_diags)
    if missing or extra:
        parts: list[str] = []
        if missing:
            parts.append(f"{len(missing)} missing")
        if extra:
            parts.append(f"{len(extra)} extra")
        return CaseResult(
            case=case,
            status="fail",
            expected=expected_payload,
            actual=actual_payload,
            message=", ".join(parts),
            elapsed=time.monotonic() - start,
        )

    return CaseResult(
        case=case,
        status="pass",
        expected=expected_payload,
        actual=actual_payload,
        elapsed=time.monotonic() - start,
    )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _print_diagnostic(d: dict) -> str:
    loc = f"{d.get('file')}({d.get('line')},{d.get('column')})"
    return f"    {loc}: {d.get('category')} TS{d.get('code')}: {d.get('message')}"


def _print_case_result(r: CaseResult, *, verbose: bool) -> None:
    if r.ok:
        if verbose:
            print(f"PASS  {r.case.name} ({r.elapsed:.2f}s)")
        return

    print(f"FAIL  {r.case.name}")
    if r.message:
        print(f"  {r.message}")

    if r.status == "missing-expected":
        return

    if r.expected is not None and r.actual is not None:
        expected_diags = _normalize_expected(r.expected)
        actual_diags = _normalize_expected(r.actual)
        missing, extra = _diff_diagnostics(expected_diags, actual_diags)

        if missing:
            print("  missing diagnostics (expected but not produced):")
            for d in missing:
                print(_print_diagnostic(d))
        if extra:
            print("  extra diagnostics (produced but not expected):")
            for d in extra:
                print(_print_diagnostic(d))


def _summary(results: list[CaseResult]) -> dict:
    by_status: dict[str, int] = {}
    for r in results:
        by_status[r.status] = by_status.get(r.status, 0) + 1

    by_category: dict[str, dict[str, int]] = {}
    for r in results:
        cat = r.case.category
        by_category.setdefault(cat, {"pass": 0, "fail": 0})
        if r.ok:
            by_category[cat]["pass"] += 1
        else:
            by_category[cat]["fail"] += 1

    return {
        "total": len(results),
        "passed": by_status.get("pass", 0),
        "failed": by_status.get("fail", 0),
        "errors": by_status.get("error", 0),
        "missing_expected": by_status.get("missing-expected", 0),
        "by_category": dict(sorted(by_category.items())),
    }


def _print_summary(results: list[CaseResult]) -> None:
    s = _summary(results)
    print()
    print("Summary:")
    print(f"  total:            {s['total']}")
    print(f"  passed:           {s['passed']}")
    print(f"  failed:           {s['failed']}")
    print(f"  errors:           {s['errors']}")
    print(f"  missing expected: {s['missing_expected']}")
    if s["by_category"]:
        print()
        print("  By category:")
        width = max(len(c) for c in s["by_category"])
        for cat, counts in s["by_category"].items():
            print(f"    {cat:<{width}}  pass={counts['pass']:<4}  fail={counts['fail']}")


def _to_json(results: list[CaseResult]) -> dict:
    return {
        "summary": _summary(results),
        "cases": [
            {
                "name": r.case.name,
                "category": r.case.category,
                "status": r.status,
                "message": r.message,
                "elapsed": r.elapsed,
            }
            for r in results
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="conformance",
        description="Run the compiler conformance suite.",
    )
    parser.add_argument(
        "--category",
        action="append",
        metavar="NAME",
        help="run only cases in the given category (may be repeated)",
    )
    parser.add_argument(
        "--case",
        action="append",
        metavar="NAME",
        help="run only the named case(s) (may be repeated)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="(compatibility flag; run.py never writes)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print PASS lines for every case",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a machine-readable report",
    )
    args = parser.parse_args(argv)

    # Import pytscheck lazily so we can produce a clean error if it's absent.
    try:
        import pytscheck  # noqa: F401
    except ImportError as exc:
        print(
            f"error: pytscheck is not importable: {exc}\n"
            f"install with `pip install -e .` before running conformance.",
            file=sys.stderr,
        )
        return 2

    cases = discover_cases()
    if not cases:
        print(
            "no cases found under conformance/cases/\n"
            "run scripts/generate_conformance_cases.py --manifest first.",
            file=sys.stderr,
        )
        return 1

    if args.category:
        wanted = set(args.category)
        cases = [c for c in cases if c.category in wanted]
        if not cases:
            print(
                f"no cases matched categories: {sorted(wanted)}",
                file=sys.stderr,
            )
            return 2

    if args.case:
        wanted = set(args.case)
        cases = [c for c in cases if c.name in wanted or c.name.rstrip("/") in wanted]
        if not cases:
            print(
                f"no cases matched: {sorted(wanted)}",
                file=sys.stderr,
            )
            return 2

    # Announce what we're about to do
    if not args.json:
        print(f"Running {len(cases)} conformance case(s)...")
        print()

    results: list[CaseResult] = []
    for case in cases:
        result = run_case(case)
        results.append(result)
        if not args.json:
            _print_case_result(result, verbose=args.verbose)

    if args.json:
        print(json.dumps(_to_json(results), indent=2))
    else:
        _print_summary(results)

    failed = [r for r in results if not r.ok]
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
