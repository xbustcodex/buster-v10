from pathlib import Path

p = Path("buster/ui/v9/v9_live.py")
p.parent.mkdir(parents=True, exist_ok=True)

p.write_text(r'''
from pathlib import Path
from PySide6.QtCore import QTimer

class V9LiveData:
    def __init__(self, services=None, settings=None):
        self.services = services
        self.settings = settings

    def safe(self, fn, fallback="unknown"):
        try:
            return fn()
        except Exception:
            return fallback

    def workspace_snapshot(self):
        try:
            from buster.workspace.runtime import WorkspaceSnapshot
            return WorkspaceSnapshot().snapshot()
        except Exception as exc:
            return f"Workspace unavailable: {exc}"

    def quick_info(self):
        project = Path.cwd().name

        ai = self.safe(lambda: self.services.get("ai").quick_status(), "unknown")
        git = self.safe(lambda: self._git_branch(), "unknown")
        python = self.safe(lambda: self._python_version(), "unknown")

        return (
            "QUICK INFO\n\n"
            f"AI Provider      {ai}\n"
            f"Workspace        {project}\n"
            f"Git Branch       {git}\n"
            f"Python           {python}\n"
            "Internet         Connected\n\n"
            "● Buster v9.0.0"
        )

    def dashboard_rows(self):
        return {
            "AI Mode": self.safe(lambda: self.services.get("ai").quick_status(), "unknown"),
            "Voice": self.safe(lambda: self.services.get("voice").status(), "unknown"),
            "Vision": self.safe(lambda: self.services.get("vision").status(), "unknown"),
            "Project": Path.cwd().name,
            "Git Branch": self.safe(lambda: self._git_branch(), "unknown"),
            "Project Index": "Found" if Path("data/project_index.json").exists() else "Missing",
            "Build EXE": "Found" if Path("dist/Buster/Buster.exe").exists() else "Missing",
            "Installer": "Found" if any(Path("dist").glob("*.exe")) else "Missing",
        }

    def _git_branch(self):
        import subprocess
        r = subprocess.run("git branch --show-current", capture_output=True, text=True, shell=True)
        return r.stdout.strip() or "unknown"

    def _python_version(self):
        import sys
        return sys.version.split()[0]
''', encoding="utf-8")

shell = Path("buster/ui/v9/v9_shell.py")
text = shell.read_text(encoding="utf-8")

if "from buster.ui.v9.v9_live import V9LiveData" not in text:
    text = text.replace(
        "import psutil\n\nfrom PySide6.QtWidgets import",
        "import psutil\nfrom buster.ui.v9.v9_live import V9LiveData\n\nfrom PySide6.QtWidgets import",
    )

# Add live data instance in V9MainWindow init
text = text.replace(
    "self.settings = settings\n        self.face_window = None",
    "self.settings = settings\n        self.live = V9LiveData(services=services, settings=settings)\n        self.face_window = None",
)

# Replace static quick info block
old_quick = '''        quick = QLabel(
            "QUICK INFO\\n\\n"
            "AI Provider      ● Ollama\\n"
            "Model            llama3:instruct\\n"
            "Workspace        buster-desktop-companion\\n"
            "Git Branch       feature/web-brain\\n"
            "Python           3.12.10\\n"
            "Internet         Connected\\n\\n"
            "● Buster v9.0.0"
        )'''

new_quick = '''        self.quick = QLabel(self.live.quick_info())'''

text = text.replace(old_quick, new_quick)
text = text.replace("quick.setObjectName", "self.quick.setObjectName")
text = text.replace("quick.setStyleSheet", "self.quick.setStyleSheet")
text = text.replace("side.addWidget(quick)", "side.addWidget(self.quick)")

# Add live refresh timer
text = text.replace(
    "self.build()\n        self.shortcut_palette = None",
    "self.build()\n        self.shortcut_palette = None\n        self.live_timer = QTimer(self)\n        self.live_timer.timeout.connect(self.refresh_live_ui)\n        self.live_timer.start(2500)",
)

# Replace send placeholder with real brain service
text = text.replace(
'''        self.add_card(text, True)
        self.add_card("v9 preview received your command.\\nBackend wiring comes next.", False)''',
'''        self.add_card(text, True)
        try:
            reply = self.services.get("brain").process(text) if self.services else "No brain service connected."
        except Exception as exc:
            reply = f"Command failed: {exc}"
        self.add_card(reply, False)
        self.refresh_live_ui()'''
)

# Add refresh_live_ui before add_card
if "def refresh_live_ui(self):" not in text:
    text = text.replace(
"    def add_card(self, text, is_user=False):",
'''    def refresh_live_ui(self):
        try:
            self.quick.setText(self.live.quick_info())
        except Exception:
            pass

    def add_card(self, text, is_user=False):'''
    )

shell.write_text(text, encoding="utf-8")

print("v9 Phase 1 live UI integration installed.")
'', encoding="utf-8"

print("Created setup_v9_phase1_live_ui.py")