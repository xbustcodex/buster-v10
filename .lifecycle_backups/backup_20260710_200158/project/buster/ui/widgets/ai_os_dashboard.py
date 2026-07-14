from __future__ import annotations

import tkinter as tk
from pathlib import Path

from buster.workspace.ai_os import AIOSCore
from buster.knowledge.intelligence import RepositoryIntelligenceBuilder
from buster.knowledge.semantic_graph import SemanticRepositoryGraphBuilder
from buster.knowledge.knowledge_engine import RepositoryKnowledgeEngine


class AIOSDashboard(tk.Frame):
    def __init__(self, master, project_root: str | Path):
        super().__init__(master, bg="#101014")
        self.project_root = Path(project_root)
        self.ai_os = AIOSCore(self.project_root)
        self.repo_intel = None
        self.semantic_graph = None
        self.knowledge_engine = None

        self.stat_vars = {}
        self.job_list = None
        self.query_entry = None
        self.output = None

        self._build_ui()
        self.rebuild_repository_intelligence()
        self.refresh()

    def _build_ui(self):
        title = tk.Label(
            self,
            text="BUSTER AI OS DASHBOARD v3.4.2",
            bg="#101014",
            fg="#00ff99",
            font=("Segoe UI", 16, "bold"),
        )
        title.pack(pady=8)

        button_bar = tk.Frame(self, bg="#101014")
        button_bar.pack(fill="x", padx=10, pady=4)

        self._button(button_bar, "Rebuild Project Model", self.rebuild_project_model, "#1f6feb")
        self._button(button_bar, "Rebuild Repository Intel", self.rebuild_repository_intelligence, "#238636")
        self._button(button_bar, "Rebuild Graph", self.rebuild_semantic_graph, "#8957e5")
        self._button(button_bar, "Rebuild Knowledge", self.rebuild_knowledge_engine, "#d29922")
        self._button(button_bar, "Refresh", self.refresh, "#30363d")

        stats = tk.LabelFrame(
            self,
            text="Repository Stats",
            bg="#101014",
            fg="#00ff99",
            padx=10,
            pady=8,
        )
        stats.pack(fill="x", padx=10, pady=6)

        grid = tk.Frame(stats, bg="#101014")
        grid.pack(fill="x")

        for idx, name in enumerate([
            "files",
            "python_files",
            "classes",
            "functions",
            "imports",
            "todos",
            "errors",
        ]):
            label = tk.Label(
                grid,
                text=name.replace("_", " ").title() + ":",
                bg="#101014",
                fg="#dddddd",
            )
            label.grid(row=idx // 4, column=(idx % 4) * 2, sticky="w", padx=5, pady=2)

            var = tk.StringVar(value="0")
            self.stat_vars[name] = var

            value = tk.Label(
                grid,
                textvariable=var,
                bg="#101014",
                fg="#ffffff",
                font=("Segoe UI", 10, "bold"),
            )
            value.grid(row=idx // 4, column=(idx % 4) * 2 + 1, sticky="w", padx=5, pady=2)

        search = tk.LabelFrame(
            self,
            text="Ask Repository",
            bg="#101014",
            fg="#00ff99",
            padx=10,
            pady=8,
        )
        search.pack(fill="both", expand=True, padx=10, pady=6)

        search_bar = tk.Frame(search, bg="#101014")
        search_bar.pack(fill="x")

        self.query_entry = tk.Entry(
            search_bar,
            bg="#161b22",
            fg="#ffffff",
            insertbackground="#ffffff",
        )
        self.query_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.query_entry.insert(0, "Where is vision engine?")
        self.query_entry.bind("<Return>", lambda event: self.ask_repository())

        self._button(search_bar, "Ask", self.ask_repository, "#1f6feb")

        quick = tk.Frame(search, bg="#101014")
        quick.pack(fill="x", pady=6)

        self._button(quick, "Largest Files", self.show_largest_files, "#30363d")
        self._button(quick, "TODOs", self.show_todos, "#30363d")
        self._button(quick, "Symbols", self.show_symbols, "#30363d")
        self._button(quick, "Tests", self.show_tests, "#30363d")

        graph_row = tk.Frame(search, bg="#101014")
        graph_row.pack(fill="x", pady=6)

        self._button(graph_row, "Who Calls", self.graph_who_calls, "#8957e5")
        self._button(graph_row, "Inherits", self.graph_inherits, "#8957e5")
        self._button(graph_row, "Dependencies", self.graph_dependencies, "#8957e5")
        self._button(graph_row, "Unused Imports", self.graph_unused_imports, "#8957e5")

        knowledge_row = tk.Frame(search, bg="#101014")
        knowledge_row.pack(fill="x", pady=6)

        self._button(knowledge_row, "Ask Knowledge", self.knowledge_ask, "#d29922")
        self._button(knowledge_row, "File Summary", self.knowledge_file_summary, "#d29922")
        self._button(knowledge_row, "Rename Impact", self.knowledge_rename_impact, "#d29922")
        self._button(knowledge_row, "Dependency Impact", self.knowledge_dependency_impact, "#d29922")

        self.output = tk.Text(
            search,
            bg="#0d1117",
            fg="#ffffff",
            insertbackground="#ffffff",
            wrap="word",
            height=14,
        )
        self.output.pack(fill="both", expand=True)

        jobs = tk.LabelFrame(
            self,
            text="Background Jobs",
            bg="#101014",
            fg="#00ff99",
            padx=10,
            pady=8,
        )
        jobs.pack(fill="both", expand=False, padx=10, pady=6)

        self.job_list = tk.Listbox(
            jobs,
            bg="#161b22",
            fg="#ffffff",
            selectbackground="#238636",
            height=5,
        )
        self.job_list.pack(fill="both", expand=True)

        self.after(1000, self.auto_refresh)

    def _button(self, parent, text, command, bg):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg="white",
            activebackground=bg,
            activeforeground="white",
        )
        btn.pack(side="left", padx=4)
        return btn

    def write_output(self, text: str):
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, text)

    def rebuild_project_model(self):
        self.ai_os.rebuild_project_model()
        self.refresh()

    def rebuild_repository_intelligence(self):
        self.write_output("Building repository intelligence...")
        self.update_idletasks()

        self.repo_intel = RepositoryIntelligenceBuilder(self.project_root).build()

        self.write_output(
            "Repository Intelligence Ready\n\n"
            f"Symbols: {len(self.repo_intel.symbols)}\n"
            f"Imports: {len(self.repo_intel.imports)}\n"
            f"TODOs: {len(self.repo_intel.todos)}\n"
            f"Largest files indexed: {len(self.repo_intel.largest_files)}\n"
            f"Test files: {len(self.repo_intel.test_files)}\n"
            f"Errors: {len(self.repo_intel.errors)}"
        )


    def rebuild_semantic_graph(self):
        self.write_output("Building semantic repository graph...")
        self.update_idletasks()

        self.semantic_graph = SemanticRepositoryGraphBuilder(self.project_root).build()

        self.write_output(
            "Semantic Repository Graph Ready\n\n"
            f"Calls: {len(self.semantic_graph.calls)}\n"
            f"Inheritance links: {len(self.semantic_graph.inheritance)}\n"
            f"Dependencies: {len(self.semantic_graph.dependencies)}\n"
            f"Unused import hints: {len(self.semantic_graph.unused_import_hints)}\n"
            f"Errors: {len(self.semantic_graph.errors)}"
        )

    def ensure_graph(self):
        if not self.semantic_graph:
            self.rebuild_semantic_graph()


    def rebuild_knowledge_engine(self):
        self.write_output("Building repository knowledge engine...")
        self.update_idletasks()

        self.knowledge_engine = RepositoryKnowledgeEngine(self.project_root)
        self.knowledge_engine.build()
        stats = self.knowledge_engine.stats()

        self.write_output(
            "Repository Knowledge Engine Ready\n\n"
            f"Files: {stats.get('files', 0)}\n"
            f"Symbols: {stats.get('symbols', 0)}\n"
            f"Imports: {stats.get('imports', 0)}\n"
            f"TODOs: {stats.get('todos', 0)}\n"
            f"Calls: {stats.get('calls', 0)}\n"
            f"Inheritance: {stats.get('inheritance', 0)}\n"
            f"Dependencies: {stats.get('dependencies', 0)}\n"
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
            query = "buster\\vision\\engine.py"

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
            query = "buster\\vision\\engine.py"

        if "\\" in query or "/" in query or query.endswith(".py"):
            question = "Dependencies for " + query
        elif "depend" in query.lower():
            question = query
        else:
            question = "Which modules depend on " + query

        self.write_output(self.semantic_graph.ask(question))

    def graph_unused_imports(self):
        self.ensure_graph()
        self.write_output(self.semantic_graph.ask("Show unused imports"))

    def ask_repository(self):
        if not self.repo_intel:
            self.rebuild_repository_intelligence()

        query = self.query_entry.get().strip()
        if not query:
            query = "Where is vision engine?"

        self.write_output(self.repo_intel.ask(query))

    def show_largest_files(self):
        if not self.repo_intel:
            self.rebuild_repository_intelligence()

        lines = ["Largest files:"]
        for f in self.repo_intel.largest_files[:20]:
            lines.append(f"- {f.file} | {f.lines} lines | {f.size} bytes")
        self.write_output("\n".join(lines))

    def show_todos(self):
        if not self.repo_intel:
            self.rebuild_repository_intelligence()

        lines = ["TODO / FIXME index:"]
        for todo in self.repo_intel.todos[:60]:
            lines.append(f"- {todo.file}:{todo.line} | {todo.text}")
        self.write_output("\n".join(lines))

    def show_symbols(self):
        if not self.repo_intel:
            self.rebuild_repository_intelligence()

        query = self.query_entry.get().strip()
        if not query:
            query = "Agent"

        matches = self.repo_intel.find_symbols(query)
        lines = [f"Symbols matching: {query}"]
        for s in matches[:80]:
            lines.append(f"- {s.kind}: {s.name} ({s.file}:{s.line})")

        if len(lines) == 1:
            lines.append("No symbol matches.")
        self.write_output("\n".join(lines))

    def show_tests(self):
        if not self.repo_intel:
            self.rebuild_repository_intelligence()

        lines = ["Test files:"]
        for item in self.repo_intel.test_files:
            lines.append(f"- {item}")
        self.write_output("\n".join(lines))

    def refresh(self):
        status = self.ai_os.status()

        for key, var in self.stat_vars.items():
            var.set(str(status.get(key, 0)))

        self.job_list.delete(0, tk.END)

        jobs = status.get("jobs", [])
        if not jobs:
            self.job_list.insert(tk.END, "No background jobs yet.")
        else:
            for job in jobs:
                text = f"[{job['status'].upper()}] {job['title']}  #{job['id']}"
                if job.get("error"):
                    text += f" ERROR: {job['error']}"
                self.job_list.insert(tk.END, text)

    def auto_refresh(self):
        self.refresh()
        self.after(1000, self.auto_refresh)


def launch_ai_os_dashboard(project_root: str | Path):
    root = tk.Tk()
    root.title("Buster AI OS Dashboard v3.4.2")
    root.geometry("760x720")
    app = AIOSDashboard(root, project_root)
    app.pack(fill="both", expand=True)
    root.mainloop()
