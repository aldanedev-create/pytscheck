# Support

## Getting help

- **Documentation:** https://pytscheck.readthedocs.io/
- **Questions and discussions:** https://github.com/your-org/pytscheck/discussions
- **Bug reports:** https://github.com/your-org/pytscheck/issues
- **Security reports:** see `SECURITY.md`

## Before opening an issue

1. Search existing issues and discussions.
2. Confirm the behavior against the latest commit on `main`.
3. Run `python scripts/verify_binaries.py` and include the output.
4. Include your OS, architecture, and Python version.

## What we can't help with

- Problems with the upstream TypeScript compiler's semantics — report those
  to Microsoft. PyTSCheck reports whatever `tsgo` reports.
- Recovering type information from already-transpiled JavaScript. Type
  annotations are gone by then; no adapter can recover them.
- Building a custom adapter for a tool we don't maintain. We'll document the
  protocol; the adapter itself belongs to the consuming tool.