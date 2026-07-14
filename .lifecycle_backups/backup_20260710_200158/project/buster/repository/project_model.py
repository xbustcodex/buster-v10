from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProjectModel:
    root: str
    files: int = 0
    python_files: int = 0
    classes: int = 0
    functions: int = 0
    imports: int = 0
    todos: int = 0
    errors: int = 0


class ProjectAnalyzer:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def analyze(self) -> ProjectModel:
        model = ProjectModel(root=str(self.root))

        for path in self.root.rglob("*"):
            if "__pycache__" in path.parts:
                continue

            if path.is_file():
                model.files += 1

            if path.suffix == ".py":
                model.python_files += 1
                self._scan_python(path, model)

        return model

    def _scan_python(self, path: Path, model: ProjectModel):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            model.todos += text.lower().count("todo")
            tree = ast.parse(text)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    model.classes += 1
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    model.functions += 1
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    model.imports += 1

        except Exception:
            model.errors += 1
