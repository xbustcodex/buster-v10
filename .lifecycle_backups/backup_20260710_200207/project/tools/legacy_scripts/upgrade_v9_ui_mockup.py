from pathlib import Path

p = Path("buster/ui/v9/v9_shell.py")

p.write_text(r'''
from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QTextEdit, QLineEdit, QFrame, QScrollArea,
    QSizePolicy
)

STYLE = """
QMainWindow, QWidget {
    background: #07111f;
    color: #e8f1ff;
    font-family: Segoe UI;
}
QFrame#Sidebar {
    background: #050d18;
    border-right: 1px solid #17304d;
}
QFrame#Card, QFrame#Dashboard {
    background: #0b1829;
    border: 1px solid #1d3f66;
    border-radius: 12px;
}
QLabel#Logo {
    font-size: 30px;
    font-weight: bold;
    color: #20a8ff;
}
QLabel#Title {
    font-size: 22px;
    font-weight: bold;
}
QLabel#Small {
    color: #8ea6c8;
}
QPushButton {
    background: #0f2540;
    border: 1px solid #1f6fa8;
    border-radius: 8px;
    padding: 10px;
    color: #e8f1ff;
}
QPushButton:hover {
    background: #12365e;
}
QPushButton#Active {
    background: #063f79;
    border: 1px solid #20a8ff;
}
QLineEdit {
    background: #0d1b2f;
    border: 1px solid #2b6ea6;
    border-radius: 12px;
    padding: 14px;
    color: #e8f1ff;
    font-size: 14px;
}
QScrollArea {
    border: none;
}
"""

class ChatCard(QFrame):
    def __init__(self, who, text, is_user=False):
        super().__init__()
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)

        top = QHBoxLayout()
        name = QLabel(("👤  You" if is_user else "🤖  Buster"))
        name.setStyleSheet("font-size:16px; font-weight:bold; color:#20a8ff;")
        time = QLabel(QTime.currentTime().toString("hh:mm:ss AP"))
        time.setObjectName("Small")
        top.addWidget(name)
        top.addStretch()
        top.addWidget(time)
        lay.addLayout(top)

        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setStyleSheet("font-size:14px; line-height:150%; color:#dcecff;")
        lay.addWidget(body)

        if not is_user:
            actions = QHBoxLayout()
            for label in ["Copy", "Save", "Open Folder"]:
                actions.addWidget(QPushButton(label))
            actions.addStretch()
            lay.addLayout(actions)

class FaceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Buster Face")
        self.resize(260, 270)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet(STYLE)

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)

        face = QLabel("◕     ◕\n   ▬")
        face.setAlignment(Qt.AlignCenter)
        face.setStyleSheet("font-size:52px; color:#20a8ff;")

        status = QLabel("Thinking...")
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet("font-size:22px; font-weight:bold; color:#20a8ff;")

        dots = QLabel("● ● ● ● ●")
        dots.setAlignment(Qt.AlignCenter)
        dots.setStyleSheet("font-size:20px; color:#20a8ff;")

        lay.addWidget(face)
        lay.addWidget(status)
        lay.addWidget(dots)

class DashboardWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard")
        self.resize(500, 480)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)

        title = QLabel("Dashboard")
        title.setObjectName("Title")
        root.addWidget(title)

        tabs = QLabel("System     Performance     Environment     Health")
        tabs.setStyleSheet("color:#20a8ff; font-size:14px;")
        root.addWidget(tabs)

        rows = [
            ("CPU", "14%"),
            ("RAM", "6.2 / 16 GB (39%)"),
            ("GPU", "Intel Iris Xe"),
            ("Disk (C:)", "182 GB free"),
            ("Ollama", "Running ●"),
            ("AI Mode", "Ollama"),
            ("Voice", "Ready"),
            ("Vision", "Ready"),
            ("Internet", "Connected"),
            ("Git Branch", "feature/web-brain"),
            ("Project", "buster-desktop-companion"),
            ("Project Index", "Up to date ●"),
            ("Build EXE", "Found"),
            ("Installer", "Found"),
        ]

        for k, v in rows:
            row = QHBoxLayout()
            a = QLabel(k)
            b = QLabel(v)
            b.setStyleSheet("color:#35ff6b;")
            row.addWidget(a)
            row.addStretch()
            row.addWidget(b)
            root.addLayout(row)

        buttons = QHBoxLayout()
        for label in ["Refresh", "Open Data", "Run Doctor"]:
            buttons.addWidget(QPushButton(label))
        root.addLayout(buttons)

class V9MainWindow(QMainWindow):
    def __init__(self, services=None, settings=None):
        super().__init__()
        self.services = services
        self.settings = settings
        self.face_window = None
        self.dashboard_window = None

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
        sidebar.setFixedWidth(270)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(24, 24, 24, 18)

        logo = QLabel("🅱  BUSTER")
        logo.setObjectName("Logo")
        side.addWidget(logo)

        sub = QLabel("v9.0")
        sub.setObjectName("Small")
        side.addWidget(sub)

        side.addSpacing(26)

        nav = [
            ("🏠  Dashboard", self.show_dashboard),
            ("💬  Chat", None),
            ("📁  Projects", None),
            ("🧠  Workspace", None),
            ("👁  Vision", None),
            ("🔊  Voice", None),
            ("🤖  Agents", None),
            ("🖥  Terminal", None),
            ("⚙  Settings", None),
            ("😊  Face Popup", self.show_face),
        ]

        for label, cb in nav:
            btn = QPushButton(label)
            if "Chat" in label:
                btn.setObjectName("Active")
            if cb:
                btn.clicked.connect(cb)
            side.addWidget(btn)

        side.addStretch()

        quick = QLabel(
            "QUICK INFO\n\n"
            "AI Provider      ● Ollama\n"
            "Model            llama3:instruct\n"
            "Workspace        buster-desktop-companion\n"
            "Git Branch       feature/web-brain\n"
            "Python           3.12.10\n"
            "Internet         Connected\n\n"
            "● Buster v9.0.0"
        )
        quick.setObjectName("Small")
        quick.setStyleSheet("color:#b7c9e8; font-size:13px; line-height:160%;")
        side.addWidget(quick)

        main = QWidget()
        ml = QVBoxLayout(main)
        ml.setContentsMargins(28, 22, 28, 18)

        top = QHBoxLayout()
        title = QLabel("Conversation")
        title.setObjectName("Title")
        top.addWidget(title)
        top.addStretch()
        top.addWidget(QLabel("● Online"))
        clear = QPushButton("Clear")
        clear.clicked.connect(self.clear_chat)
        top.addWidget(clear)
        ml.addLayout(top)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.chat_inner = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_inner)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(14)
        self.chat_layout.addStretch()
        self.scroll.setWidget(self.chat_inner)
        ml.addWidget(self.scroll, 1)

        self.add_card("workspace snapshot", True)
        self.add_card(
            "Project: buster-desktop-companion\n"
            "Folder: C:\\Users\\xkali\\new_ai\\buster-desktop-companion\n\n"
            "Git\n  Branch : feature/web-brain\n  Status : Modified\n\n"
            "Python\n  Version : 3.12.10\n\n"
            "Workspace\n  Approved folders : 4\n  Project index : Yes\n  Settings : Yes\n\n"
            "Build\n  EXE : Yes\n  Installer : Yes",
            False
        )

        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a command or message...")
        self.input.returnPressed.connect(self.send)
        send = QPushButton("Send")
        send.setFixedWidth(110)
        send.clicked.connect(self.send)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(send)
        ml.addLayout(input_row)

        footer = QLabel("● Context: buster-desktop-companion        Tokens: 1,248        Temp: 0.2")
        footer.setObjectName("Small")
        ml.addWidget(footer)

        outer.addWidget(sidebar)
        outer.addWidget(main, 1)

    def add_card(self, text, is_user=False):
        card = ChatCard("You" if is_user else "Buster", text, is_user)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, card)

    def send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.add_card(text, True)
        self.add_card("v9 preview received your command.\nBackend wiring comes next.", False)

    def clear_chat(self):
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def show_face(self):
        if self.face_window is None:
            self.face_window = FaceWindow()
        self.face_window.show()
        self.face_window.raise_()

    def show_dashboard(self):
        if self.dashboard_window is None:
            self.dashboard_window = DashboardWindow()
        self.dashboard_window.show()
        self.dashboard_window.raise_()
''', encoding="utf-8")

print("Upgraded v9_shell.py to closer mockup style.")