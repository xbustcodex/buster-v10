import os
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QApplication
)


class TerminalPanel(QWidget):
    def __init__(self, live=None, runtime_core=None):
        super().__init__()
        self.live = live
        self.runtime_core = runtime_core
        self.current_dir = os.getcwd()
        self.history = []
        self.history_index = -1
        self.project_name = Path.cwd().name
        self.prompt_text = "buster>"

        self.commands = {
            "help": self.cmd_help,
            "clear": self.cmd_clear,
            "history": self.cmd_history,

            # Filesystem
            "cd": self.cmd_cd,
            "ls": self.cmd_ls,
            "pwd": self.cmd_pwd,

            # Project
            "project": self.cmd_project,
            "workspace": self.cmd_workspace,

            # Runtime
            "runtime": self.cmd_runtime,

            # Agents
            "plan": self.cmd_plan,
            "build": self.cmd_build,
            "test": self.cmd_test,
            "review": self.cmd_review,
            "fix": self.cmd_fix,
            "agent": self.cmd_agent,
            "status": self.cmd_status,
            "jobs": self.cmd_jobs,
            "events": self.cmd_events,
            "memory": self.cmd_memory,
            "blackboard": self.cmd_blackboard,
            "registry": self.cmd_registry,
            "services": self.cmd_services,

            # Orchestrator (NEW)
            "task": self.cmd_task,
            "workflow": self.cmd_workflow,

            # Tools
            "python": self.cmd_python,
            "pip": self.cmd_pip,
            "git": self.cmd_git,

            "echo": self.cmd_echo,
            "exit": lambda args: self.close(),
        }

        self.setWindowTitle("Runtime Terminal")
        self.resize(1100, 720)
        self.build_ui()
        self.setup_shortcuts()
        self.display_welcome()

    def build_ui(self):
        self.setStyleSheet("""
            QWidget { background:#1e1e1e; color:#d4d4d4; }
            QPushButton {
                background:#2d2d2d; color:#cccccc; border:0;
                padding:6px 12px; border-radius:4px;
            }
            QPushButton:hover { background:#3d3d3d; }
            QLineEdit {
                background:#2d2d2d; color:#d4d4d4;
                padding:8px; border-radius:4px;
                font-family:Consolas;
            }
            QTextEdit {
                background:#101820; color:#d4d4d4;
                border:0; font-family:Consolas; font-size:10pt;
            }
        """)

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("🖥 Runtime Terminal")
        title.setStyleSheet("font-size:18px;font-weight:bold;color:white;")
        self.status = QLabel("● Ready")
        self.status.setStyleSheet("color:#4ec9b0;font-weight:bold;")
        self.project_label = QLabel(f"Project: {self.project_name}")
        self.project_label.setStyleSheet("color:#4ec9b0;")

        header.addWidget(title)
        header.addWidget(self.project_label)
        header.addStretch()
        header.addWidget(self.status)
        layout.addLayout(header)

        quick = QHBoxLayout()
        for cmd in ["project", "workspace", "build", "run", "test", "fix", "review", "agent"]:
            btn = QPushButton(cmd)
            btn.clicked.connect(lambda _, c=cmd: self.execute_command(c))
            quick.addWidget(btn)
        quick.addStretch()
        layout.addLayout(quick)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

        row = QHBoxLayout()
        self.prompt = QLabel(self.prompt_text)
        self.prompt.setStyleSheet("color:#4ec9b0;font-weight:bold;font-family:Consolas;")

        self.input = QLineEdit()
        self.input.setPlaceholderText("Enter command...")
        self.input.returnPressed.connect(self.run_input)

        run = QPushButton("Run")
        run.clicked.connect(self.run_input)

        clear = QPushButton("Clear")
        clear.clicked.connect(lambda: self.execute_command("clear"))

        row.addWidget(self.prompt)
        row.addWidget(self.input, 1)
        row.addWidget(run)
        row.addWidget(clear)
        layout.addLayout(row)

        self.dir_label = QLabel(f"📁 {self.current_dir}")
        self.dir_label.setStyleSheet("color:#569cd6;font-size:11px;")
        layout.addWidget(self.dir_label)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Up"), self).activated.connect(self.history_up)
        QShortcut(QKeySequence("Down"), self).activated.connect(self.history_down)
        QShortcut(QKeySequence("Tab"), self).activated.connect(self.auto_complete)

    def write(self, text, kind="output"):
        colors = {
            "prompt": "#4ec9b0",
            "error": "#f44747",
            "success": "#4ec9b0",
            "info": "#569cd6",
            "warning": "#dcdcaa",
            "command": "#c586c0",
            "output": "#d4d4d4",
            "path": "#ce9178",
        }
        color = colors.get(kind, "#d4d4d4")
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe = safe.replace(" ", "&nbsp;").replace("\n", "<br>")
        self.output.insertHtml(f'<span style="color:{color};">{safe}</span><br>')
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def display_welcome(self):
        self.write("🖥 Runtime Terminal ready", "info")
        self.write("Type 'help' for commands.", "info")
        self.write(f"Current directory: {self.current_dir}", "path")

    def run_input(self):
        command = self.input.text().strip()
        if command:
            self.input.clear()
            self.execute_command(command)

    def execute_command(self, command):
        self.history.append(command)
        self.history_index = len(self.history)

        self.write(f"\n{self.prompt_text} {command}", "command")

        parts = command.split()
        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1:]

        self.status.setText("● Running...")
        self.status.setStyleSheet("color:#dcdcaa;font-weight:bold;")
        QApplication.processEvents()

        try:
            if cmd in self.commands:
                self.commands[cmd](args)
            else:
                self.run_system(command)
        except Exception as e:
            self.write(str(e), "error")
        finally:
            self.status.setText("● Ready")
            self.status.setStyleSheet("color:#4ec9b0;font-weight:bold;")
            self.dir_label.setText(f"📁 {self.current_dir}")
            
    def cmd_runtime(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        if args and args[0] == "status":
            import json
            self.write(json.dumps(self.runtime_core.status(), indent=2, default=str), "info")
            return

        if args and args[0] == "tick":
            import json
            result = self.runtime_core.tick()
            self.write(json.dumps(result, indent=2, default=str), "success")
            return

        if args and args[0] == "test":
            import json
            result = self.runtime_core.run_agent("tester", {"request": "Run project tests"})
            self.write(json.dumps(result, indent=2, default=str), "success")
            return

        self.write("Usage: runtime status | runtime tick | runtime test", "info")        
            

    def run_system(self, command):
        result = subprocess.run(
            command,
            shell=True,
            cwd=self.current_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.stdout:
            self.write(result.stdout, "output")
        if result.stderr:
            self.write(result.stderr, "error")
        self.write(
            "Command completed." if result.returncode == 0 else f"Exit code: {result.returncode}",
            "success" if result.returncode == 0 else "error",
        )

    def cmd_help(self, args):
        self.write("""
Commands:
help, clear, history, cd, ls, pwd, status, jobs, events, memory, blackboard, registry, services,
project, workspace, build, run, test, fix, review, agent
git <args>, python <args>, pip <args>
Any unknown command runs in the system shell.
""", "info")

    def cmd_clear(self, args):
        self.output.clear()
        self.display_welcome()

    def cmd_history(self, args):
        for i, cmd in enumerate(self.history, 1):
            self.write(f"{i}. {cmd}", "output")

    def cmd_cd(self, args):
        target = Path.home() if not args else Path(args[0])
        if not target.is_absolute():
            target = Path(self.current_dir) / target
        if target.exists() and target.is_dir():
            self.current_dir = str(target.resolve())
            self.write(f"Changed directory to {self.current_dir}", "success")
        else:
            self.write(f"Directory not found: {target}", "error")

    def cmd_ls(self, args):
        for item in sorted(Path(self.current_dir).iterdir()):
            self.write(("📁 " if item.is_dir() else "📄 ") + item.name, "path" if item.is_dir() else "output")

    def cmd_pwd(self, args):
        self.write(self.current_dir, "path")

    def cmd_project(self, args):
        self.write(f"Project: {self.project_name}", "info")
        self.write(f"Root: {Path.cwd()}", "path")

    def cmd_workspace(self, args):
        ws = Path.cwd() / "buster_workspace" / "ai_builds"
        ws.mkdir(parents=True, exist_ok=True)
        self.write(f"AI Build Workspace: {ws}", "info")
        
    def cmd_workflow(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        import json

        result = self.runtime_core.workflow.run_request(
            " ".join(args) or "Build project"
        )

        self.write(
            json.dumps(result, indent=2, default=str),
            "success",
        )   

    def cmd_test(self, args):
        self.run_system("pytest -q")
        
    def cmd_plan(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        import json

        request = " ".join(args).strip()

        if not request:
            self.write("Usage: plan <request>", "warning")
            return

        try:
            result = self.runtime_core.run_agent(
                "planner",
                {"request": request},
            )

            self.write(
                json.dumps(result, indent=2, default=str),
                "success",
            )

        except Exception as e:
            self.write(f"Planner Agent failed: {e}", "error")    

    def cmd_build(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        import json

        request = " ".join(args).strip() or "Build project"

        try:
            result = self.runtime_core.run_agent(
                "builder",
                {"request": request},
            )

            self.write(
                json.dumps(result, indent=2, default=str),
                "success",
            )

        except Exception as e:
            self.write(f"Builder Agent failed: {e}", "error")

    def cmd_run(self, args):
        self.run_system("python main.py")

    def cmd_fix(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        import json

        request = " ".join(args).strip() or "Fix current project"

        try:
            result = self.runtime_core.run_agent(
                "fixer",
                {"request": request},
            )

            self.write(
                json.dumps(result, indent=2, default=str),
                "success",
            )

        except Exception as e:
            self.write(f"Fixer Agent failed: {e}", "error")

    def cmd_review(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        import json

        request = " ".join(args).strip() or "Review project code"

        try:
            result = self.runtime_core.run_agent(
                "reviewer",
                {"request": request},
            )

            self.write(
                json.dumps(result, indent=2, default=str),
                "success",
            )

        except Exception as e:
            self.write(f"Reviewer Agent failed: {e}", "error")
            
    def cmd_task(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        import json

        request = " ".join(args).strip()

        if not request:
            self.write("Usage: task <request>", "warning")
            return

        result = self.runtime_core.run(request)

        self.write(
            json.dumps(result, indent=2, default=str),
            "success",
        )        

    def cmd_agent(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        import json

        if not args:
            self.write(
                json.dumps(
                    self.runtime_core.agents.status(),
                    indent=2,
                    default=str,
                ),
                "info",
            )
            return

        name = args[0]
        request = " ".join(args[1:]) or "Run"

        try:
            result = self.runtime_core.run_agent(
                name,
                {"request": request},
            )

            self.write(
                json.dumps(result, indent=2, default=str),
                "success",
            )

        except Exception as e:
            self.write(str(e), "error")
            
    def _runtime_json(self, data, kind="info"):
        import json
        self.write(json.dumps(data, indent=2, default=str), kind)


    def cmd_status(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        self._runtime_json(self.runtime_core.status(), "info")


    def cmd_jobs(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        self._runtime_json(self.runtime_core.jobs.status(), "info")


    def cmd_events(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        limit = 25
        if args:
            try:
                limit = int(args[0])
            except ValueError:
                pass

        self._runtime_json(self.runtime_core.events.recent(limit), "info")


    def cmd_memory(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        self._runtime_json(self.runtime_core.agent_memory.status(), "info")


    def cmd_blackboard(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        self._runtime_json(self.runtime_core.blackboard.snapshot(), "info")


    def cmd_registry(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        self._runtime_json(self.runtime_core.registry.status(), "info")


    def cmd_services(self, args):
        if not self.runtime_core:
            self.write("Runtime core not connected.", "error")
            return

        self._runtime_json(
            {
                "services": self.runtime_core.sdk.registry.names(),
                "agents": self.runtime_core.agents.names(),
            },
            "info",
        )       

    def cmd_git(self, args):
        self.run_system("git " + " ".join(args) if args else "git status")

    def cmd_python(self, args):
        self.run_system("python " + " ".join(args) if args else "python --version")

    def cmd_pip(self, args):
        self.run_system("pip " + " ".join(args) if args else "pip --version")

    def cmd_echo(self, args):
        self.write(" ".join(args), "output")

    def history_up(self):
        if self.history and self.history_index > 0:
            self.history_index -= 1
            self.input.setText(self.history[self.history_index])

    def history_down(self):
        if self.history and self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.input.setText(self.history[self.history_index])
        else:
            self.input.clear()
            self.history_index = len(self.history)

    def auto_complete(self):
        text = self.input.text().strip().lower()
        matches = [c for c in self.commands if c.startswith(text)]
        if len(matches) == 1:
            self.input.setText(matches[0] + " ")
        elif matches:
            self.write("Completions: " + ", ".join(matches), "info")