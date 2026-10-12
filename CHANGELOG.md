# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Add musllinux 1.2+ tags to verified static Linux wheels, official ARMv7 binaries, and pinned-source Linux/Windows x86 builds. Test installed wheels in Alpine, 32-bit Linux, and 32-bit Windows environments.

### Added

- Optional framework-independent ProjectContext for inherited settings, real/generated imports, isolated workspaces and declaration resources from Python packages.
- Source-map v3 VLQ primary/end/related position translation, multiple sources, sourceRoot and inline indexed sections.
- Project-aware component/schema example, migration guide and real compiler/zip-resource/Unicode/concurrency/timeout regressions.

- JavaScript/JSDoc guide and a runnable string/project example with real compiler regressions.

- `scripts/publish.py` builds and validates all nine wheels plus the source archive, then uploads through Twine; supports TestPyPI and build-only runs.

- Complete user/maintainer documentation, CLI reference, adapter limitations, and PyPI publishing guide.

- Repository scaffold: `pyproject.toml`, packaging, linting, typing, testing config.
- Phase-0 scripts: `scripts/build_binaries.py`, `scripts/verify_binaries.py`.
- Public exception hierarchy in `pytscheck.exceptions`.
- Default constants in `pytscheck.defaults`.

### Changed

- Normalize adapter input paths before duplicate checks; reject directory/file collisions, invalid text, and oversized virtual sources.
- Run standalone file/string checks with `--ignoreConfig` to avoid incidental tsconfig errors.
- Validate compiler options and preserve configuration/adapter exception types for malformed inputs.
- Honor internal client runner overrides with per-context isolation and restore them after each call.

- Nothing yet.

### Deprecated

- Nothing yet.

### Removed

- Nothing yet.

### Fixed

- Nothing yet.

### Security

- Nothing yet.