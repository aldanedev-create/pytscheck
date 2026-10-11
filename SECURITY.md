# Security Policy

## Supported versions

PyTSCheck is in pre-alpha. Until 1.0, only the latest commit on `main` is
supported for security fixes.

## Reporting a vulnerability

Please do **not** open a public issue for security problems.

Report privately via GitHub Security Advisories:
https://github.com/your-org/pytscheck/security/advisories/new

Or email `security@example.invalid` with:

- A description of the issue and its impact
- A minimal reproduction
- Affected versions
- Any suggested mitigation

We aim to acknowledge reports within 3 business days and to provide a
resolution timeline within 10 business days.

## Threat model

PyTSCheck:

- invokes a bundled native binary as a subprocess
- never uses a shell for that invocation
- parses untrusted compiler output
- accepts source strings, file paths, and project directories from callers
- optionally accepts adapter output from third-party packages

The following are considered in scope:

- Subprocess argument injection
- Path traversal, symlink escape, or writes outside designated temp dirs
- Denial of service via oversized inputs, output bombs, or hangs
- Parser crashes or infinite loops on hostile output
- Privilege escalation through bundled binary replacement

The following are out of scope:

- Vulnerabilities in the upstream TypeScript compiler itself
  (report those to Microsoft)
- Attacks requiring an already-compromised Python environment
- Social engineering

## Supply chain

- Bundled `tsgo` binaries are pinned to an exact npm version and verified
  against the registry's SHA-512 integrity value at build time.
- Dependencies are audited in CI (`pip-audit`).
- Builds are reproducible; see `.github/workflows/reproducible-build.yml`.