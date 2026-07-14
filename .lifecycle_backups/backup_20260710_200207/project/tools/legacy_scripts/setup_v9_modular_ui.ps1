New-Item -ItemType Directory -Force "buster/ui/v9" | Out-Null
New-Item -ItemType File -Force "buster/ui/v9/__init__.py" | Out-Null

@'
STYLE = r"""
QMainWindow, QWidget { background: #07111f; color: #e8f1ff; font-family: Segoe UI; }
QFrame#Sidebar { background: #050d18; border-right: 1px solid #17304d; }
QFrame#Card, QFrame#Panel { background: #0b1829; border: 1px solid #1d3f66; border-radius: 12px; }
QLabel#Logo { font-size: 30px; font-weight: bold; color: #20a8ff; }
QLabel#Title { font-size: 22px; font-weight: bold; color: #e8f1ff; }
QLabel#Small { color: #8ea6c8; }
QPushButton { background: #0f2540; border: 1px solid #1f6fa8; border-radius: 8px; padding: 10px; color: #e8f1ff; }
QPushButton:hover { background: #12365e; }
QPushButton#Active { background: #063f79; border: 1px solid #20a8ff; }
QLineEdit { background: #0d1b2f; border: 1px solid #2b6ea6; border-radius: 12px; padding: 14px; color: #e8f1ff; font-size: 14px; }
QScrollArea { border: none; }
"""
'@ | Set-Content "buster/ui/v9/theme.py"

@'
from pathlib import Path
import subprocess
import sys

class V9LiveServices:
    def __init__(self, services=None, settings=None):
        self.services = services
        self.settings = settings

    def safe(self, fn, fallback="unknown"):
        try:
            return fn()
        except Exception:
            return fallback

    def brain(self, text):
        if not self.services:
            return "No brain service connected."
        return self.services.get("brain").process(text)

    def git_branch(self):
        r = subprocess.run("git branch --show-current", capture_output=True, text=True, shell=True)
        return r.stdout.strip() or "unknown"

    def python_version(self):
        return sys.version.split()[0]

    def quick_info(self):
        ai = self.safe(lambda: self.services.get("ai").quick_status(), "unknown")
        return (
            "QUICK INFO\n\n"
            f"AI Provider      {ai}\n"
            f"Workspace        {Path.cwd().name}\n"
            f"Git Branch       {self.git_branch()}\n"
            f"Python           {self.python_version()}\n"
            "Internet         Connected\n\n"
            "● Buster v9.0.0"
        )
'@ | Set-Content "buster/ui/v9/live_services.py"

@'
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton

class Sidebar(QFrame):
    def __init__(self, live, on_dashboard=None, on_face=None):
        super().__init__()
        self.live = live
        self.on_dashboard = on_dashboard
        self.on_face = on_face
        self.setObjectName("Sidebar")
        self.setFixedWidth(270)
        self.build()

    def build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 18)

        logo = QLabel("🅱  BUSTER")
        logo.setObjectName("Logo")
        layout.addWidget(logo)

        sub = QLabel("v9.0 Desktop AI OS")
        sub.setObjectName("Small")
        layout.addWidget(sub)
        layout.addSpacing(24)

        items = [
            ("🏠  Dashboard", self.on_dashboard),
            ("💬  Chat", None),
            ("📁  Projects", None),
            ("🧠  Workspace", None),
            ("👁  Vision", None),
            ("🔊  Voice", None),
            ("🤖  Agents", None),
            ("🖥  Terminal", None),
            ("⚙  Settings", None),
            ("😊  Face Popup", self.on_face),
        ]

        for label, callback in items:
            btn = QPushButton(label)
            if "Chat" in label:
                btn.setObjectName("Active")
            if callback:
                btn.clicked.connect(callback)
            layout.addWidget(btn)

        layout.addStretch()

        self.quick = QLabel(self.live.quick_info())
        self.quick.setObjectName("Small")
        self.quick.setStyleSheet("color:#b7c9e8; font-size:13px;")
        layout.addWidget(self.quick)

    def refresh(self):
        self.quick.setText(self.live.quick_info())
'@ | Set-Content "buster/ui/v9/sidebar.py"

@'
from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFrame, QScrollArea

class ChatCard(QFrame):
    def __init__(self, text, is_user=False):
        super().__init__()
        self.setObjectName("Card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)

        top = QHBoxLayout()
        who = QLabel("👤  You" if is_user else "🤖  Buster")
        who.setStyleSheet("font-size:16px; font-weight:bold; color:#20a8ff;")
        time = QLabel(QTime.currentTime().toString("hh:mm:ss AP"))
        time.setObjectName("Small")
        top.addWidget(who)
        top.addStretch()
        top.addWidget(time)
        layout.addLayout(top)

        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setStyleSheet("font-size:14px; color:#dcecff;")
        layout.addWidget(body)

        if not is_user:
            actions = QHBoxLayout()
            for label in ["Copy", "Save", "Open Folder"]:
                actions.addWidget(QPushButton(label))
            actions.addStretch()
            layout.addLayout(actions)

class ChatView(QWidget):
    def __init__(self, live, on_message=None):
        super().__init__()
        self.live = live
        self.on_message = on_message
        self.build()

    def build(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        title = QLabel("Conversation")
        title.setObjectName("Title")
        clear = QPushButton("Clear")
        clear.clicked.connect(self.clear)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(clear)
        layout.addLayout(top)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.cards = QVBoxLayout(self.inner)
        self.cards.setSpacing(14)
        self.cards.addStretch()
        self.scroll.setWidget(self.inner)
        layout.addWidget(self.scroll, 1)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a command or message...")
        self.input.returnPressed.connect(self.send)
        send = QPushButton("Send")
        send.setFixedWidth(110)
        send.clicked.connect(self.send)
        row.addWidget(self.input, 1)
        row.addWidget(send)
        layout.addLayout(row)

        self.add_card("workspace snapshot", True)
        self.add_card(self.live.safe(lambda: self.live.brain("workspace snapshot"), "Buster v9 ready."), False)

    def add_card(self, text, is_user=False):
        self.cards.insertWidget(self.cards.count() - 1, ChatCard(text, is_user))

    def send(self):
        text = self.input.text().strip()
        if not text:
            return

        self.input.clear()
        self.add_card(text, True)

        try:
            reply = self.live.brain(text)
        except Exception as exc:
            reply = f"Command failed: {exc}"

        self.add_card(reply, False)

        if self.on_message:
            self.on_message()

    def clear(self):
        while self.cards.count() > 1:
            item = self.cards.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
'@ | Set-Content "buster/ui/v9/chat_view.py"

@'
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from buster.ui.v9.theme import STYLE

class FaceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Buster Face")
        self.resize(300, 320)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet(STYLE)

        self.frames = [
            "◕     ◕\n   ◡",
            "⌒     ⌒\n   ◡",
            "◕     ◕\n   ▬",
            "⌒     ⌒\n   ▬",
        ]
        self.index = 0

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.face = QLabel(self.frames[0])
        self.face.setAlignment(Qt.AlignCenter)
        self.face.setStyleSheet("font-size:60px; color:#20a8ff;")

        self.status = QLabel("Thinking...")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("font-size:24px; font-weight:bold; color:#20a8ff;")

        layout.addWidget(self.face)
        layout.addWidget(self.status)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(550)

    def animate(self):
        self.index = (self.index + 1) % len(self.frames)
        self.face.setText(self.frames[self.index])
'@ | Set-Content "buster/ui/v9/face_window.py"

@'
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
import psutil
from pathlib import Path
from buster.ui.v9.theme import STYLE

class DashboardWindow(QWidget):
    def __init__(self, live):
        super().__init__()
        self.live = live
        self.setWindowTitle("Dashboard")
        self.resize(520, 520)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)

        title = QLabel("Dashboard")
        title.setObjectName("Title")
        root.addWidget(title)

        self.rows = {}
        for label in ["CPU", "RAM", "Disk", "AI Mode", "Voice", "Vision", "Git Branch", "Project"]:
            row = QHBoxLayout()
            left = QLabel(label)
            right = QLabel("checking...")
            right.setStyleSheet("color:#35ff6b;")
            row.addWidget(left)
            row.addStretch()
            row.addWidget(right)
            root.addLayout(row)
            self.rows[label] = right

        buttons = QHBoxLayout()
        buttons.addWidget(QPushButton("Refresh"))
        buttons.addWidget(QPushButton("Open Data"))
        buttons.addWidget(QPushButton("Run Doctor"))
        root.addLayout(buttons)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)
        self.refresh()

    def refresh(self):
        self.rows["CPU"].setText(f"{psutil.cpu_percent()}%")
        mem = psutil.virtual_memory()
        self.rows["RAM"].setText(f"{mem.percent}%")
        disk = psutil.disk_usage("C:\\")
        self.rows["Disk"].setText(f"{round(disk.free / (1024 ** 3), 1)} GB free")
        self.rows["AI Mode"].setText(self.live.safe(lambda: self.live.services.get("ai").quick_status(), "unknown"))
        self.rows["Voice"].setText(self.live.safe(lambda: self.live.services.get("voice").status(), "unknown"))
        self.rows["Vision"].setText(self.live.safe(lambda: self.live.services.get("vision").status(), "unknown"))
        self.rows["Git Branch"].setText(self.live.git_branch())
        self.rows["Project"].setText(Path.cwd().name)
'@ | Set-Content "buster/ui/v9/dashboard.py"

@'
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget
from buster.ui.v9.theme import STYLE

class CommandPalette(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Command Palette")
        self.resize(520, 420)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout(self)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Type a command...")
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.addItems([
            "workspace snapshot",
            "git status",
            "python info",
            "approved folders",
            "repo summary",
            "index project",
            "check updates",
            "settings",
        ])
        layout.addWidget(self.list)

        self.search.textChanged.connect(self.filter)
        self.list.itemDoubleClicked.connect(self.accept)

    def filter(self, text):
        text = text.lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(text not in item.text().lower())

    def selected_command(self):
        item = self.list.currentItem()
        return item.text() if item else self.search.text().strip()
'@ | Set-Content "buster/ui/v9/command_palette.py"

@'
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel
from buster.ui.v9.theme import STYLE
from buster.ui.v9.live_services import V9LiveServices
from buster.ui.v9.sidebar import Sidebar
from buster.ui.v9.chat_view import ChatView
from buster.ui.v9.face_window import FaceWindow
from buster.ui.v9.dashboard import DashboardWindow
from buster.ui.v9.command_palette import CommandPalette

class V9MainWindow(QMainWindow):
    def __init__(self, services=None, settings=None):
        super().__init__()
        self.services = services
        self.settings = settings
        self.live = V9LiveServices(services, settings)
        self.face_window = None
        self.dashboard_window = None

        self.setWindowTitle("Buster v9.0 — Windows AI Desktop Companion")
        self.resize(1280, 820)
        self.setStyleSheet(STYLE)
        self.build()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_live)
        self.timer.start(2500)

    def build(self):
        root = QWidget()
        self.setCentralWidget(root)

        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.sidebar = Sidebar(self.live, self.show_dashboard, self.show_face)

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(28, 22, 28, 18)

        title = QLabel("Buster Desktop AI OS\nYour AI Development Companion")
        title.setObjectName("Title")
        main_layout.addWidget(title)

        self.chat = ChatView(self.live, self.refresh_live)
        main_layout.addWidget(self.chat, 1)

        footer = QLabel("Context: buster-desktop-companion     Tokens: 1,248     Temp: 0.2")
        footer.setObjectName("Small")
        main_layout.addWidget(footer)

        outer.addWidget(self.sidebar)
        outer.addWidget(main, 1)

    def refresh_live(self):
        self.sidebar.refresh()

    def show_face(self):
        if self.face_window is None:
            self.face_window = FaceWindow()
        self.face_window.show()
        self.face_window.raise_()

    def show_dashboard(self):
        if self.dashboard_window is None:
            self.dashboard_window = DashboardWindow(self.live)
        self.dashboard_window.show()
        self.dashboard_window.raise_()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_K and event.modifiers() & Qt.ControlModifier:
            dlg = CommandPalette(self)
            if dlg.exec():
                cmd = dlg.selected_command()
                if cmd:
                    self.chat.input.setText(cmd)
                    self.chat.send()
            return

        super().keyPressEvent(event)
'@ | Set-Content "buster/ui/v9/main_window.py"

@'
from buster.ui.v9.main_window import V9MainWindow
from buster.ui.v9.face_window import FaceWindow
'@ | Set-Content "buster/ui/v9/v9_shell.py"

Write-Host "Modular v9 UI created."