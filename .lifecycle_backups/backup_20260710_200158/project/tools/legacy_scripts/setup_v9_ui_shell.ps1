New-Item -ItemType Directory -Force "buster/ui/v9" | Out-Null
New-Item -ItemType File -Force "buster/ui/v9/__init__.py" | Out-Null

@'
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QTextEdit, QLineEdit, QFrame
)

STYLE = """
QMainWindow, QWidget {
    background: #07111f;
    color: #e8f1ff;
    font-family: Segoe UI;
}
QFrame#Sidebar {
    background: #06101d;
    border-right: 1px solid #18304f;
}
QFrame#Panel {
    background: #0d1b2f;
    border: 1px solid #1d3f66;
    border-radius: 10px;
}
QLabel#Title {
    font-size: 26px;
    font-weight: bold;
    color: #20a8ff;
}
QLabel#Section {
    font-size: 15px;
    font-weight: bold;
    color: #e8f1ff;
}
QPushButton {
    background: #0f2540;
    border: 1px solid #1f6fa8;
    border-radius: 8px;
    padding: 10px;
    color: #e8f1ff;
    text-align: left;
}
QPushButton:hover {
    background: #12365e;
}
QPushButton#Active {
    background: #063f79;
    border: 1px solid #20a8ff;
}
QTextEdit {
    background: #081426;
    border: 1px solid #18304f;
    border-radius: 10px;
    padding: 12px;
    color: #dcecff;
    font-size: 13px;
}
QLineEdit {
    background: #0d1b2f;
    border: 1px solid #2b6ea6;
    border-radius: 10px;
    padding: 12px;
    color: #e8f1ff;
    font-size: 13px;
}
"""

class V9MainWindow(QMainWindow):
    def __init__(self, services=None, settings=None):
        super().__init__()
        self.services = services
        self.settings = settings
        self.setWindowTitle("Buster v9.0 — Windows AI Desktop Companion")
        self.resize(1280, 820)
        self.setStyleSheet(STYLE)
        self.build()

    def build(self):
        root = QWidget()
        self.setCentralWidget(root)

        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(22, 22, 22, 22)

        title = QLabel("BUSTER")
        title.setObjectName("Title")
        side.addWidget(title)

        subtitle = QLabel("v9.0 Desktop AI OS")
        subtitle.setStyleSheet("color:#8ea6c8;")
        side.addWidget(subtitle)

        side.addSpacing(25)

        for label in [
            "🏠 Dashboard",
            "💬 Chat",
            "📁 Projects",
            "🧠 Workspace",
            "👁 Vision",
            "🔊 Voice",
            "🤖 Agents",
            "⚙ Settings",
        ]:
            btn = QPushButton(label)
            if "Chat" in label:
                btn.setObjectName("Active")
            side.addWidget(btn)

        side.addStretch()

        quick = QLabel(
            "QUICK INFO\n\n"
            "AI Provider   ● Ollama\n"
            "Workspace     buster-desktop-companion\n"
            "Git Branch    feature/web-brain\n"
            "Python        3.12.10\n"
            "Internet      Connected"
        )
        quick.setStyleSheet("color:#b7c9e8; line-height: 150%;")
        side.addWidget(quick)

        main = QFrame()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(26, 22, 26, 18)

        top = QHBoxLayout()
        heading = QLabel("Conversation")
        heading.setObjectName("Title")
        heading.setStyleSheet("font-size:22px; color:#e8f1ff;")
        top.addWidget(heading)
        top.addStretch()
        top.addWidget(QLabel("● Online"))
        main_layout.addLayout(top)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setPlainText(
            "👤 You\n"
            "workspace snapshot\n\n"
            "🤖 Buster\n"
            "Project: buster-desktop-companion\n"
            "Folder: C:\\Users\\xkali\\new_ai\\buster-desktop-companion\n\n"
            "Git\n"
            "  Branch : feature/web-brain\n"
            "  Status : Modified\n\n"
            "Python\n"
            "  Version : 3.12.10\n\n"
            "Workspace\n"
            "  Approved folders : 4\n"
            "  Project index : Yes\n"
            "  Settings : Yes\n\n"
            "Build\n"
            "  EXE : Yes\n"
            "  Installer : Yes\n"
        )
        main_layout.addWidget(self.chat, 1)

        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a command or message...")
        send = QPushButton("Send")
        send.setFixedWidth(100)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(send)
        main_layout.addLayout(input_row)

        footer = QLabel("Context: buster-desktop-companion        Tokens: 1,248        Temp: 0.2")
        footer.setStyleSheet("color:#8ea6c8;")
        main_layout.addWidget(footer)

        outer.addWidget(sidebar)
        outer.addWidget(main, 1)

class FaceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Buster Face")
        self.resize(260, 260)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        face = QLabel("◕   ◕\n  ▬")
        face.setAlignment(Qt.AlignCenter)
        face.setStyleSheet("font-size:48px; color:#20a8ff;")

        status = QLabel("Thinking...")
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet("font-size:22px; color:#20a8ff;")

        layout.addWidget(face)
        layout.addWidget(status)
'@ | Set-Content "buster/ui/v9/v9_shell.py"

@'
import sys
from PySide6.QtWidgets import QApplication
from buster.ui.v9.v9_shell import V9MainWindow, FaceWindow

app = QApplication(sys.argv)

main = V9MainWindow()
face = FaceWindow()

main.show()
face.show()

sys.exit(app.exec())
'@ | Set-Content "run_v9_ui_preview.py"

Write-Host "Buster v9 UI preview created."
Write-Host "Run with: python run_v9_ui_preview.py"