from pathlib import Path

ROOT = Path(__file__).parent
BUSTER = ROOT / "buster"

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    print("wrote:", path)

write(BUSTER / "repository" / "knowledge_engine.py", r'''
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from buster.knowledge.intelligence import RepositoryIntelligenceBuilder
from buster.knowledge.semantic_graph import SemanticRepositoryGraphBuilder


@dataclass
class FileKnowledge:
    file: str
    symbols: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)


@dataclass
class RepositoryKnowledge:
    root: str
    files: dict[str, FileKnowledge] = field(default_factory=dict)
    answers: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class RepositoryKnowledgeEngine:
    """
    Shared repository brain for Planner, Builder, Tester, Reviewer, Fixer,
    Verifier, Vision, Memory, and future autonomous agents.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.intel = None
        self.graph = None
        self.knowledge = RepositoryKnowledge(root=str(self.root))

    def build(self) -> RepositoryKnowledge:
        self.intel = RepositoryIntelligenceBuilder(self.root).build()
        self.graph = SemanticRepositoryGraphBuilder(self.root).build()

        self.knowledge = RepositoryKnowledge(
            root=str(self.root),
            errors=list(self.intel.errors) + list(self.graph.errors),
        )

        self._build_file_knowledge()
        return self.knowledge

    def _file(self, file: str) -> FileKnowledge:
        if file not in self.knowledge.files:
            self.knowledge.files[file] = FileKnowledge(file=file)
        return self.knowledge.files[file]

    def _build_file_knowledge(self):
        for symbol in self.intel.symbols:
            fk = self._file(symbol.file)
            fk.symbols.append(f"{symbol.kind}: {symbol.name}:{symbol.line}")

        for imp in self.intel.imports:
            fk = self._file(imp.file)
            fk.imports.append(f"{imp.module}.{imp.name}:{imp.line}")

        for todo in self.intel.todos:
            fk = self._file(todo.file)
            fk.todos.append(f"{todo.line}: {todo.text}")

        for dep in self.graph.dependencies:
            fk = self._file(dep.file)
            fk.dependencies.append(f"{dep.module}:{dep.line}")

        for call in self.graph.calls:
            fk = self._file(call.file)
            fk.calls.append(f"{call.caller} -> {call.callee}:{call.line}")

    def ask(self, question: str) -> str:
        if self.intel is None or self.graph is None:
            self.build()

        q = question.lower().strip()

        if q.startswith("summarize file "):
            target = question[len("summarize file "):].strip(" ?")
            return self.summarize_file(target)

        if q.startswith("what depends on "):
            target = question[len("what depends on "):].strip(" ?")
            return self.what_depends_on(target)

        if q.startswith("rename impact "):
            target = question[len("rename impact "):].strip(" ?")
            return self.rename_impact(target)

        if q.startswith("who calls "):
            return self.graph.ask(question)

        if "inherit" in q:
            return self.graph.ask(question)

        if "todo" in q:
            return self.list_todos()

        if "openrouter" in q:
            return self.what_depends_on("openrouter")

        if "vision" in q:
            return self.summarize_file("buster\\vision\\engine.py")

        return self.search(question)

    def summarize_file(self, file_query: str) -> str:
        match = self._find_file(file_query)
        if not match:
            return f"No file found for: {file_query}"

        fk = self.knowledge.files[match]

        lines = [f"File summary: {fk.file}"]
        lines.append("")
        lines.append(f"Symbols: {len(fk.symbols)}")
        for item in fk.symbols[:30]:
            lines.append(f"- {item}")

        lines.append("")
        lines.append(f"Imports: {len(fk.imports)}")
        for item in fk.imports[:30]:
            lines.append(f"- {item}")

        lines.append("")
        lines.append(f"Calls: {len(fk.calls)}")
        for item in fk.calls[:30]:
            lines.append(f"- {item}")

        if fk.todos:
            lines.append("")
            lines.append(f"TODOs: {len(fk.todos)}")
            for item in fk.todos[:30]:
                lines.append(f"- {item}")

        return "\n".join(lines)

    def what_depends_on(self, target: str) -> str:
        q = target.lower()
        matches = []

        for dep in self.graph.dependencies:
            if q in dep.module.lower():
                matches.append(f"- {dep.file} imports {dep.module} ({dep.line})")

        for imp in self.intel.imports:
            if q in imp.module.lower() or q in imp.name.lower():
                item = f"- {imp.file} imports {imp.module}.{imp.name} ({imp.line})"
                if item not in matches:
                    matches.append(item)

        if not matches:
            return f"No dependencies found for: {target}"

        return "Dependencies for " + target + ":\n" + "\n".join(matches[:100])

    def rename_impact(self, target: str) -> str:
        symbol_matches = self.intel.find_symbols(target)
        call_matches = self.graph.who_calls(target)
        import_matches = self.intel.find_imports(target)

        lines = [f"Rename impact: {target}", ""]

        lines.append(f"Matching symbols: {len(symbol_matches)}")
        for s in symbol_matches[:40]:
            lines.append(f"- {s.kind}: {s.name} ({s.file}:{s.line})")

        lines.append("")
        lines.append(f"Call sites: {len(call_matches)}")
        for c in call_matches[:40]:
            lines.append(f"- {c.caller} -> {c.callee} ({c.file}:{c.line})")

        lines.append("")
        lines.append(f"Import references: {len(import_matches)}")
        for i in import_matches[:40]:
            lines.append(f"- {i.file} imports {i.module}.{i.name} ({i.line})")

        if not symbol_matches and not call_matches and not import_matches:
            lines.append("")
            lines.append("No direct rename impact found.")

        return "\n".join(lines)

    def list_todos(self) -> str:
        todos = self.intel.todos[:100]
        if not todos:
            return "No TODOs found."

        lines = ["Repository TODOs:"]
        for todo in todos:
            lines.append(f"- {todo.file}:{todo.line} | {todo.text}")
        return "\n".join(lines)

    def search(self, query: str) -> str:
        symbols = self.intel.find_symbols(query)
        imports = self.intel.find_imports(query)
        todos = self.intel.find_todos(query)

        lines = [f"Knowledge search: {query}", ""]

        lines.append(f"Symbols: {len(symbols)}")
        for s in symbols[:30]:
            lines.append(f"- {s.kind}: {s.name} ({s.file}:{s.line})")

        lines.append("")
        lines.append(f"Imports: {len(imports)}")
        for i in imports[:30]:
            lines.append(f"- {i.file} imports {i.module}.{i.name} ({i.line})")

        lines.append("")
        lines.append(f"TODOs: {len(todos)}")
        for t in todos[:30]:
            lines.append(f"- {t.file}:{t.line} | {t.text}")

        return "\n".join(lines)

    def _find_file(self, file_query: str) -> str | None:
        q = file_query.lower().replace("/", "\\")
        files = list(self.knowledge.files.keys())

        for f in files:
            if f.lower().replace("/", "\\") == q:
                return f

        for f in files:
            if q in f.lower().replace("/", "\\"):
                return f

        return None

    def stats(self) -> dict:
        if self.intel is None or self.graph is None:
            self.build()

        return {
            "files": len(self.knowledge.files),
            "symbols": len(self.intel.symbols),
            "imports": len(self.intel.imports),
            "todos": len(self.intel.todos),
            "calls": len(self.graph.calls),
            "inheritance": len(self.graph.inheritance),
            "dependencies": len(self.graph.dependencies),
            "errors": len(self.knowledge.errors),
        }
''')

write(ROOT / "test_v3_4_repository_knowledge_engine.py", r'''
from pathlib import Path

from buster.knowledge.knowledge_engine import RepositoryKnowledgeEngine


def main():
    root = Path(__file__).parent
    engine = RepositoryKnowledgeEngine(root)
    knowledge = engine.build()

    print("=== Buster v3.4 Repository Knowledge Engine Test ===")
    print("Stats:")
    for k, v in engine.stats().items():
        print(f"{k}: {v}")

    print()
    print('Ask: "summarize file buster\\vision\\engine.py"')
    print(engine.ask("summarize file buster\\vision\\engine.py"))

    print()
    print('Ask: "what depends on openrouter"')
    print(engine.ask("what depends on openrouter"))

    print()
    print('Ask: "rename impact start"')
    print(engine.ask("rename impact start"))

    print()
    print('Ask: "Which classes inherit Agent?"')
    print(engine.ask("Which classes inherit Agent?"))

    print()
    print("SUCCESS: v3.4 Repository Knowledge Engine installed.")


if __name__ == "__main__":
    main()
''')

print()
print("Buster v3.4 Repository Knowledge Engine patch complete.")
print("Run:")
print("python test_v3_4_repository_knowledge_engine.py")