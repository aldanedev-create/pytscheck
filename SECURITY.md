# Security policy

## Supported versions

The project is in development. Security fixes target the latest code on `main`; no long-term maintenance policy for older development releases is promised.

## Report privately

Use [GitHub private vulnerability reporting](https://github.com/aldanedev-create/pytscheck/security/advisories/new) when available. Do not publish exploit details or private source in a public issue. If the private reporting form is unavailable, contact the repository maintainer through an established private channel; there is no configured security email address in this repository.

Include the issue's impact, affected version, OS/architecture, minimal reproduction, and any suggested mitigation. Avoid unverified promises about acknowledgment/resolution times.

## Threat model

The wrapper accepts source strings, paths, projects, and third-party adapter output; invokes a pinned native compiler; and parses its output. Relevant concerns include argument handling, temporary paths, source traversal, output/input exhaustion, process cleanup, and binary provenance.

The existing checks are described in [security and limits](docs/security.md). They do not create a sandbox around project filesystem access or plugin code. Use OS isolation for hostile input. Vulnerabilities in the bundled upstream compiler should also be reported to its upstream maintainers.

## Supply chain

Compiler archives are pinned and verified using upstream SHA-512 values; manifests record binary hashes and sizes. Wheels retain upstream licenses/notices. Source builds can download compiler archives. Passing integrity checks establishes correspondence to recorded bytes, not a guarantee that upstream code is free of vulnerabilities.

The implemented CI and distribution workflows are in `.github/workflows/ci.yml` and `.github/workflows/distributions.yml`. This policy does not claim a dedicated reproducible-build or automatic publishing workflow.
