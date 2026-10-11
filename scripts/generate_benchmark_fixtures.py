#!/usr/bin/env python3
"""Generate benchmarks/fixtures/ from a declarative spec.

Produces TypeScript files of known, stable size so benchmarks have
consistent inputs across runs. Same pattern as generate_fixtures.py and
generate_conformance_cases.py:

- declarative spec
- idempotent output
- committed to git
- companion verifier detects drift

Usage:

    python scripts/generate_benchmark_fixtures.py --dry-run
    python scripts/generate_benchmark_fixtures.py --manifest
    python scripts/generate_benchmark_fixtures.py --force --manifest
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_ROOT = REPO_ROOT / "benchmarks" / "fixtures"
MANIFEST_PATH = FIXTURES_ROOT / "MANIFEST.json"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Fixture:
    relpath: str
    content: str
    description: str = ""
    generated: bool = True


@dataclass
class FixtureSet:
    name: str
    fixtures: list[Fixture] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


def _header(description: str) -> str:
    return f"// benchmark fixture: {description}\n\n"


def generate_tiny() -> str:
    """A ~10-line, 300-byte valid TypeScript file."""
    return _header("tiny: single small file, no errors") + (
        "export const a: number = 1;\n"
        "export const b: string = 'x';\n"
        "export const c: boolean = true;\n"
        "export function add(x: number, y: number): number {\n"
        "  return x + y;\n"
        "}\n"
        "export interface P { x: number; y: number; }\n"
        "export const p: P = { x: 1, y: 2 };\n"
        "export type Pair = readonly [number, string];\n"
        "export const pair: Pair = [1, 'a'] as const;\n"
    )


def generate_medium(n_decls: int = 1_000) -> str:
    """A ~1,000-declaration, ~40 KB valid file."""
    lines = [_header(f"medium: {n_decls} numeric declarations, no errors")]
    for i in range(n_decls):
        lines.append(f"export const x{i}: number = {i};\n")
    return "".join(lines)


def generate_large_file(n_decls: int = 10_000) -> str:
    """A ~10,000-declaration, ~400 KB valid file."""
    lines = [_header(f"large: {n_decls} numeric declarations, no errors")]
    for i in range(n_decls):
        lines.append(f"export const x{i}: number = {i};\n")
    return "".join(lines)


def generate_error_heavy(n_errors: int = 500) -> str:
    """A file with N guaranteed type errors."""
    lines = [_header(f"errors: {n_errors} type errors")]
    for i in range(n_errors):
        lines.append(f'export const bad{i}: number = "string";\n')
    return "".join(lines)


def generate_mixed(n_ok: int, n_bad: int) -> str:
    """A file mixing valid and invalid declarations."""
    lines = [_header(f"mixed: {n_ok} valid, {n_bad} errors")]
    for i in range(n_ok):
        lines.append(f"export const ok{i}: number = {i};\n")
    for i in range(n_bad):
        lines.append(f'export const bad{i}: number = "s";\n')
    return "".join(lines)


def generate_project_files(n_files: int, decls_per_file: int) -> list[tuple[str, str]]:
    """Return (relpath, content) for a large project."""
    files: list[tuple[str, str]] = []
    files.append(
        (
            "large-project/tsconfig.json",
            '{\n'
            '  "compilerOptions": {\n'
            '    "strict": true,\n'
            '    "noEmit": true,\n'
            '    "target": "es2022",\n'
            '    "module": "esnext"\n'
            "  },\n"
            '  "include": ["**/*.ts"]\n'
            "}\n",
        )
    )
    for i in range(n_files):
        body_lines = [_header(f"project file {i}")]
        for j in range(decls_per_file):
            body_lines.append(f"export const f{i}_x{j}: number = {j};\n")
        files.append((f"large-project/file_{i:03d}.ts", "".join(body_lines)))
    return files


# ---------------------------------------------------------------------------
# Declarations
# ---------------------------------------------------------------------------


def fixtures_standalone() -> list[Fixture]:
    return [
        Fixture(
            relpath="tiny.ts",
            content=generate_tiny(),
            description="~300 bytes, 10 declarations, no errors",
        ),
        Fixture(
            relpath="medium.ts",
            content=generate_medium(1_000),
            description="~40 KB, 1,000 declarations, no errors",
        ),
        Fixture(
            relpath="large.ts",
            content=generate_large_file(10_000),
            description="~400 KB, 10,000 declarations, no errors",
        ),
        Fixture(
            relpath="errors-100.ts",
            content=generate_error_heavy(100),
            description="100 type errors",
        ),
        Fixture(
            relpath="errors-1000.ts",
            content=generate_error_heavy(1_000),
            description="1,000 type errors",
        ),
        Fixture(
            relpath="mixed.ts",
            content=generate_mixed(500, 100),
            description="500 valid + 100 errors",
        ),
    ]


def fixtures_large_project() -> list[Fixture]:
    entries = generate_project_files(n_files=200, decls_per_file=100)
    out: list[Fixture] = []
    for relpath, content in entries:
        if relpath.endswith("tsconfig.json"):
            out.append(
                Fixture(
                    relpath=relpath,
                    content=content,
                    description="tsconfig for the large project benchmark",
                    generated=False,  # hand-authored structure, not sized
                )
            )
        else:
            out.append(
                Fixture(
                    relpath=relpath,
                    content=content,
                    description="100 declarations, no errors",
                )
            )
    return out


FIXTURE_SETS: list[FixtureSet] = [
    FixtureSet("standalone", fixtures_standalone()),
    FixtureSet("large-project", fixtures_large_project()),
]


def all_fixtures() -> Iterable[Fixture]:
    for fs in FIXTURE_SETS:
        for f in fs.fixtures:
            yield f


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def build_manifest() -> dict:
    fixtures = list(all_fixtures())
    entries: list[dict] = []
    total_bytes = 0
    for f in fixtures:
        size = len(f.content.encode("utf-8"))
        total_bytes += size
        entries.append(
            {
                "path": f.relpath,
                "size_bytes": size,
                "description": f.description,
                "generated": f.generated,
            }
        )
    return {
        "generator": "scripts/generate_benchmark_fixtures.py",
        "version": 1,
        "fixture_count": len(entries),
        "total_bytes": total_bytes,
        "fixtures": entries,
    }


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def write_fixture(fixture: Fixture, *, force: bool) -> str:
    path = FIXTURES_ROOT / fixture.relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        current = path.read_text(encoding="utf-8")
        if current == fixture.content:
            return "skipped"
        return "would-update"
    action = "updated" if path.exists() else "created"
    path.write_text(fixture.content, encoding="utf-8")
    return action


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_benchmark_fixtures",
        description="Generate benchmarks/fixtures/ from a declarative spec.",
    )
    parser.add_argument("--force", action="store_true",
                        help="overwrite hand-edited files")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change, write nothing")
    parser.add_argument("--manifest", action="store_true",
                        help="write/update benchmarks/fixtures/MANIFEST.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    counts = {"created": 0, "updated": 0, "skipped": 0, "would-update": 0}
    changes: list[str] = []

    for fixture in all_fixtures():
        if args.dry_run:
            path = FIXTURES_ROOT / fixture.relpath
            if path.exists() and path.read_text(encoding="utf-8") != fixture.content:
                changes.append(f"WOULD UPDATE {fixture.relpath}")
                counts["would-update"] += 1
            elif not path.exists():
                changes.append(f"WOULD CREATE {fixture.relpath}")
                counts["created"] += 1
            else:
                counts["skipped"] += 1
            continue
        action = write_fixture(fixture, force=args.force)
        counts[action] += 1
        if action in {"created", "updated"}:
            changes.append(f"{action.upper():8s} {fixture.relpath}")

    if args.manifest and not args.dry_run:
        manifest = build_manifest()
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        changes.append(f"wrote {MANIFEST_PATH.relative_to(REPO_ROOT)}")

    if args.json:
        print(json.dumps({"changes": changes, "counts": counts}, indent=2))
    else:
        for line in changes:
            print(line)
        print()
        print("Summary:")
        print(f"  created:      {counts['created']}")
        print(f"  updated:      {counts['updated']}")
        print(f"  skipped:      {counts['skipped']}")
        if args.dry_run:
            print(f"  would-update: {counts['would-update']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())