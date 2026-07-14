from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton


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
