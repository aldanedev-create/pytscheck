"""Isolated project snapshots for context-aware adapters."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import replace
from importlib import resources
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from ..config import CompilerOptions, validate_options
from ..exceptions import AdapterExtractionError, AdapterProtocolError, ConfigurationError
from ..models import Result, SourceFile
from ..runner import run
from .context import DeclarationResource, ProjectContext
from .sources import _validate_sources

_SOURCE_EXTENSIONS = {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"}
_SKIP = {"node_modules", ".git", "__pycache__", "dist", "build", "venv", ".venv", ".review-venv"}
_FIELDS = {
    "strict": "strict",
    "no_emit": "noEmit",
    "skip_lib_check": "skipLibCheck",
    "types": "types",
    "lib": "lib",
    "target": "target",
    "module": "module",
    "module_resolution": "moduleResolution",
}


def _jsonc(path: Path) -> dict[str, Any]:
    try:
        if path.stat().st_size > 8 * 1024 * 1024:
            raise ConfigurationError(f"configuration exceeds 8 MiB: {path}")
        text = path.read_text(encoding="utf-8-sig")
        text = re.sub(
            r'"(?:\\.|[^"\\])*"|/\*[\s\S]*?\*/|//[^\r\n]*',
            lambda m: m[0] if m[0].startswith('"') else " ",
            text,
        )
        text = re.sub(
            r'"(?:\\.|[^"\\])*"|,\s*([}\]])', lambda m: m[0] if m[0].startswith('"') else m[1], text
        )
        data = json.loads(text)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise ConfigurationError(f"cannot load tsconfig {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigurationError(f"tsconfig must be an object: {path}")
    return data


def _base_config(value: str, directory: Path) -> Path:
    if value.startswith((".", "/")) or Path(value).is_absolute():
        candidate = (directory / value).resolve()
        candidates = [candidate, Path(str(candidate) + ".json")]
    else:
        candidates = []
        for parent in (directory, *directory.parents):
            candidate = parent / "node_modules" / value
            candidates += [candidate, Path(str(candidate) + ".json"), candidate / "tsconfig.json"]
            metadata = candidate / "package.json"
            if metadata.is_file():
                name = _jsonc(metadata).get("tsconfig")
                if isinstance(name, str):
                    candidates.insert(0, candidate / name)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise ConfigurationError(f"cannot resolve tsconfig extends {value!r} from {directory}")


def _settings(path: Path, stack: tuple[Path, ...] = ()) -> tuple[dict[str, Any], dict[str, Path]]:
    path = path.resolve()
    if path in stack or len(stack) >= 64:
        raise ConfigurationError(f"cyclic or excessively deep tsconfig extends: {path}")
    data = _jsonc(path)
    options: dict[str, Any] = {}
    origins: dict[str, Path] = {}
    bases = data.get("extends", [])
    if isinstance(bases, str):
        bases = [bases]
    if not isinstance(bases, list) or not all(isinstance(v, str) for v in bases):
        raise ConfigurationError("tsconfig extends must be a string or list of strings")
    for base in bases:
        inherited, locations = _settings(_base_config(base, path.parent), (*stack, path))
        options.update(inherited)
        origins.update(locations)
    own = data.get("compilerOptions", {})
    if not isinstance(own, dict):
        raise ConfigurationError("compilerOptions must be an object")
    options.update(own)
    origins.update({key: path.parent for key in own})
    return options, origins


def _overrides(value: CompilerOptions | dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        try:
            options = CompilerOptions(**value)
        except TypeError as exc:
            raise ConfigurationError(f"invalid compiler options: {exc}") from exc
        fields = set(value)
    else:
        options = value
        fields = set(_FIELDS)
    validate_options(options)
    result: dict[str, Any] = {}
    for field, name in _FIELDS.items():
        item = getattr(options, field)
        if field in fields and item is not None:
            if field in {"types", "lib"}:
                if isinstance(value, dict) or item:
                    result[name] = list(item)
            else:
                result[name] = item
    result.update(
        {key.removeprefix("--"): item for key, item in options.extra.items() if item is not None}
    )
    return result


class _Snapshot:
    def __init__(self, root: Path, workspace: Path, context: ProjectContext) -> None:
        self.root, self.workspace, self.context = root, workspace, context
        self.files = self.bytes = 0

    def write(self, path: Path, data: bytes) -> None:
        self.files += 1
        self.bytes += len(data)
        if (
            self.files > self.context.max_workspace_files
            or self.bytes > self.context.max_workspace_bytes
        ):
            raise ConfigurationError("adapter workspace exceeds its file/byte limit")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def copy(self, source: Path, destination: Path) -> None:
        self.files += 1
        if self.files > self.context.max_workspace_files:
            raise ConfigurationError("adapter workspace exceeds its file limit")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as reader, destination.open("wb") as writer:
            while data := reader.read(64 * 1024):
                self.bytes += len(data)
                if self.bytes > self.context.max_workspace_bytes:
                    raise ConfigurationError("adapter workspace exceeds its byte limit")
                writer.write(data)

    def project_files(self, resolve_json: bool = False) -> list[Path]:
        found = []
        for directory, dirs, files in os.walk(self.root, followlinks=False):
            dirs[:] = [d for d in dirs if d not in _SKIP and not d.startswith(".pytscheck-")]
            for name in files:
                source = Path(directory) / name
                if source.suffix not in _SOURCE_EXTENSIONS and not (
                    source.name == "package.json" or (resolve_json and source.suffix == ".json")
                ):
                    continue
                if not source.resolve().is_relative_to(self.root):
                    raise ConfigurationError(f"project source symlink escapes root: {source}")
                relative = source.relative_to(self.root)
                self.copy(source, self.workspace / relative)
                if source.suffix in _SOURCE_EXTENSIONS:
                    found.append(relative)
        return found

    def resource(self, item: Any, target: Path, depth: int = 0) -> list[Path]:
        if depth > 64:
            raise ConfigurationError("declaration resources exceed maximum directory depth")
        if isinstance(item, Path) and item.is_symlink():
            raise ConfigurationError("declaration resources cannot contain symlinks")
        if item.is_dir():
            result = []
            for child in item.iterdir():
                if child.name in {".", ".."} or "/" in child.name or "\\" in child.name:
                    raise ConfigurationError("unsafe declaration resource name")
                result.extend(self.resource(child, target / child.name, depth + 1))
            return result
        if not item.is_file():
            raise ConfigurationError(f"declaration resource does not exist: {item}")
        if not (item.name.endswith((".d.ts", ".d.mts", ".d.cts")) or item.name == "package.json"):
            return []
        self.files += 1
        if self.files > self.context.max_workspace_files:
            raise ConfigurationError("adapter workspace exceeds its file limit")
        target.parent.mkdir(parents=True, exist_ok=True)
        with item.open("rb") as reader, target.open("wb") as writer:
            while data := reader.read(64 * 1024):
                self.bytes += len(data)
                if self.bytes > self.context.max_workspace_bytes:
                    raise ConfigurationError("adapter workspace exceeds its byte limit")
                writer.write(data)
        return [target] if target.name != "package.json" else []

    def relocate(self, value: str, origin: Path) -> str:
        absolute = (origin / value).resolve()
        if absolute.is_relative_to(self.root) and "node_modules" not in absolute.parts:
            return str(self.workspace / absolute.relative_to(self.root))
        return str(absolute)


def check_project_sources(
    root: Path,
    sources: tuple[SourceFile, ...],
    context: ProjectContext,
    *,
    options: CompilerOptions | dict[str, Any] | None = None,
    keep_raw: bool = False,
) -> Result:
    """Check generated and real inputs without replacing original project files."""
    from ..checker import _run_tsgo_on_args, _runner_override

    if not isinstance(context, ProjectContext):
        raise AdapterProtocolError("get_context must return ProjectContext")
    if not isinstance(context.compiler_options, dict):
        raise ConfigurationError("ProjectContext.compiler_options must be a dictionary")
    for limit in (context.max_workspace_files, context.max_workspace_bytes):
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ConfigurationError("workspace limits must be positive integers")
    for flag in (context.inherit_tsconfig, context.include_project_files):
        if not isinstance(flag, bool):
            raise ConfigurationError("project context flags must be bools")
    if context.tsconfig is not None and not isinstance(context.tsconfig, (str, Path)):
        raise ConfigurationError("tsconfig must be a path or None")
    for collection in (context.declaration_paths, context.declaration_resources):
        if not isinstance(collection, (tuple, list)):
            raise ConfigurationError("declaration collections must be tuples or lists")
    sources = _validate_sources(sources)
    if not sources:
        raise ConfigurationError("adapter returned no sources to check")
    config = (
        (root / context.tsconfig).resolve()
        if context.tsconfig is not None
        else root / "tsconfig.json"
    )
    settings: dict[str, Any] = {}
    origins: dict[str, Path] = {}
    if context.inherit_tsconfig and (config.exists() or context.tsconfig is not None):
        settings, origins = _settings(config)
    settings.update(context.compiler_options)
    origins.update({key: root for key in context.compiler_options})
    supplied = _overrides(options)
    settings.update(supplied)
    origins.update({key: root for key in supplied})
    if supplied.get("noEmit") is False or context.compiler_options.get("noEmit") is False:
        raise ConfigurationError("context-aware adapter checks require noEmit")
    settings.setdefault("strict", True)
    settings["noEmit"] = True
    settings["pretty"] = False
    original_files: list[str] | None = None
    if context.include_project_files and context.inherit_tsconfig and config.is_file():
        shown = (_runner_override.get() or run)(["--showConfig", "-p", str(config)], cwd=root)
        output = shown.stdout + shown.stderr
        if shown.returncode == 0:
            try:
                original = json.loads(shown.stdout)
                original_files = original.get("files", [])
                if not isinstance(original_files, list) or not all(
                    isinstance(v, str) for v in original_files
                ):
                    raise ValueError("files must be a list of paths")
            except (ValueError, AttributeError) as exc:
                raise ConfigurationError(f"invalid compiler showConfig response: {exc}") from exc
        elif "TS18003" in output:
            original_files = []
        else:
            return _run_tsgo_on_args(
                ["--showConfig", "-p", str(config)], cwd=root, keep_raw=keep_raw
            )
    try:
        # Nesting preserves normal ancestor node_modules lookup on every OS.
        with tempfile.TemporaryDirectory(prefix=".pytscheck-", dir=root) as directory:
            workspace = Path(directory)
            snapshot = _Snapshot(root, workspace, context)
            real = snapshot.project_files(settings.get("resolveJsonModule") is True)
            for source in sources:
                if source.path == "tsconfig.pytscheck.json" or source.path.startswith(
                    ".pytscheck-"
                ):
                    raise AdapterProtocolError(
                        "generated source uses reserved workspace metadata path"
                    )
                destination = workspace / source.path
                if (root / source.path).exists() or destination.exists():
                    raise AdapterProtocolError(
                        f"generated source conflicts with real file: {source.path}"
                    )
                snapshot.write(destination, source.text.encode("utf-8"))
            inputs = [workspace / source.path for source in sources]
            if context.include_project_files:
                if original_files is not None:
                    inputs += [
                        Path(snapshot.relocate(path, config.parent)) for path in original_files
                    ]
                else:
                    inputs += [
                        workspace / path
                        for path in real
                        if path.suffix in {".ts", ".tsx", ".mts", ".cts"} or settings.get("allowJs")
                    ]
            for field in ("rootDir", "baseUrl"):
                if isinstance(settings.get(field), str):
                    settings[field] = snapshot.relocate(settings[field], origins.get(field, root))
            for field in ("rootDirs", "typeRoots"):
                if isinstance(settings.get(field), list):
                    settings[field] = [
                        snapshot.relocate(path, origins.get(field, root))
                        for path in settings[field]
                    ]
            paths = settings.get("paths", {})
            if not isinstance(paths, dict):
                raise ConfigurationError("compiler paths must be an object")
            paths = dict(paths)
            for key, values in paths.items():
                if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                    raise ConfigurationError("compiler paths values must be lists of strings")
                paths[key] = [
                    snapshot.relocate(value, origins.get("paths", root)) for value in values
                ]
            for index, declaration in enumerate(context.declaration_paths):
                if not isinstance(declaration, (str, Path)):
                    raise ConfigurationError("declaration paths must be paths")
                path = (root / declaration).resolve()
                target = workspace / ".pytscheck-types" / str(index) / path.name
                if path.is_relative_to(root) and (workspace / path.relative_to(root)).exists():
                    target = workspace / path.relative_to(root)
                    candidates = target.rglob("*") if target.is_dir() else [target]
                    inputs.extend(
                        file
                        for file in candidates
                        if file.name.endswith((".d.ts", ".d.mts", ".d.cts"))
                    )
                else:
                    inputs.extend(snapshot.resource(path, target))
            for index, resource in enumerate(context.declaration_resources):
                if not isinstance(resource, DeclarationResource):
                    raise ConfigurationError(
                        "declaration_resources must contain DeclarationResource objects"
                    )
                if not isinstance(resource.package, str) or not resource.package:
                    raise ConfigurationError("declaration package must be a non-empty name")
                if resource.module is not None and (
                    not isinstance(resource.module, str) or not resource.module
                ):
                    raise ConfigurationError("declaration module must be a non-empty name or None")
                if not isinstance(resource.resource, str):
                    raise ConfigurationError("declaration resource must be a string")
                resource_path = PurePosixPath(resource.resource.replace("\\", "/"))
                if (
                    not resource.resource
                    or resource_path.is_absolute()
                    or PureWindowsPath(resource.resource).drive
                    or ".." in resource_path.parts
                ):
                    raise ConfigurationError("declaration resource must be package-relative")
                item = resources.files(resource.package).joinpath(resource_path.as_posix())
                target = workspace / ".pytscheck-types" / f"package-{index}"
                if item.is_file():
                    target /= item.name
                inputs.extend(snapshot.resource(item, target))
                if resource.module:
                    entry = target
                    if target.is_dir():
                        metadata = target / "package.json"
                        name = (
                            _jsonc(metadata).get("types", "index.d.ts")
                            if metadata.exists()
                            else "index.d.ts"
                        )
                        if not isinstance(name, str):
                            raise ConfigurationError("declaration package types must be a string")
                        entry = target / name
                    boundary = target if target.is_dir() else target.parent
                    if (
                        not entry.is_file()
                        or not entry.resolve().is_relative_to(boundary)
                        or not entry.name.endswith((".d.ts", ".d.mts", ".d.cts"))
                    ):
                        raise ConfigurationError("declaration module has no safe types entry")
                    paths[resource.module] = [str(entry)]
            if paths:
                settings["paths"] = paths
            generated_config = workspace / "tsconfig.pytscheck.json"
            try:
                encoded = json.dumps(
                    {
                        "compilerOptions": settings,
                        "files": list(dict.fromkeys(str(path) for path in inputs)),
                    }
                ).encode("utf-8")
            except (TypeError, ValueError) as exc:
                raise ConfigurationError(
                    f"compiler settings must be JSON-compatible: {exc}"
                ) from exc
            snapshot.write(generated_config, encoded)
            result = _run_tsgo_on_args(
                ["-p", str(generated_config)], cwd=workspace, keep_raw=keep_raw
            )

            def filename(value: str | None) -> str | None:
                if value is None:
                    return None
                path = (workspace / value).resolve()
                if path.is_relative_to(workspace):
                    return path.relative_to(workspace).as_posix()
                if path.is_relative_to(root):
                    return path.relative_to(root).as_posix()
                return value

            return replace(
                result,
                diagnostics=tuple(
                    replace(
                        d,
                        file=filename(d.file),
                        related=tuple(
                            replace(info, file=filename(info.file)) for info in d.related
                        ),
                    )
                    for d in result.diagnostics
                ),
            )
    except (OSError, UnicodeError, ModuleNotFoundError) as exc:
        raise AdapterExtractionError(f"cannot prepare adapter project: {exc}") from exc
