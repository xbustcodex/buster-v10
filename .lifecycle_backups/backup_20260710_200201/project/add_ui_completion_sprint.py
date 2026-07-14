from pathlib import Path

ROOT = Path.cwd()

files = {
    "buster/ui/v9/panels/developer_checklist_panel.py": r'''from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton


class DeveloperChecklistPanel(QWidget):
    def __init__(self, live=None):
        super().__init__()
        self.live = live
        self.setWindowTitle("Developer Checklist")
        self.resize(720, 620)

        layout = QVBoxLayout(self)

        title = QLabel("🛠 Buster Developer Checklist")
        title.setObjectName("Title")
        layout.addWidget(title)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh)

        self.refresh()

    def refresh(self):
        git = self.live.git_branch() if self.live else "unknown"

        text = f"""
UI COMPLETION SPRINT

Main UI
[✓] Dashboard
[✓] Chat
[✓] Backend Tools
[✓] Face Popup
[~] Projects
[~] Workspace
[~] Vision
[~] Voice
[~] Agents
[~] Terminal
[~] Settings

Backend Tools
[✓] Runtime Dashboard
[✓] Runtime Console
[✓] Mission Control
[✓] Live Runtime UI

Runtime
[✓] Runtime Core
[✓] SDK Runtime
[✓] Registry
[✓] Job Manager
[✓] Agent Orchestrator
[✓] Blackboard
[✓] Agent Memory
[✓] Developer Tools

Next Work
[ ] Upgrade Projects panel
[ ] Upgrade Workspace panel
[ ] Upgrade Vision panel
[ ] Upgrade Voice panel
[ ] Upgrade Agents panel
[ ] Upgrade Terminal panel
[ ] Upgrade Settings panel
[ ] Polish sidebar spacing
[ ] Add proper plugin manager

Git Branch
{git}
"""
        self.output.setPlainText(text.strip())
''',

    "buster/ui/v9/panels/simple_status_panel.py": r'''from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton


class SimpleStatusPanel(QWidget):
    def __init__(self, title="Panel", message="", live=None):
        super().__init__()
        self.panel_title = title
        self.message = message
        self.live = live

        self.setWindowTitle(title)
        self.resize(720, 520)

        layout = QVBoxLayout(self)

        heading = QLabel(title)
        heading.setObjectName("Title")
        layout.addWidget(heading)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

        close = QPushButton("Close")
        close.clicked.connect(self.close)
        layout.addWidget(close)

        self.refresh()

    def refresh(self):
        self.output.setPlainText(self.message)
'''
}

for rel, content in files.items():
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"created/updated: {rel}")

print("UI Completion Sprint panels added.")