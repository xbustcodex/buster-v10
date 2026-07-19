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

==============================
BUSTER v10 STABILIZATION
==============================

UI
[✓] Dashboard
[✓] Chat
[✓] Sidebar Navigation
[✓] Runtime Workspace
[✓] Runtime Timeline
[✓] Face Popup
[✓] Notification Center
[✓] Developer Mission Control
[✓] Self Improvement

Core Runtime
[✓] Runtime Core
[✓] Event Bus
[✓] Service Manager
[✓] Runtime Monitor
[✓] Lifecycle Manager

AI
[✓] Provider Framework
[✓] Ollama
[ ] Claude
[ ] OpenAI
[ ] Gemini

Autonomy
[✓] Autonomy Engine
[✓] Execution Engine
[✓] Self Improvement Service
[✓] Strategy Selector
[✓] Risk Analysis

Testing
[ ] UI opens without errors
[ ] Runtime starts cleanly
[ ] Event Bus verified
[ ] All panels refresh
[ ] Memory verified
[ ] Plugin loading verified
[ ] AI conversation verified
[ ] Execution Engine verified
[ ] Self Improvement verified

Release
[ ] PyInstaller build
[ ] Installer
[ ] Documentation
Git Branch
{git}
"""
        self.output.setPlainText(text.strip())
