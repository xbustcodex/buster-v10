from pathlib import Path
import shutil

ROOT = Path(__file__).parent
WIDGET = ROOT / "buster" / "ui" / "widgets" / "ai_os_dashboard.py"
BACKUP = WIDGET.with_suffix(".py.bak_v335")

shutil.copy2(WIDGET, BACKUP)
print("backup:", BACKUP)

text = WIDGET.read_text(encoding="utf-8")

text = text.replace(
    "from buster.knowledge.intelligence import RepositoryIntelligenceBuilder",
    "from buster.knowledge.intelligence import RepositoryIntelligenceBuilder\nfrom buster.knowledge.semantic_graph import SemanticRepositoryGraphBuilder",
)

text = text.replace(
    "        self.repo_intel = None",
    "        self.repo_intel = None\n        self.semantic_graph = None",
)

text = text.replace(
    '        self._button(button_bar, "Rebuild Repository Intel", self.rebuild_repository_intelligence, "#238636")',
    '        self._button(button_bar, "Rebuild Repository Intel", self.rebuild_repository_intelligence, "#238636")\n        self._button(button_bar, "Rebuild Graph", self.rebuild_semantic_graph, "#8957e5")',
)

text = text.replace(
'''        self._button(quick, "Largest Files", self.show_largest_files, "#30363d")
        self._button(quick, "TODOs", self.show_todos, "#30363d")
        self._button(quick, "Symbols", self.show_symbols, "#30363d")
        self._button(quick, "Tests", self.show_tests, "#30363d")
''',
'''        self._button(quick, "Largest Files", self.show_largest_files, "#30363d")
        self._button(quick, "TODOs", self.show_todos, "#30363d")
        self._button(quick, "Symbols", self.show_symbols, "#30363d")
        self._button(quick, "Tests", self.show_tests, "#30363d")

        graph_row = tk.Frame(search, bg="#101014")
        graph_row.pack(fill="x", pady=6)

        self._button(graph_row, "Who Calls", self.graph_who_calls, "#8957e5")
        self._button(graph_row, "Inherits", self.graph_inherits, "#8957e5")
        self._button(graph_row, "Dependencies", self.graph_dependencies, "#8957e5")
        self._button(graph_row, "Unused Imports", self.graph_unused_imports, "#8957e5")
'''
)

insert_after = '''
    def rebuild_repository_intelligence(self):
        self.write_output("Building repository intelligence...")
        self.update_idletasks()

        self.repo_intel = RepositoryIntelligenceBuilder(self.project_root).build()

        self.write_output(
            "Repository Intelligence Ready\\n\\n"
            f"Symbols: {len(self.repo_intel.symbols)}\\n"
            f"Imports: {len(self.repo_intel.imports)}\\n"
            f"TODOs: {len(self.repo_intel.todos)}\\n"
            f"Largest files indexed: {len(self.repo_intel.largest_files)}\\n"
            f"Test files: {len(self.repo_intel.test_files)}\\n"
            f"Errors: {len(self.repo_intel.errors)}"
        )
'''

replacement = insert_after + '''

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

    def graph_who_calls(self):
        self.ensure_graph()
        query = self.query_entry.get().strip()
        if not query:
            query = "start"
        if query.lower().startswith("who calls "):
            question = query
        else:
            question = "Who calls " + query
        self.write_output(self.semantic_graph.ask(question))

    def graph_inherits(self):
        self.ensure_graph()
        query = self.query_entry.get().strip()
        if not query:
            query = "Agent"
        if "inherit" in query.lower():
            question = query
        else:
            question = "Which classes inherit " + query
        self.write_output(self.semantic_graph.ask(question))

    def graph_dependencies(self):
        self.ensure_graph()
        query = self.query_entry.get().strip()
        if not query:
            query = "buster\\\\vision\\\\engine.py"

        if "\\\\" in query or "/" in query or query.endswith(".py"):
            question = "Dependencies for " + query
        elif "depend" in query.lower():
            question = query
        else:
            question = "Which modules depend on " + query

        self.write_output(self.semantic_graph.ask(question))

    def graph_unused_imports(self):
        self.ensure_graph()
        self.write_output(self.semantic_graph.ask("Show unused imports"))
'''

if insert_after not in text:
    raise SystemExit("Could not find rebuild_repository_intelligence block. Patch stopped.")

text = text.replace(insert_after, replacement)

text = text.replace(
    'root.title("Buster AI OS Dashboard v3.3.2")',
    'root.title("Buster AI OS Dashboard v3.3.5")',
)

text = text.replace(
    'text="BUSTER AI OS DASHBOARD v3.3.2"',
    'text="BUSTER AI OS DASHBOARD v3.3.5"',
)

WIDGET.write_text(text, encoding="utf-8")
print("patched:", WIDGET)

test = ROOT / "test_v3_3_5_graph_search_dashboard.py"
test.write_text(r'''
from pathlib import Path

from buster.ui.widgets.ai_os_dashboard import launch_ai_os_dashboard


if __name__ == "__main__":
    project_root = Path(__file__).parent
    launch_ai_os_dashboard(project_root)
'''.strip() + "\n", encoding="utf-8")

print("wrote:", test)

bat = ROOT / "scripts" / "run_ai_os_dashboard_v3_3_5.bat"
bat.parent.mkdir(parents=True, exist_ok=True)
bat.write_text(r'''
@echo off
cd /d "%~dp0\.."
python test_v3_3_5_graph_search_dashboard.py
pause
'''.strip() + "\n", encoding="utf-8")

print("wrote:", bat)

print()
print("Buster v3.3.5 Graph Search Dashboard patch complete.")
print("Run:")
print("python test_v3_3_5_graph_search_dashboard.py")