# JavaScript and JSDoc

PyTSCheck can type-check JavaScript through the bundled native TypeScript compiler. JSDoc supplies type information while your files stay `.js`. Checking requires no Node.js runtime when using a platform wheel.

## Check a project

Create `tsconfig.json` at the project root:

```json
{
  "compilerOptions": {
    "allowJs": true,
    "checkJs": true,
    "strict": true,
    "noEmit": true
  },
  "include": ["src/**/*.js"]
}
```

`allowJs` includes JavaScript inputs. `checkJs` enables checking across those files. `noEmit` keeps the compiler from writing JavaScript outputs; PyTSCheck enables it by default too.

In `src/app.js`:

```javascript
/** @type {number} */
export const age = "twenty";
```

Run:

```bash
pytscheck project .
```

The compiler reports TS2322 for assigning a string to a number. Replace `"twenty"` with `20` to pass.

```python
from pytscheck import check_project

result = check_project(".")
for error in result.errors:
    print(error.file, error.line, error.code, error.message)
```

Project mode applies the root configuration and its imports. Without a tsconfig, automatic discovery scans TypeScript extensions, not `.js`; use a config for JavaScript projects.

## Functions, object types, and return values

```javascript
/** @typedef {{name: string, age: number}} User */

/**
 * @param {User} user
 * @returns {string}
 */
export function greet(user) {
  return user.name;
}

// Error: age must be a number.
greet({name: "Ada", age: "twenty"});
```

The compiler can use `@type`, `@param`, `@returns`, and `@typedef` to check assignments and function calls. Supported syntax and exact diagnostics follow the pinned native compiler, not a separate JSDoc documentation generator.

## Check a string or individual file

Pass the JavaScript filename and compiler flags explicitly:

```python
from pytscheck import CompilerOptions, check

options = CompilerOptions(extra={"allowJs": True, "checkJs": True})
result = check(
    '/** @type {number} */\nexport const age = "twenty";',
    filename="input.js",
    options=options,
)
assert [error.code for error in result.errors] == [2322]
```

For a file on disk:

```python
from pytscheck import CompilerOptions, check_file

result = check_file(
    "src/app.js",
    options=CompilerOptions(extra={"allowJs": True, "checkJs": True}),
)
```

Single-file checks ignore incidental tsconfigs and use the supplied options. Use `check_project` to inherit project configuration. The CLI's `file` subcommand has no `allowJs`/`checkJs` flags; use the Python API or configured project mode.

## Per-file checking and mixed projects

With `allowJs:true`, a leading `// @ts-check` enables checking for one JavaScript file even if project-wide `checkJs` is disabled. `// @ts-nocheck` can disable checking for a file. These directives alter what is checked; a clean result is not proof that excluded or unchecked files are type-safe.

A project can include both `src/**/*.ts` and `src/**/*.js`. Provide the declarations needed by imports and select suitable module/module-resolution options in tsconfig. The bundled standard libraries do not supply every external package's types.

## Run the verified example

```bash
python examples/check_jsdoc.py
```

It detects a JSDoc-typed function's invalid string argument, then checks the corrected JavaScript project successfully. JSDoc checking validates types; it does not execute your code, guarantee runtime behavior, or generate documentation pages.

See [compiler options](compiler-options.md), [project checking](project-checking.md), and [diagnostics](diagnostics.md).
