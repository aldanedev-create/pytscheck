# Contributing to PyTSCheck

Start with [development setup](docs/development.md) and [testing](docs/testing.md). Contributions should preserve the documented public API and keep operational failures distinct from compiler errors.

## Setup and checks

```bash
git clone https://github.com/aldanedev-create/pytscheck.git
cd pytscheck
python -m venv .venv
# Activate for your shell, then:
python -m pip install -e ".[dev]"
python scripts/build_binaries.py linux-x64
python -m ruff check src tests scripts conformance benchmarks
python -m ruff format --check src tests scripts conformance benchmarks
python -m mypy src/pytscheck
python -m pytest tests
python conformance/run.py
```

Replace `linux-x64` with your [platform identifier](docs/supported-platforms.md). Run compiler-mutating tests serially with no other suite/build using that checkout.

## Change conventions

- Keep the PR focused and describe the problem, resulting behavior, and validation.
- Test observable behavior with real files/compiler executions when applicable.
- Do not disguise compiler crashes, adapter extraction failures, or unparsed output as successful checks.
- Update documentation and `CHANGELOG.md` for user-visible changes.
- Change generators before regenerating their fixtures; review fixture and conformance diffs.
- Keep consumer adapters in their own packages; do not import frameworks into core.
- Follow the existing typing and Ruff style. Do not change public exports or exception taxonomy casually.

Use concise commit messages such as `fix: bound compiler output` or `docs: explain project checking`. Submit PRs against `main` and wait for all CI checks. Compiler pin/platform changes require the [compiler-upgrade procedure](docs/compiler-upgrade.md).

## Reports

Report bugs through [GitHub issues](https://github.com/aldanedev-create/pytscheck/issues) with versions, OS/architecture, the smallest reproduction, and relevant sanitized output. Report security concerns using [SECURITY.md](SECURITY.md).

Participation follows [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). See [publishing](docs/publishing.md) for maintainer release steps.
