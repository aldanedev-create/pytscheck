# Checking projects

Use `check_project()` when imports, declarations, configuration, and dependencies belong to a directory tree.

```python
from pytscheck import check_project

result = check_project("./frontend")
for error in result.errors:
    print(error.file, error.line, error.message)
```

The path must be an existing directory. With `tsconfig.json` at that root, the wrapper invokes `tsgo -p`. Without it, it passes discovered TypeScript filenames directly to the compiler.

## Minimal project

Create `frontend/src/app.ts`:

```typescript
export const message: string = "Hello";
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {"strict": true, "noEmit": true, "target": "es2022"},
  "include": ["src/**/*.ts"]
}
```

Run `python -m pytscheck project frontend`.

## Imports and declarations

The native compiler resolves relative imports and dependencies. The bundled declarations cover standard JavaScript/TypeScript libraries; they do not replace project packages such as React or `@types/node`. Install or provide the declarations your project needs through its own package workflow.

For a project without a config, discovery includes `.ts`, `.tsx`, `.mts`, and `.cts` suffixes, including `.d.ts` files through their `.ts` suffix. Paths containing `node_modules` are excluded from the input scan, although the compiler can still resolve imported dependencies there. An empty discovery result raises `ConfigurationError`.

The fallback scan caps inputs at 20,000 files. This cap is not applied to tsconfig-managed inputs. Neither mode provides a complete sandbox or a global project-byte limit.

## Path aliases

Prefer a tsconfig and relative alias destinations:

```json
{
  "compilerOptions": {
    "module": "preserve",
    "moduleResolution": "bundler",
    "paths": {"@lib/*": ["./src/lib/*"]},
    "noEmit": true
  },
  "include": ["src/**/*.ts"]
}
```

The pinned native compiler does not support every older TypeScript option. The repository's alias fixture uses relative `paths` destinations rather than the removed `baseUrl` option. Compiler diagnostics are the authority for an option accepted by your exact version.

## Monorepos and references

`check_project` invokes project checking, not `tsgo -b`. It does not recursively build referenced packages, generate their declarations, or orchestrate workspace tasks. Prepare referenced declaration outputs using your build system, then check the relevant project roots.

A string `extends` target resolving outside the supplied root is rejected by prevalidation. Review [configuration](configuration.md) for this restriction. Adapter checking is a separate path: it checks supplied virtual files in a private directory rather than loading the original root's tsconfig.

## Use in CI

```bash
python -m pytscheck project frontend --json
```

Use exit codes to distinguish compiler errors from failure to run the checker. See [CLI](cli.md).
