# Compiler Conformance Suite

The conformance suite verifies that PyTSCheck's diagnostics match what the
bundled `tsgo` compiler actually produces. It is the project's primary guard
against silent behavior drift when the compiler version changes.

## Purpose

PyTSCheck does not implement a TypeScript type system. It wraps Microsoft's
native TypeScript compiler (`tsgo`) and translates its output into Python
objects. That means:

- The compiler is the **authority** on TypeScript semantics.
- PyTSCheck's job is to faithfully relay what the compiler says.
- If the compiler's behavior changes between versions, PyTSCheck's output
  changes with it — and we need to know.

The conformance suite is how we know.

## What lives here

```
conformance/
├── README.md            # this file
├── manifest.json        # generated inventory of every case
├── run.py               # the CI runner
├── cases/               # TypeScript inputs (generated, committed)
│   ├── assignability/
│   ├── inference/
│   ├── generics/
│   ├── functions/
│   ├── classes/
│   ├── unions/
│   ├── intersections/
│   ├── narrowing/
│   ├── nullability/
│   ├── modules/
│   ├── declarations/
│   └── compiler-options/
└── expected/            # expected diagnostics (generated, committed)
    ├── assignability/
    │   └── basic.json
    └── ...
```

Three categories of file, three different lifecycles:

| Directory | Who writes it | Committed? | Regenerated when? |
|---|---|---|---|
| `cases/` | `scripts/generate_conformance_cases.py` | Yes | When the spec changes |
| `expected/` | `scripts/update_conformance.py --apply` | Yes | When the compiler pin changes, or when a case is added |
| `manifest.json` | Both scripts | Yes | When either runs |
| `run.py` | Hand-authored | Yes | When the runner's logic changes |
| `README.md` | Hand-authored | Yes | When the docs need updating |

## How a case works

A case is one small TypeScript file (or a directory with a `tsconfig.json`)
that exercises a single language feature. Each case has a matching expected
output — a `.json` file listing the diagnostics the compiler is expected to
produce.

Example — `cases/assignability/literal-mismatch.ts`:

```typescript
// string literal to number: TS2322
export const a: number = "string";
```

Example — `expected/assignability/literal-mismatch.json`:

```json
{
  "case": "assignability/literal-mismatch.ts",
  "description": "string literal to number: TS2322",
  "success": false,
  "diagnostics": [
    {
      "file": "assignability/literal-mismatch.ts",
      "line": 2,
      "column": 7,
      "code": 2322,
      "category": "error",
      "message": "Type 'string' is not assignable to type 'number'."
    }
  ]
}
```

`run.py` reads both, runs the compiler on the `.ts` file, and compares.

## Running the suite

```bash
# Run everything
python conformance/run.py

# Run one category
python conformance/run.py --category narrowing

# Run one case
python conformance/run.py --case assignability/literal-mismatch.ts

# Compare and exit — do not regenerate
python conformance/run.py --check

# Machine-readable output
python conformance/run.py --json
```

Exit codes:

```
0  every case matched its expected output
1  one or more cases differed, failed to run, or had missing expected output
2  usage error
```

The runner **never writes to disk.** Regenerating expected output is the job
of `scripts/update_conformance.py`.

## The three-script workflow

Conformance output passes through three scripts in sequence:

```
                    ┌────────────────────────────────────────────┐
   (1) generate     │ scripts/generate_conformance_cases.py       │
   the inputs       │ writes conformance/cases/**  +  manifest    │
                    └────────────────────┬───────────────────────┘
                                         │
                                         ▼
                                 cases/*.ts committed
                                         │
                                         ▼
                    ┌────────────────────────────────────────────┐
   (2) record       │ scripts/update_conformance.py --apply       │
   what the         │ runs the compiler on every case             │
   compiler says    │ writes conformance/expected/**              │
                    └────────────────────┬───────────────────────┘
                                         │
                                         ▼
                                 expected/*.json committed
                                         │
                                         ▼
                    ┌────────────────────────────────────────────┐
   (3) verify       │ conformance/run.py --check                  │
   in CI            │ runs compiler, compares to expected         │
                    └────────────────────┬───────────────────────┘
                                         │
                                         ▼
                                exit 0 (pass) / 1 (drift)
```

Step 1 runs when the case spec changes.

Step 2 runs when a case is added or the compiler pin is upgraded. Its output
is reviewed in a PR before it's committed.

Step 3 runs in CI on every PR and every release.

## Adding a case

1. Add a `Case(...)` entry to the appropriate `cases_*()` function in
   `scripts/generate_conformance_cases.py`.
2. Run `python scripts/generate_conformance_cases.py --manifest`. This
   creates the `.ts` file and updates `manifest.json`.
3. Run `python scripts/update_conformance.py --apply --case <name>`. This
   runs the compiler and writes the expected output.
4. Review `conformance/expected/<name>.json` — does it match what you
   expect the compiler to say?
5. Commit the `.ts` file, the `.json` file, and `manifest.json`.

## Upgrading the compiler pin

When the pinned `tsgo` version changes, the compiler's behavior may change.
That's expected and the whole point of the suite is to make it visible.

1. Bump `COMPILER_VERSION` in `src/pytscheck/version.py`.
2. Run `python scripts/build_binaries.py <platform>` to fetch the new binary.
3. Run `python scripts/update_conformance.py` (no `--apply`) to stage the new
   expected output.
4. Review the diff under `conformance/.staging/`. Every change is a
   behavioral change in the compiler.
5. Decide case by case: accept it, or file a bug against the compiler.
6. Run `python scripts/update_conformance.py --apply` to write the real
   `expected/` tree.
7. Commit everything. The commit message should name the old and new compiler
   versions and link to any relevant upstream changelog.

This process is documented in detail in `docs/compiler-upgrade.md`.

## What a case tests

Each case exercises **one** language feature, and its expected output
captures **exactly** what the compiler says about it. This means:

- Adding a case is how you document a language feature.
- Removing a case is how you retire a feature that's no longer supported.
- A case whose expected output changes in a PR is a **signal**. Investigate
  before accepting.

We deliberately do not test:

- **Diagnostic message text.** Messages are English strings that can change
  at any time. The suite compares message text because the compiler's exact
  output is the ground truth, but no test *asserts a specific message*. If
  you want to assert a specific code, write a `tests/integration/` test
  instead.
- **Compilation results.** The suite runs in no-emit mode. It never produces
  `.js` files.
- **Performance.** Compiler speed is measured in `benchmarks/`, not here.
- **Alternate compilers.** Only the pinned `tsgo` is tested. We don't claim
  compatibility with `tsc` or any other compiler.

## Why expected output is committed

It's tempting to skip committing `expected/` — just run the compiler fresh
each time and compare nothing. That would be simpler but would defeat the
purpose. Committed expected output gives us:

1. **A baseline.** A diff between the pinned compiler and a candidate compiler
   shows exactly what changed.
2. **Offline visibility.** A contributor without a bundled binary can read
   `expected/*.json` and see what each case should produce.
3. **A review artifact.** A compiler-upgrade PR is reviewable case by case.
   Without committed expected output, the reviewer would have to run the
   compiler themselves to see what changed.

The expected files are **generated by a script, reviewed by a human, and
committed**. They are not build artifacts. They are part of the source tree.

## Relationship to other test suites

| Suite | Purpose | Runs the compiler? |
|---|---|---|
| `tests/unit/` | Contract and invariant tests | No |
| `tests/integration/` | End-to-end behavior | Yes |
| `tests/compatibility/` | Platform + version parity | Yes |
| `tests/security/` | Hostile input handling | Yes |
| `tests/fuzz/` | Random and hostile inputs | Some |
| `tests/adapters/` | Adapter protocol | Some |
| **`conformance/`** | **Feature-by-feature compiler output** | **Yes** |

Conformance is the broadest-coverage, most systematic suite. Where
`tests/integration/` covers realistic usage patterns, conformance covers
specific language features one by one.

## Case categories

The starter set covers twelve categories. Each corresponds to a documented
TypeScript feature area:

| Category | What it covers |
|---|---|
| `assignability/` | Type-compatibility rules |
| `inference/` | Type inference from expressions |
| `generics/` | Type parameters, constraints, defaults |
| `functions/` | Signatures, parameters, return types |
| `classes/` | Inheritance, abstract members, implements |
| `unions/` | Union types, discriminated unions |
| `intersections/` | Intersection types |
| `narrowing/` | typeof, instanceof, control-flow analysis |
| `nullability/` | Optional chaining, nullish coalescing, strict null checks |
| `modules/` | Imports, exports, ambient modules |
| `declarations/` | Ambient declarations, `.d.ts` files |
| `compiler-options/` | Behavior under strict, noImplicitAny, etc. |

Adding a category is one `CaseSet(...)` entry in
`scripts/generate_conformance_cases.py`.

## CI integration

The conformance suite runs in `.github/workflows/compiler-conformance.yml`
on every push and every pull request. Two commands:

```bash
# Verify case files are in sync with the generator
python scripts/verify_conformance_cases.py --quiet

# Run the suite
python conformance/run.py
```

The first fails if a case was hand-edited without updating the generator.
The second fails if any case's output differs from what's expected.

Neither command regenerates anything. If they fail, the fix is to run the
generator and the update script locally, review the diff, and commit.

## Further reading

- `scripts/generate_conformance_cases.py` — the case generator
- `scripts/update_conformance.py` — the expected-output updater
- `scripts/verify_conformance_cases.py` — the drift check
- `docs/compiler-upgrade.md` — the compiler-bump procedure
- `docs/testing.md` — the overall test strategy
- `tests/compatibility/test_compiler_diagnostic_parity.py` — direct vs.
  through-pytscheck comparison
```
