# Installation

## Requirements

Use Python 3.11+ on a [supported OS and architecture](supported-platforms.md). Python 3.11–3.13 are tested in CI. The wheel must match the architecture of your Python interpreter, not just your operating system.

Wheels bundle `tsgo`, standard-library declarations, and upstream notices. No Node.js, npm, Go compiler, or third-party Python runtime dependency is required to check code after installing a wheel. Project-specific TypeScript packages and declarations must still be available if your sources import them.

## Install a published release

Once `0.1.0` is available on PyPI:

```bash
python -m pip install --upgrade pip
python -m pip install --only-binary=:all: "pytscheck==0.1.0"
python -m pytscheck --version
python -m pytscheck --where
```

An exact version selects the intended release. `--only-binary=:all:` prevents a source-build fallback when there is no matching wheel.

## Install before publication or offline

Download the wheel for your platform from a successful **Build PyPI distributions** Actions run. Extract the Actions artifact ZIP first; pip installs the `.whl`, not that outer ZIP.

```bash
python -m pip install --no-index --no-deps /path/to/actual-wheel.whl
```

For Windows PowerShell, use an actual Windows wheel filename:

```powershell
py -m pip install --no-index --no-deps .\pytscheck-0.1.0-py3-none-win_amd64.whl
py -m pytscheck --version
```

The package itself does not need network access at check time. Dependencies imported by your TypeScript project are separate from the compiler's bundled standard library.

## Work from source

```bash
git clone https://github.com/aldanedev-create/pytscheck.git
cd pytscheck
python -m venv .venv
```

Activate with `source .venv/bin/activate` on Linux/macOS, or `.\.venv\Scripts\Activate.ps1` in PowerShell.

```bash
python -m pip install -e ".[dev]"
python scripts/build_binaries.py linux-x64
python scripts/verify_binaries.py
```

Replace `linux-x64` with `win32-x64`, `win32-arm64`, `darwin-x64`, `darwin-arm64`, or `linux-arm64`. Editable installation does not fetch the compiler automatically. A normal wheel build can fetch it through the custom Hatch build hook.

## Verify an installation

```bash
python -m pytscheck string 'export const x: number = 1;'
```

On any shell, this Python command avoids quoting a TypeScript string:

```bash
python -c "from pytscheck import check; assert check('export const x: number = 1;').success"
```

If pip reports no matching distribution or the executable is missing, see [troubleshooting](troubleshooting.md).
