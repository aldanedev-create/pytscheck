# Diagnostics and reporting

A type error is a completed check with `result.success=False`, not an exception. Operational failures raise instead.

```python
from pytscheck import check

result = check('export const age: number = "twenty";', filename="example.ts", keep_raw=True)
assert not result.success
assert any(d.code == 2322 for d in result.errors)
for d in result.diagnostics:
    location = f"{d.file or '<global>'}({d.line},{d.column})"
    print(f"{location}: {d.category} TS{d.code}: {d.message}")
```

## Positions and filenames

Compiler file locations use 1-based line and column values. `file=None` identifies a global diagnostic. Preserve compiler coordinates when reporting them; don't claim they are Python byte offsets. Paths from temporary sources may refer to temporary files that have already been removed.

`end_line`, `end_column`, and `related` are optional. Text parsing does not promise the complete structured diagnostic metadata available from a compiler API.

With an adapter, matching virtual filenames can become `origin_path`, and `origin_file` records the virtual path. With a source-map v3 map, mapped positions are translated to original coordinates. Without a map, positions remain generated; unmapped map segments also retain generated locations. See [project-aware adapters](adapter-projects.md).

## JSON from Python

```python
import json
from dataclasses import asdict
from pytscheck import check

result = check('export const x: number = "bad";')
payload = asdict(result)
print(json.dumps(payload, indent=2))
```

`asdict` includes all result fields, diagnostic fields, and nested related information. Tuples serialize as JSON arrays. `keep_raw=True` adds compiler text to this payload; otherwise it is `None`.

The [CLI JSON](cli.md) deliberately uses a smaller explicit shape and does not export raw output or related information.

## Error codes and text

Prefer numeric codes such as `2322` in program logic. Message wording and positions may change when the compiler pin changes. Error codes are not a guarantee that a different TypeScript version produces identical diagnostics. The [conformance suite](testing.md) records expectations for this pin.

Compiler stdout and stderr are captured separately and combined for parsing. The runner forces plain diagnostic formatting. Unrecognized output raises `OutputParseError`, so a changed compiler protocol cannot silently become a successful check.
