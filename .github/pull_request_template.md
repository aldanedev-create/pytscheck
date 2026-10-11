<!--
Thanks for contributing to pytscheck!

Before opening the PR, please:

  1. Run `python scripts/run_all_tests.py --fast` locally.
  2. Update CHANGELOG.md under [Unreleased].
  3. Confirm your changes are covered by tests.

If this is a compiler version bump, see docs/compiler-upgrade.md.
-->

## Summary

<!-- One paragraph describing what this PR does and why. -->

## Type of change

- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change
- [ ] Documentation
- [ ] Internal / tooling / CI
- [ ] Compiler version bump

## Checklist

- [ ] Tests added or updated
- [ ] `CHANGELOG.md` updated
- [ ] `ruff check` passes
- [ ] `ruff format --check` passes
- [ ] `mypy src/pytscheck` passes
- [ ] `pytest tests -q` passes
- [ ] If public API changed: `docs/` updated
- [ ] If adapter protocol changed: `src/pytscheck/integrations/README.md` updated
- [ ] If compiler pin changed: conformance `expected/` regenerated and reviewed

## Related issues

<!-- e.g. "Closes #123", "Fixes #456" -->

## Notes for reviewers

<!-- Anything that isn't obvious from the diff. -->