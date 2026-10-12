# Publishing to PyPI

This guide publishes the current **release version `0.1.0`**. It does not upload anything automatically. Use artifacts from the exact commit whose CI passed.

## Build and upload with one script

Install the tools, then run from the repository root:

```bash
python -m pip install --upgrade build twine
python scripts/publish.py
```

The script builds all six platform wheels and one source archive, validates version consistency and wheel contents, runs strict Twine checks, then uploads to **real PyPI**. Twine prompts for your PyPI API token (or uses your configured credentials). The package version is whatever is committed in both version files; it does not change the version for you.

For a test upload or a build without uploading:

```bash
python scripts/publish.py --repository testpypi
python scripts/publish.py --build-only
```

Each invocation uses a new directory under `build/releases/`, prints its location, and uploads only the seven freshly built files. Existing distributions are preserved. Any failed build or validation stops the upload. This script does not run the full test suite; complete release CI first. Network access is needed for isolated build dependencies and any missing pinned compiler archives. Do not run it while compiler-mutating tests are active in the same checkout.

## 1. Choose and commit the release version

Package versions must agree in `pyproject.toml` and `src/pytscheck/version.py`. Leave both at `0.1.0` to publish this initial release. For a subsequent version, change both deliberately, update the changelog and documentation, commit, and wait for fresh successful CI/builds. Do not rename an existing wheel to change its version.

PyPI does not allow reusing a previously uploaded distribution filename. If this version was already uploaded, choose a new version and rebuild. Package-name ownership must also belong to your PyPI account; GitHub repository ownership does not reserve the PyPI name.

Merge the release fixes and documentation PRs, then fetch the final code:

```bash
git switch main
git pull --ff-only origin main
```

Check the **CI** and **Build PyPI distributions** workflows in [Actions](https://github.com/aldanedev-create/pytscheck/actions). Use the successful distribution run for this exact commit, including the latest README.

## 2. Obtain all seven distributions

Open **Build PyPI distributions** for the chosen commit and download these artifact ZIPs:

| Artifact | File to extract |
| --- | --- |
| `wheel-linux-x64` | Linux x64 `.whl` |
| `wheel-linux-arm64` | Linux ARM64 `.whl` |
| `wheel-win32-x64` | Windows x64 `.whl` |
| `wheel-win32-arm64` | Windows ARM64 `.whl` |
| `wheel-darwin-x64` | macOS Intel `.whl` |
| `wheel-darwin-arm64` | macOS Apple Silicon `.whl` |
| `sdist` | `pytscheck-0.1.0.tar.gz` |

Extract the actual six `.whl` files and one `.tar.gz` into a new clean `dist/` directory. Do not upload the outer ZIP files or `compiler-*` artifacts to PyPI. Keep compiler bundles separately for standalone downloads.

The six wheel suffixes are listed in [supported platforms](supported-platforms.md). Every file must contain the intended package version. A previous build saved before a README update will still carry the old PyPI description; use the new run.

## 3. Set up publishing tools and validate

On Windows PowerShell, from the folder containing `dist/`:

```powershell
py -m venv .publish-venv
.\.publish-venv\Scripts\Activate.ps1
python -m pip install --upgrade pip twine
Get-ChildItem .\dist
python -m twine check --strict dist/*
```

On Linux/macOS, use `python3 -m venv .publish-venv`, `source .publish-venv/bin/activate`, then the same pip/Twine commands. Twine checks metadata and README rendering; it does not run the compiler or replace CI.

If you built locally, a plain `python -m build --wheel` builds only the host wheel. To build all targets locally, install `build` and run this Python script from the repository root:

```python
import os
import subprocess
import sys

platforms = (
    "linux-x64", "linux-arm64", "win32-x64", "win32-arm64",
    "darwin-x64", "darwin-arm64",
)
for platform in platforms:
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel"],
        env={**os.environ, "PYTSCHECK_BUILD_PLATFORM": platform},
        check=True,
    )
subprocess.run([sys.executable, "-m", "build", "--sdist"], check=True)
```

This requires access to build dependencies and pinned npm archives. Cross-building does not replace native testing. See [development](development.md), [testing](testing.md), and [binary distribution](binary-distribution.md).

## 4. Create accounts and upload tokens

Create/verify an account on [PyPI](https://pypi.org/account/register/) and configure its required two-factor authentication. For a first project upload, create an account-scoped API token in account settings; after the project exists, prefer a project-scoped token.

[TestPyPI](https://test.pypi.org/account/register/) is a separate service with a separate account/token. A TestPyPI token cannot upload to PyPI. Store tokens privately; do not put them in source files, commits, screenshots, or chat.

Use `--username __token__` below and paste the appropriate full token at the password/token prompt. Terminal input is hidden.

## 5. Test the upload

With the TestPyPI token:

```bash
python -m twine upload --repository testpypi --username __token__ dist/*
```

Create a fresh virtual environment outside the repository so the editable checkout cannot mask the installed package, then:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --no-deps --only-binary=:all: "pytscheck==0.1.0"
python -m pytscheck --version
python -m pytscheck --where
python -c "from pytscheck import check; assert check('export const x: number = 1;').success"
python -c "from pytscheck import check; r=check('export const x: number = false;'); assert not r.success"
```

The second source intentionally assigns a boolean to a number and must report a type error. Verify wheel installation on representative supported systems, not just import success.

## 6. Publish to real PyPI

Return to the publishing environment/folder. Use the real PyPI token:

```bash
python -m twine upload --username __token__ dist/*
```

Review the resulting [project page](https://pypi.org/project/pytscheck/) and its files. Test in another clean environment:

```bash
python -m pip install --only-binary=:all: "pytscheck==0.1.0"
python -m pytscheck --version
python -c "from pytscheck import check; assert check('export const x: number = 1;').success"
```

To install the newest available prerelease rather than a specific version, users can use `python -m pip install --pre pytscheck`. Stable releases do not need prerelease selection.

## 7. Tag and provide GitHub downloads

After a successful upload, tag the exact released commit (for this version, `v0.1.0`), push the tag, and create a GitHub Release with changelog notes. Attach the seven PyPI distributions and any standalone compiler bundles you want to offer. Keep declaration libraries and notices beside the compiler in those bundles.

Tagging alone does not upload to PyPI. The current distribution workflow builds artifacts for PRs/main pushes or manual dispatch; it has no automatic publishing job.

## Upload errors

| Error | Resolution |
| --- | --- |
| Invalid/expired token or 403 | Check service, token, scope, and project ownership |
| File already exists | Use a new version and rebuild; do not rename files or overwrite |
| Name unavailable | Use a name you own; changing it requires metadata/docs updates and a rebuild |
| Missing wheels | Upload all six wheel artifacts plus source archive from the same commit/version |
| README rendering error | Fix Markdown/metadata, rebuild, and run strict Twine checks again |

Official references: [PyPA packaging tutorial](https://packaging.python.org/en/latest/tutorials/packaging-projects/), [PyPI account/token help](https://pypi.org/help/), and [Twine documentation](https://twine.readthedocs.io/).
