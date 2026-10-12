"""Check JSDoc-typed JavaScript without Node.js."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pytscheck import CompilerOptions, check, check_project

SOURCE = """/**
 * @param {number} count
 * @returns {number}
 */
export function double(count) { return count * 2; }
export const value = double("wrong");
"""


def main() -> int:
    options = CompilerOptions(extra={"allowJs": True, "checkJs": True})
    result = check(SOURCE, filename="input.js", options=options)
    assert any(error.code == 2345 for error in result.errors), result.diagnostics
    for error in result.errors:
        print(f"{error.file}:{error.line}:{error.column}: TS{error.code}: {error.message}")
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "app.js").write_text(SOURCE.replace('double("wrong")', "double(2)"))
        (root / "tsconfig.json").write_text(
            json.dumps(
                {
                    "compilerOptions": {"allowJs": True, "checkJs": True, "noEmit": True},
                    "include": ["*.js"],
                }
            )
        )
        assert check_project(root).success
    print("JSDoc error detected; corrected JavaScript project passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
