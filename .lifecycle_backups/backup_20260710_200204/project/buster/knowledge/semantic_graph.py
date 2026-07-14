from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CallEdge:
    caller: str
    callee: str
    file: str
    line: int


@dataclass
class InheritanceEdge:
    child: str
    parent: str
    file: str
    line: int


@dataclass
class DependencyEdge:
    file: str
    module: str
    line: int


@dataclass
class SemanticRepositoryGraph:
    root: str
    calls: list[CallEdge] = field(default_factory=list)
    inheritance: list[InheritanceEdge] = field(default_factory=list)
    dependencies: list[DependencyEdge] = field(default_factory=list)
    unused_import_hints: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def who_calls(self, name: str, exact: bool = False) -> list[CallEdge]:
        query = name.strip().lower()

        if not query:
            return []

        results = []

        for call in self.calls:
            callee = call.callee.lower()

            if exact:
                if callee == query:
                    results.append(call)
                continue

            # Specific dotted search: VisionEngine.start, self.timer.start, thread.start
            if "." in query:
                if callee == query or callee.endswith("." + query):
                    results.append(call)
                continue

            # Simple method search: start should match .start or start, not startswith
            last_part = callee.split(".")[-1]
            if last_part == query:
                results.append(call)

        return results

    def inherits_from(self, name: str) -> list[InheritanceEdge]:
        q = name.lower().strip()
        return [
            i for i in self.inheritance
            if i.parent.lower() == q
            or i.parent.lower().endswith("." + q)
            or q in i.parent.lower()
        ]

    def depends_on(self, name: str) -> list[DependencyEdge]:
        q = name.lower().strip()
        return [d for d in self.dependencies if q in d.module.lower()]

    def dependencies_for_file(self, file_query: str) -> list[DependencyEdge]:
        q = file_query.lower().replace("/", "\\")
        return [d for d in self.dependencies if q in d.file.lower().replace("/", "\\")]

    def ask(self, question: str) -> str:
        q = question.lower().strip()

        if q.startswith("who calls "):
            target = question[len("who calls "):].strip(" ?")
            calls = self.who_calls(target)
            return self.format_calls(calls, f"Who calls {target}")

        if q.startswith("exact calls "):
            target = question[len("exact calls "):].strip(" ?")
            calls = self.who_calls(target, exact=True)
            return self.format_calls(calls, f"Exact calls {target}")

        if "classes inherit" in q or "inherits from" in q:
            target = (
                q.replace("which classes inherit", "")
                 .replace("what classes inherit", "")
                 .replace("inherits from", "")
                 .strip(" ?")
            )
            return self.format_inheritance(self.inherits_from(target), f"Classes inheriting {target}")

        if q.startswith("dependencies for "):
            target = question[len("dependencies for "):].strip(" ?")
            return self.format_dependencies(
                self.dependencies_for_file(target),
                f"Dependencies for file {target}",
            )

        if "depend on" in q:
            target = (
                q.replace("which modules depend on", "")
                 .replace("what modules depend on", "")
                 .replace("depends on", "")
                 .strip(" ?")
            )
            return self.format_dependencies(self.depends_on(target), f"Dependencies for {target}")

        if "unused import" in q:
            return "Unused import hints:\n" + "\n".join(f"- {x}" for x in self.unused_import_hints[:80])

        return (
            "Graph commands:\n"
            "- Who calls VisionEngine.start?\n"
            "- Who calls start?\n"
            "- Exact calls self.timer.start\n"
            "- Which classes inherit Agent?\n"
            "- Which modules depend on OpenRouter?\n"
            "- Dependencies for buster\\vision\\engine.py\n"
            "- Show unused imports"
        )

    def format_calls(self, calls, title):
        if not calls:
            return title + ": none"

        lines = [title + ":"]
        for c in calls[:80]:
            lines.append(f"- {c.caller} -> {c.callee} ({c.file}:{c.line})")
        return "\n".join(lines)

    def format_inheritance(self, items, title):
        if not items:
            return title + ": none"

        lines = [title + ":"]
        for i in items[:80]:
            lines.append(f"- {i.child} inherits {i.parent} ({i.file}:{i.line})")
        return "\n".join(lines)

    def format_dependencies(self, items, title):
        if not items:
            return title + ": none"

        lines = [title + ":"]
        for d in items[:80]:
            lines.append(f"- {d.file} imports {d.module} ({d.line})")
        return "\n".join(lines)


class SemanticRepositoryGraphBuilder:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.ignore_dirs = {
            "__pycache__", ".git", ".venv", "venv", "env", "models",
        }
        self.ignore_suffixes = {
            ".pyc", ".pyo", ".pt", ".onnx", ".db", ".sqlite", ".sqlite3",
            ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".avi", ".zip",
        }

    def _should_ignore(self, path: Path) -> bool:
        rel_parts = path.relative_to(self.root).parts

        if any(part in self.ignore_dirs for part in rel_parts):
            return True

        if path.suffix.lower() in self.ignore_suffixes:
            return True

        if rel_parts and rel_parts[0] == self.root.name:
            return True

        if path.name.startswith("apply_v") and path.suffix == ".py":
            return True

        if ".bak" in path.name:
            return True

        return False

    def build(self) -> SemanticRepositoryGraph:
        graph = SemanticRepositoryGraph(root=str(self.root))

        for path in self.root.rglob("*.py"):
            if self._should_ignore(path):
                continue

            rel = str(path.relative_to(self.root))

            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(text)
                self._scan_file(tree, rel, text, graph)
            except Exception as e:
                graph.errors.append(f"{rel}: {e}")

        graph.calls = self._dedupe(graph.calls)
        graph.inheritance = self._dedupe(graph.inheritance)
        graph.dependencies = self._dedupe(graph.dependencies)
        graph.unused_import_hints = sorted(set(graph.unused_import_hints))

        return graph

    def _scan_file(self, tree: ast.AST, rel: str, text: str, graph: SemanticRepositoryGraph):
        imported_names = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    imported_names[name] = (alias.name, node.lineno)
                    graph.dependencies.append(DependencyEdge(rel, alias.name, node.lineno))

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                graph.dependencies.append(DependencyEdge(rel, module, node.lineno))
                for alias in node.names:
                    name = alias.asname or alias.name
                    imported_names[name] = (f"{module}.{alias.name}", node.lineno)

        used_names = {
            n.id for n in ast.walk(tree)
            if isinstance(n, ast.Name)
        }

        for local_name, (full_name, line) in imported_names.items():
            if local_name not in used_names and local_name != "*":
                if full_name == "__future__.annotations":
                    continue
                graph.unused_import_hints.append(f"{rel}:{line} possible unused import {full_name}")

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    graph.inheritance.append(
                        InheritanceEdge(
                            child=node.name,
                            parent=self._expr_name(base),
                            file=rel,
                            line=node.lineno,
                        )
                    )

        visitor = _CallVisitor(rel)
        visitor.visit(tree)
        graph.calls.extend(visitor.calls)

    def _expr_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = self._expr_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        if isinstance(node, ast.Subscript):
            return self._expr_name(node.value)
        if isinstance(node, ast.Call):
            return self._expr_name(node.func)
        return type(node).__name__

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


class _CallVisitor(ast.NodeVisitor):
    def __init__(self, rel: str):
        self.rel = rel
        self.scope = ["<module>"]
        self.calls: list[CallEdge] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Call(self, node: ast.Call):
        caller = ".".join([x for x in self.scope if x != "<module>"]) or "<module>"
        callee = self._call_name(node.func)
        self.calls.append(CallEdge(caller, callee, self.rel, node.lineno))
        self.generic_visit(node)

    def _call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = self._call_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        if isinstance(node, ast.Call):
            return self._call_name(node.func)
        return type(node).__name__
