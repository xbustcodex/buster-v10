from pathlib import Path
import shutil

ROOT = Path(__file__).parent
WIDGET = ROOT / "buster" / "ui" / "widgets" / "ai_os_dashboard.py"
BACKUP = WIDGET.with_suffix(".py.bak_v342")

shutil.copy2(WIDGET, BACKUP)
print("backup:", BACKUP)

text = WIDGET.read_text(encoding="utf-8")

text = text.replace(
    "from buster.knowledge.semantic_graph import SemanticRepositoryGraphBuilder",
    "from buster.knowledge.semantic_graph import SemanticRepositoryGraphBuilder\nfrom buster.knowledge.knowledge_engine import RepositoryKnowledgeEngine",
)

text = text.replace(
    "        self.semantic_graph = None",
    "        self.semantic_graph = None\n        self.knowledge_engine = None",
)

text = text.replace(
    '        self._button(button_bar, "Rebuild Graph", self.rebuild_semantic_graph, "#8957e5")',
    '        self._button(button_bar, "Rebuild Graph", self.rebuild_semantic_graph, "#8957e5")\n        self._button(button_bar, "Rebuild Knowledge", self.rebuild_knowledge_engine, "#d29922")',
)

text = text.replace(
'''        self._button(graph_row, "Who Calls", self.graph_who_calls, "#8957e5")
        self._button(graph_row, "Inherits", self.graph_inherits, "#8957e5")
        self._button(graph_row, "Dependencies", self.graph_dependencies, "#8957e5")
        self._button(graph_row, "Unused Imports", self.graph_unused_imports, "#8957e5")
''',
'''        self._button(graph_row, "Who Calls", self.graph_who_calls, "#8957e5")
        self._button(graph_row, "Inherits", self.graph_inherits, "#8957e5")
        self._button(graph_row, "Dependencies", self.graph_dependencies, "#8957e5")
        self._button(graph_row, "Unused Imports", self.graph_unused_imports, "#8957e5")

        knowledge_row = tk.Frame(search, bg="#101014")
        knowledge_row.pack(fill="x", pady=6)

        self._button(knowledge_row, "Ask Knowledge", self.knowledge_ask, "#d29922")
        self._button(knowledge_row, "File Summary", self.knowledge_file_summary, "#d29922")
        self._button(knowledge_row, "Rename Impact", self.knowledge_rename_impact, "#d29922")
        self._button(knowledge_row, "Dependency Impact", self.knowledge_dependency_impact, "#d29922")
'''
)

insert_after = '''
    def rebuild_semantic_graph(self):
        self.write_output("Building semantic repository graph...")
        self.update_idletasks()

        self.semantic_graph = SemanticRepositoryGraphBuilder(self.project_root).build()

        self.write_output(
            "Semantic Repository Graph Ready\\n\\n"
            f"Calls: {len(self.semantic_graph.calls)}\\n"
            f"Inheritance links: {len(self.semantic_graph.inheritance)}\\n"
            f"Dependencies: {len(self.semantic_graph.dependencies)}\\n"
            f"Unused import hints: {len(self.semantic_graph.unused_import_hints)}\\n"
            f"Errors: {len(self.semantic_graph.errors)}"
        )

    def ensure_graph(self):
        if not self.semantic_graph:
            self.rebuild_semantic_graph()
'''

replacement = insert_after + '''

    def rebuild_knowledge_engine(self):
        self.write_output("Building repository knowledge engine...")
        self.update_idletasks()

        self.knowledge_engine = RepositoryKnowledgeEngine(self.project_root)
        self.knowledge_engine.build()
        stats = self.knowledge_engine.stats()

        self.write_output(
            "Repository Knowledge Engine Ready\\n\\n"
            f"Files: {stats.get('files', 0)}\\n"
            f"Symbols: {stats.get('symbols', 0)}\\n"
            f"Imports: {stats.get('imports', 0)}\\n"
            f"TODOs: {stats.get('todos', 0)}\\n"
            f"Calls: {stats.get('calls', 0)}\\n"
            f"Inheritance: {stats.get('inheritance', 0)}\\n"
            f"Dependencies: {stats.get('dependencies', 0)}\\n"
            f"Errors: {stats.get('errors', 0)}"
        )

    def ensure_knowledge(self):
        if not self.knowledge_engine:
            self.rebuild_knowledge_engine()

    def knowledge_ask(self):
        self.ensure_knowledge()
        query = self.query_entry.get().strip()
        if not query:
            query = "vision"
        self.write_output(self.knowledge_engine.ask(query))

    def knowledge_file_summary(self):
        self.ensure_knowledge()
        query = self.query_entry.get().strip()
        if not query:
            query = "buster\\\\vision\\\\engine.py"

        if not query.lower().startswith("summarize file "):
            query = "summarize file " + query

        self.write_output(self.knowledge_engine.ask(query))

    def knowledge_rename_impact(self):
        self.ensure_knowledge()
        query = self.query_entry.get().strip()
        if not query:
            query = "start"

        if not query.lower().startswith("rename impact "):
            query = "rename impact " + query

        self.write_output(self.knowledge_engine.ask(query))

    def knowledge_dependency_impact(self):
        self.ensure_knowledge()
        query = self.query_entry.get().strip()
        if not query:
            query = "openrouter"

        if not query.lower().startswith("what depends on "):
            query = "what depends on " + query

        self.write_output(self.knowledge_engine.ask(query))
'''

if insert_after not in text:
    raise SystemExit("Could not find semantic graph block. Patch stopped.")

text = text.replace(insert_after, replacement)

text = text.replace("BUSTER AI OS DASHBOARD v3.3.5", "BUSTER AI OS DASHBOARD v3.4.2")
text = text.replace("Buster AI OS Dashboard v3.3.5", "Buster AI OS Dashboard v3.4.2")

WIDGET.write_text(text, encoding="utf-8")
print("patched:", WIDGET)

test = ROOT / "test_v3_4_2_knowledge_engine_dashboard.py"
test.write_text(r'''
from pathlib import Path

from buster.ui.widgets.ai_os_dashboard import launch_ai_os_dashboard


if __name__ == "__main__":
    project_root = Path(__file__).parent
    launch_ai_os_dashboard(project_root)
'''.strip() + "\n", encoding="utf-8")

print("wrote:", test)

bat = ROOT / "scripts" / "run_ai_os_dashboard_v3_4_2.bat"
bat.parent.mkdir(parents=True, exist_ok=True)
bat.write_text(r'''
@echo off
cd /d "%~dp0\.."
python test_v3_4_2_knowledge_engine_dashboard.py
pause
'''.strip() + "\n", encoding="utf-8")

print("wrote:", bat)

print()
print("Buster v3.4.2 Knowledge Engine Dashboard patch complete.")
print("Run:")
print("python test_v3_4_2_knowledge_engine_dashboard.py")