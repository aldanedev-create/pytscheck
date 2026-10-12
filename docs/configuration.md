# Configuration

## Defaults

Checks use `CompilerOptions(strict=True, no_emit=True, skip_lib_check=False)`. These become command-line flags `--strict` and `--noEmit`; library checking stays enabled. Optional targets, module settings, type packages, and libraries default to the compiler's choices.

```python
from pytscheck import CompilerOptions, check

options = CompilerOptions(target="es2022", module="nodenext", module_resolution="nodenext")
result = check("export const answer: number = 42;", options=options)
assert result.success
```

A dictionary of those same Python field names also works:

```python
from pytscheck import check

assert check("export const x = 1;", options={"target": "es2022"}).success
```

Use `module_resolution`, not tsconfig's `moduleResolution`, in that dictionary.

## Project tsconfig

`check_project(root)` looks for `root/tsconfig.json`. It prevalidates JSON/JSONC, including comments and trailing commas, then invokes `tsgo -p` with the default/options flags. It does not search parent directories for another config. A malformed config raises `ConfigurationError` or produces a compiler configuration diagnostic, depending on where it is detected.

```json
{
  "compilerOptions": {
    "target": "es2022",
    "module": "nodenext",
    "moduleResolution": "nodenext",
    "strict": true,
    "noEmit": true
  },
  "include": ["src/**/*.ts"]
}
```

Command-line flags supplied by the wrapper override corresponding tsconfig options. Thus default strict/no-emit flags apply even if the config disables them.

## Boolean behavior

For `strict`, `no_emit`, and `skip_lib_check`, `True` emits the positive compiler flag. `False` omits the flag; it does not pass an explicit negative value. For example, `strict=False` lets a project's tsconfig decide strictness rather than overriding `strict:true`.

The `extra` mapping follows similar rules: `True` emits a bare flag, `False`/`None` omit it, and other values become a flag/value pair. To explicitly override a tsconfig boolean, a compiler string value may be used, for example `extra={"strict": "false"}`. See [compiler options](compiler-options.md).

## Extends and references

The wrapper rejects a string `extends` target that resolves outside the supplied project root. Ordinary configurations extending `../tsconfig.json` can therefore fail. Choose a root containing the configuration you intend to check and keep extension targets inside it; do not assume arbitrary shared-parent layouts are supported.

The compiler handles resolution of accepted configuration contents. This API does not run build mode for referenced projects. See [project checking](project-checking.md) before checking a monorepo.
