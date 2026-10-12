# Compiler options

`CompilerOptions` exposes the subset of flags the wrapper uses directly. The pinned compiler validates flag names and values; not every option from another TypeScript version is supported.

| Python field | Default | Compiler behavior |
| --- | --- | --- |
| `strict` | `True` | Emit `--strict` when true |
| `no_emit` | `True` | Emit `--noEmit` when true |
| `skip_lib_check` | `False` | Emit `--skipLibCheck` when true |
| `types` | `()` | Non-empty tuple becomes comma-separated `--types` |
| `lib` | `()` | Non-empty tuple becomes comma-separated `--lib` |
| `target` | `None` | Optional `--target` value |
| `module` | `None` | Optional `--module` value |
| `module_resolution` | `None` | Optional `--moduleResolution` value |
| `extra` | `{}` | Additional compiler flags |

```python
from pytscheck import CompilerOptions, check

result = check(
    "export const el = document.createElement('div');",
    options=CompilerOptions(target="es2022", lib=("es2022", "dom")),
)
assert result.success
```

`types=("node",)` selects an installed declaration package; it does not download it. An empty `types` tuple omits the flag and is not equivalent to `"types": []` in a tsconfig. Use a project tsconfig to explicitly disable automatic type-package inclusion.

## Additional flags

```python
from pytscheck import CompilerOptions, check

result = check(
    "export const x: number = 1;",
    options=CompilerOptions(extra={"noUnusedLocals": True}),
)
assert result.success
```

Keys may be `noUnusedLocals` or `--noUnusedLocals`. Values are serialized individually; no shell is involved. `True` emits a flag; `False` and `None` omit it; strings and other values are converted to text. Provide compiler list values as comma-separated strings when using `extra`.

The runner always appends `--pretty false` so diagnostics stay machine-readable even when a project or terminal enables color. Pretty output cannot be enabled through `extra`.

Avoid execution-mode flags such as `watch`, `build`, and `help`, and do not use `extra` to smuggle file/project arguments. The checker expects one bounded diagnostic run. Disabling `no_emit` may allow compiler output on disk, so leave the default for checking workflows.

There are no public `timeout`, `max_source_bytes`, or subprocess-limit fields in `CompilerOptions`. The runtime defaults are described in [security](security.md).
