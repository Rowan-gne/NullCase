"""Import graph of a repository, built with ``ast``."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

SKIP_DIRS = frozenset(
    {".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist", "site-packages"}
)


@dataclass(frozen=True, slots=True)
class ModuleInfo:
    path: Path  # relative to the repository root
    name: str  # dotted module name
    imports: frozenset[str]  # absolute dotted names this module imports

    @property
    def is_test(self) -> bool:
        return self.path.name.startswith("test_") or self.path.name.endswith("_test.py")


def module_name(path: Path) -> str:
    """Dotted name for a file, following ``__init__.py`` files up to the package root.

    Works for flat and ``src/`` layouts. A file outside any package (such as a
    rootdir-style test file) is named by its stem.
    """
    parts = [] if path.name == "__init__.py" else [path.stem]
    directory = path.parent
    while (directory / "__init__.py").is_file():
        parts.insert(0, directory.name)
        directory = directory.parent
    return ".".join(parts)


def imports_of(tree: ast.Module, name: str, is_package: bool) -> frozenset[str]:
    """Absolute module names imported by a module, with relative imports resolved.

    ``from a import b`` records both ``a`` and ``a.b``, since ``b`` may be a submodule.
    """
    package = name if is_package else name.rpartition(".")[0]
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base_parts = package.split(".") if package else []
                if node.level - 1 > len(base_parts):
                    continue  # relative import beyond the top-level package
                base_parts = base_parts[: len(base_parts) - (node.level - 1)]
                base = ".".join([*base_parts, *([node.module] if node.module else [])])
            else:
                base = node.module or ""
            if base:
                found.add(base)
            found.update(f"{base}.{a.name}" if base else a.name for a in node.names)
    found.discard("")
    return frozenset(found)


def python_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if not any(part in SKIP_DIRS or part.startswith(".") for part in relative.parts[:-1]):
            yield path


@dataclass(frozen=True, slots=True)
class ImportGraph:
    root: Path
    modules: tuple[ModuleInfo, ...]

    @classmethod
    def build(cls, root: Path) -> ImportGraph:
        modules: list[ModuleInfo] = []
        for path in python_files(root):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeDecodeError):
                continue  # not our job to report unparseable files
            name = module_name(path)
            is_package = path.name == "__init__.py"
            modules.append(
                ModuleInfo(path.relative_to(root), name, imports_of(tree, name, is_package))
            )
        return cls(root, tuple(modules))

    def importers_of(self, target: str) -> list[ModuleInfo]:
        """Modules that import ``target`` or one of its submodules."""
        prefix = target + "."
        return [
            m
            for m in self.modules
            if m.name != target and any(i == target or i.startswith(prefix) for i in m.imports)
        ]
