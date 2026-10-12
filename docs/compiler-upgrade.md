# Upgrading the bundled compiler

Package version, compiler version, and adapter protocol version are independent. A compiler update can change diagnostics or supported flags even when the Python API stays the same.

## Update deliberately

1. Choose and inspect the intended upstream native preview version.
2. Update the compiler pin in `scripts/build_binaries.py` and `src/pytscheck/version.py`, and each target's recorded upstream archive integrity as required by the fetch script.
3. Fetch all six targets with `python scripts/build_binaries.py <platform>` and regenerate/verify the manifest using the repository scripts.
4. Run native tests, fixture gates, lint/type checks, and conformance before rewriting expectations.
5. Stage changed expected diagnostics with `python scripts/update_conformance.py`; review the staged differences. Use `--apply` only when the new behavior is understood.
6. Run `python conformance/run.py`, `python scripts/update_conformance.py --check`, benchmarks, and the release gate.
7. Rebuild all wheels and inspect binary architecture, minimum OS tags, checksums, declarations, notices, and native CI.

`generate_conformance_cases.py` owns the input manifest. Updating expectations must not replace it with a different schema. Do not regenerate cases or expected diagnostics just to turn an unexplained failure green.

## Review impact

Record changed error codes/messages/positions, removed flags, standard-library differences, platform requirements, and performance changes in the changelog. If binary minimum OS requirements change, update wheel tags, platform docs, and build tests together.

A successful Linux run cannot validate a Windows/macOS compiler upgrade. Wait for native CI and all six distribution builds before publishing. Follow [publishing](publishing.md).
