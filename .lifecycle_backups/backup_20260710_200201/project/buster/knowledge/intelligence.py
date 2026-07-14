from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Symbol:
    name: str
    kind: str
    file: str
    line: int


@dataclass
class ImportItem:
    module: str
    name: str
    file: str
    line: int


@dataclass
class TodoItem:
    text: str
    file: str
    line: int


@dataclass
class FileInfo:
    file: str
    size: int
    lines: int


@dataclass
class RepositoryIntelligence:
    root: str
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[ImportItem] = field(default_factory=list)
    todos: list[TodoItem] = field(default_factory=list)
    largest_files: list[FileInfo] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def find_symbols(self, query: str) -> list[Symbol]:
        q = query.lower()
        return [s for s in self.symbols if q in s.name.lower() or q in s.file.lower()]

    def find_imports(self, query: str) -> list[ImportItem]:
        q = query.lower()
        return [i for i in self.imports if q in i.module.lower() or q in i.name.lower() or q in i.file.lower()]

    def find_todos(self, query: str = "") -> list[TodoItem]:
        q = query.lower()
        if not q:
            return self.todos
        return [t for t in self.todos if q in t.text.lower() or q in t.file.lower()]

    def ask(self, question: str) -> str:
        q = question.lower().strip()

        if "vision engine" in q:
            matches = [
                s for s in self.symbols
                if "buster\\vision\\engine.py" in s.file.replace("/", "\\").lower()
                and ("VisionEngine" in s.name or s.kind in ("class", "method"))
            ]
            return self._format_matches(matches[:20], "Vision engine")

        if q.startswith("where is "):
            target = q.replace("where is ", "").strip(" ?")
            return self._where_text(target)

        if "openrouter" in q:
            matches = self.find_imports("openrouter") + self.find_symbols("openrouter")
            return self._format_matches(matches, "OpenRouter matches")

        if "todo" in q:
            return self._format_matches(self.todos[:30], "TODOs")

        if "test" in q:
            return "Test files:\n" + "\n".join(f"- {x}" for x in self.test_files[:50])

        return self._where_text(question)

    def _where_file_or_symbol(self, *parts: str) -> str:
        terms = [p.lower() for p in parts]
        matches = []

        for s in self.symbols:
            hay = (s.name + " " + s.file).lower()
            if all(t in hay for t in terms):
                matches.append(s)

        if matches:
            return self._format_matches(matches, "Matches")

        return self._where_text(" ".join(parts))

    def _where_text(self, text: str) -> str:
        q = text.lower()
        matches = []

        for s in self.symbols:
            if q in s.name.lower() or q in s.file.lower():
                matches.append(s)

        for i in self.imports:
            if q in i.module.lower() or q in i.name.lower() or q in i.file.lower():
                matches.append(i)

        for f in self.largest_files:
            if q in f.file.lower():
                matches.append(f)

        if not matches:
            return f"No matches found for: {text}"

        return self._format_matches(matches[:40], f"Matches for {text}")

    def _format_matches(self, matches, title: str) -> str:
        if not matches:
            return f"{title}: none"

        lines = [title + ":"]
        for m in matches:
            if isinstance(m, Symbol):
                lines.append(f"- {m.kind}: {m.name}  ({m.file}:{m.line})")
            elif isinstance(m, ImportItem):
                lines.append(f"- import: {m.module}.{m.name}  ({m.file}:{m.line})")
            elif isinstance(m, TodoItem):
                lines.append(f"- TODO: {m.text}  ({m.file}:{m.line})")
            elif isinstance(m, FileInfo):
                lines.append(f"- file: {m.file}  {m.lines} lines  {m.size} bytes")
            else:
                lines.append(f"- {m}")
        return "\n".join(lines)


class RepositoryIntelligenceBuilder:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.ignore_dirs = {
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "env",
            "models",
        }
        self.ignore_suffixes = {
            ".pyc",
            ".pyo",
            ".pt",
            ".onnx",
            ".db",
            ".sqlite",
            ".sqlite3",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".mp4",
            ".avi",
            ".zip",
        }

    def _should_ignore(self, path: Path) -> bool:
        rel_parts = path.relative_to(self.root).parts

        if any(part in self.ignore_dirs for part in rel_parts):
            return True

        if path.suffix.lower() in self.ignore_suffixes:
            return True

        # Ignore old nested duplicate copy of the project.
        if rel_parts and rel_parts[0] == self.root.name:
            return True

        # Patch scripts are useful, but should not pollute repository intelligence.
        if path.name.startswith("apply_v") and path.suffix == ".py":
            return True

        return False

    def build(self) -> RepositoryIntelligence:
        intel = RepositoryIntelligence(root=str(self.root))
        file_infos = []

        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            if self._should_ignore(path):
                continue

            rel = str(path.relative_to(self.root))

            try:
                size = path.stat().st_size
                text = path.read_text(encoding="utf-8", errors="ignore")
                lines = text.splitlines()
                file_infos.append(FileInfo(rel, size, len(lines)))

                if path.name.startswith("test_") or path.name.endswith("_test.py") or "tests" in path.parts:
                    if path.suffix == ".py":
                        intel.test_files.append(rel)

                for n, line in enumerate(lines, start=1):
                    low = line.lower()
                    if "todo" in low or "fixme" in low:
                        intel.todos.append(TodoItem(line.strip(), rel, n))

                if path.suffix == ".py":
                    self._scan_python(path, rel, text, intel)

            except Exception as e:
                intel.errors.append(f"{rel}: {e}")

        intel.symbols = self._dedupe(intel.symbols)
        intel.imports = self._dedupe(intel.imports)
        intel.todos = self._dedupe(intel.todos)
        intel.test_files = sorted(set(intel.test_files))
        intel.largest_files = sorted(file_infos, key=lambda x: x.size, reverse=True)[:30]
        return intel

    def _dedupe(self, items):
        seen = set()
        clean = []

        for item in items:
            key = tuple(sorted(item.__dict__.items()))
            if key in seen:
                continue
            seen.add(key)
            clean.append(item)

        return clean

    def _scan_python(self, path: Path, rel: str, text: str, intel: RepositoryIntelligence):
        try:
            tree = ast.parse(text)
        except Exception as e:
            intel.errors.append(f"{rel}: AST parse failed: {e}")
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                intel.symbols.append(Symbol(node.name, "class", rel, node.lineno))

                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        intel.symbols.append(Symbol(f"{node.name}.{item.name}", "method", rel, item.lineno))

            elif isinstance(node, ast.FunctionDef):
                intel.symbols.append(Symbol(node.name, "function", rel, node.lineno))

            elif isinstance(node, ast.AsyncFunctionDef):
                intel.symbols.append(Symbol(node.name, "async_function", rel, node.lineno))

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    intel.imports.append(ImportItem(alias.name, alias.asname or alias.name, rel, node.lineno))

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    intel.imports.append(ImportItem(module, alias.name, rel, node.lineno))
