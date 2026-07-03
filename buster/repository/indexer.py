import ast
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class SymbolInfo:
    name: str
    kind: str
    file: str
    line: int

@dataclass
class RepoIndex:
    root: str = ""
    files: list = field(default_factory=list)
    python_files: list = field(default_factory=list)
    classes: list = field(default_factory=list)
    functions: list = field(default_factory=list)
    imports: dict = field(default_factory=dict)
    todos: list = field(default_factory=list)
    largest: list = field(default_factory=list)

class RepositoryIndexer:
    def __init__(self, default_root="."):
        self.default_root = Path(default_root)
        self.index = RepoIndex(root=str(self.default_root.resolve()))
        self.last_error = ""

    def build(self, root_path="."):
        root = Path(root_path or ".").resolve()
        if not root.exists():
            return f"Project path not found: {root}"
        self.index = RepoIndex(root=str(root))
        skip_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build", ".idea", ".gradle"}
        sizes = []
        for path in root.rglob("*"):
            if any(part in skip_dirs for part in path.parts):
                continue
            if path.is_file():
                rel = str(path.relative_to(root))
                self.index.files.append(rel)
                try: sizes.append((rel, path.stat().st_size))
                except Exception: pass
                if path.suffix.lower() == ".py":
                    self.index.python_files.append(rel)
                    self._scan_python(path, rel)
                if path.suffix.lower() in [".py", ".md", ".txt", ".json", ".yml", ".yaml", ".toml"]:
                    self._scan_todos(path, rel)
        self.index.largest = sorted(sizes, key=lambda x: x[1], reverse=True)[:20]
        return f"Project indexed.\nRoot: {self.index.root}\nFiles: {len(self.index.files)}\nPython files: {len(self.index.python_files)}\nClasses: {len(self.index.classes)}\nFunctions: {len(self.index.functions)}\nTODOs: {len(self.index.todos)}"

    def _scan_python(self, path, rel):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception as exc:
            self.last_error = str(exc)
            return
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self.index.classes.append(SymbolInfo(node.name, "class", rel, node.lineno))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.index.functions.append(SymbolInfo(node.name, "function", rel, node.lineno))
            elif isinstance(node, ast.Import):
                imports += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        if imports:
            self.index.imports[rel] = imports

    def _scan_todos(self, path, rel):
        try:
            for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if "todo" in line.lower() or "fixme" in line.lower():
                    self.index.todos.append(f"{rel}:{i}: {line.strip()[:160]}")
        except Exception:
            pass

    def status(self):
        return f"Repo root: {self.index.root}\nFiles: {len(self.index.files)}\nPython files: {len(self.index.python_files)}\nClasses: {len(self.index.classes)}\nFunctions: {len(self.index.functions)}\nTODOs: {len(self.index.todos)}"

    def find_symbol(self, name):
        q = name.lower()
        matches = [f"{x.kind} {x.name} - {x.file}:{x.line}" for x in self.index.classes + self.index.functions if q in x.name.lower()]
        return "\n".join(matches[:30]) if matches else f"No symbol found matching {name}."

    def where_is(self, query):
        q = query.lower()
        matches = []
        for rel in self.index.files:
            if q in rel.lower(): matches.append(f"file - {rel}")
        for x in self.index.classes + self.index.functions:
            if q in x.name.lower() or q in x.file.lower(): matches.append(f"{x.kind} {x.name} - {x.file}:{x.line}")
        for rel, imports in self.index.imports.items():
            if any(q in imp.lower() for imp in imports):
                matches.append(f"import in {rel}: " + ", ".join(imports[:12]))
        return "\n".join(matches[:40]) if matches else f"I could not find {query} in the current index. Try: index project"

    def todos(self):
        return "\n".join(self.index.todos[:40]) if self.index.todos else "No TODO or FIXME items found."

    def largest_files(self):
        return "\n".join([f"{rel} - {size} bytes" for rel, size in self.index.largest[:20]]) if self.index.largest else "No files indexed yet."
