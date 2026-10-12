# Quick start

Install a wheel using the [installation guide](installation.md). These examples use the public top-level API.

## Check a string

```python
from pytscheck import check

valid = check("export const count: number = 3;")
assert valid.success

invalid = check('export const count: number = "three";')
assert not invalid.success
assert any(error.code == 2322 for error in invalid.errors)
for error in invalid.errors:
    print(error.file, error.line, error.column, error.message)
```

`check()` writes a private temporary file and removes it after checking. Use a non-empty basename such as `input.ts` or `view.tsx` for `filename`; directory paths are rejected. Use file/project checking when imports depend on files on disk.

## Check a file

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from pytscheck import check_file

with TemporaryDirectory() as directory:
    path = Path(directory) / "app.ts"
    path.write_text("export const count: number = 3;", encoding="utf-8")
    result = check_file(path)
    assert result.success
```

## Check a project

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from pytscheck import check_project

with TemporaryDirectory() as directory:
    root = Path(directory)
    (root / "tsconfig.json").write_text(
        '{"compilerOptions":{"strict":true,"noEmit":true},"include":["*.ts"]}',
        encoding="utf-8",
    )
    (root / "app.ts").write_text("export const x: number = 1;", encoding="utf-8")
    assert check_project(root).success
```

For JavaScript annotated with JSDoc, see the [JSDoc guide](jsdoc.md).

Read [project checking](project-checking.md) for imports, aliases, declarations, and references.

## Set compiler options

```python
from pytscheck import CompilerOptions, check

result = check(
    "export const x: number = 1;",
    options=CompilerOptions(target="es2022", lib=("es2022", "dom")),
)
assert result.success
```

## Handle failures separately

```python
from pytscheck import PyTSCheckError, check

try:
    result = check('export const x: number = "wrong";')
except PyTSCheckError as exc:
    print("Could not complete the check:", exc)
else:
    if result.success:
        print("No compiler errors")
    else:
        print("Compiler reported", len(result.errors), "errors")
```

An exception is different from a completed check reporting type errors. See [Python API](python-api.md) and [diagnostics](diagnostics.md).
