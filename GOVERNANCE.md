# Governance

PyTSCheck is a small, focused developer tool. Governance is deliberately light.

## Roles

- **Maintainers** have commit access and are responsible for reviews, releases,
  and the compatibility policy.
- **Contributors** submit pull requests and participate in discussions.

## Decision making

- Routine changes: lazy consensus among maintainers. If no maintainer objects
  within a reasonable window, the change lands.
- API changes, protocol changes, supported-platform changes, and license
  changes: explicit approval from at least two maintainers.
- Compiler version pin upgrades: require passing the conformance suite and
  at least one maintainer's sign-off.

## Releases

Releases are cut from `main` by a maintainer, tagged `vX.Y.Z`, and published
to PyPI. Platform wheels are built in CI. Release validation must pass before
publishing (see `.github/workflows/release.yml` and `scripts/release_check.py`).

## Compatibility policy

- The public Python API follows Semantic Versioning.
- The adapter protocol is versioned separately (`ADAPTER_PROTOCOL_VERSION`).
  Breaking protocol changes require a major protocol bump.
- The supported `tsgo` version is pinned and recorded in every `Result`.

## Changing this document

Submit a pull request. Substantive changes require explicit approval from at
least two maintainers.