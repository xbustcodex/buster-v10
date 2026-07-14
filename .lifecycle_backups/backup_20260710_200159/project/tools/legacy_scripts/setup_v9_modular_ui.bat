@echo off
setlocal

mkdir buster\ui\v9 2>nul

echo.> buster\ui\v9\__init__.py

REM theme.py
(
echo STYLE = r"""
echo QMainWindow, QWidget { background: #07111f; color: #e8f1ff; font-family: Segoe UI; }
echo QFrame#Sidebar { background: #050d18; border-right: 1px solid #17304d; }
echo QFrame#Card, QFrame#Panel { background: #0b1829; border: 1px solid #1d3f66; border-radius: 12px; }
echo QLabel#Logo { font-size: 30px; font-weight: bold; color: #20a8ff; }
echo QLabel#Title { font-size: 22px; font-weight: bold; color: #e8f1ff; }
echo QLabel#Small { color: #8ea6c8; }
echo QPushButton { background: #0f2540; border: 1px solid #1f6fa8; border-radius: 8px; padding: 10px; color: #e8f1ff; }
echo QPushButton:hover { background: #12365e; }
echo QPushButton#Active { background: #063f79; border: 1px solid #20a8ff; }
echo QLineEdit { background: #0d1b2f; border: 1px solid #2b6ea6; border-radius: 12px; padding: 14px; color: #e8f1ff; font-size: 14px; }
echo QScrollArea { border: none; }
echo """
) > buster\ui\v9\theme.py

REM live_services.py
(
echo from pathlib import Path
echo import subprocess, sys
echo.
echo class V9LiveServices:
echo     def __init__(self, services=None, settings=None):
echo         self.services = services
echo         self.settings = settings
echo.
echo     def safe(self, fn, fallback="unknown"):
echo         try: return fn()
echo         except Exception: return fallback
echo.
echo     def brain(self, text):
echo         if not self.services:
echo             return "No brain service connected."
echo         return self.services.get("brain").process(text)
echo.
echo     def git_branch(self):
echo         r = subprocess.run("git branch --show-current", capture_output=True, text=True, shell=True)
echo         return r.stdout.strip() or "unknown"
echo.
echo     def python_version(self):
echo         return sys.version.split()[0]
echo.
echo     def quick_info(self):
echo         ai = self.safe(lambda: self.services.get("ai").quick_status(), "unknown")
echo         return (
echo             "QUICK INFO\n\n"
echo             f"AI Provider      {ai}\n"
echo             f"Workspace        {Path.cwd().name}\n"
echo             f"Git Branch       {self.git_branch()}\n"
echo             f"Python           {self.python_version()}\n"
echo             "Internet         Connected\n\n"
echo             "● Buster v9.0.0"
echo         )
) > buster\ui\v9\live_services.py

REM sidebar.py
(
echo from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton
echo.
echo class Sidebar(QFrame):
echo     def __init__(self, live, on_dashboard=None, on_face=None):
echo         super().__init__()
echo         self.live = live
echo         self.on_dashboard = on_dashboard
echo         self.on_face = on_face
echo         self.setObjectName("Sidebar")
echo         self.setFixedWidth(270)
echo         self.build()
echo.
echo     def build(self):
echo         layout = QVBoxLayout(self)
echo         layout.setContentsMargins(24,24,24,18)
echo         logo = QLabel("🅱  BUSTER")
echo         logo.setObjectName("Logo")
echo         layout.addWidget(logo)
echo         sub = QLabel("v9.0 Desktop AI OS")
echo         sub.setObjectName("Small")
echo         layout.addWidget(sub)
echo         layout.addSpacing(24)
echo.
echo         items = [
echo             ("🏠  Dashboard", self.on_dashboard),
echo             ("💬  Chat", None),
echo             ("📁  Projects", None),
echo             ("🧠  Workspace", None),
echo             ("👁  Vision", None),
echo             ("🔊  Voice", None),
echo             ("🤖  Agents", None),
echo             ("🖥  Terminal", None),
echo             ("⚙  Settings", None),
echo             ("😊  Face Popup", self.on_face),
echo         ]
echo.
echo         for label, callback in items:
echo             btn = QPushButton(label)
echo             if "Chat" in label:
echo                 btn.setObjectName("Active")
echo             if callback:
echo                 btn.clicked.connect(callback)
echo             layout.addWidget(btn)
echo.
echo         layout.addStretch()
echo         self.quick = QLabel(self.live.quick_info())
echo         self.quick.setObjectName("Small")
echo         self.quick.setStyleSheet("color:#b7c9e8; font-size:13px;")
echo         layout.addWidget(self.quick)
echo.
echo     def refresh(self):
echo         self.quick.setText(self.live.quick_info())
) > buster\ui\v9\sidebar.py

REM chat_view.py
(
echo from PySide6.QtCore import Qt, QTime
echo from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QFrame, QScrollArea
echo.
echo class ChatCard(QFrame):
echo     def __init__(self, text, is_user=False):
echo         super().__init__()
echo         self.setObjectName("Card")
echo         layout = QVBoxLayout(self)
echo         layout.setContentsMargins(18,14,18,14)
echo         top = QHBoxLayout()
echo         who = QLabel("👤  You" if is_user else "🤖  Buster")
echo         who.setStyleSheet("font-size:16px; font-weight:bold; color:#20a8ff;")
echo         time = QLabel(QTime.currentTime().toString("hh:mm:ss AP"))
echo         time.setObjectName("Small")
echo         top.addWidget(who)
echo         top.addStretch()
echo         top.addWidget(time)
echo         layout.addLayout(top)
echo         body = QLabel(text)
echo         body.setWordWrap(True)
echo         body.setTextInteractionFlags(Qt.TextSelectableByMouse)
echo         body.setStyleSheet("font-size:14px; color:#dcecff;")
echo         layout.addWidget(body)
echo         if not is_user:
echo             actions = QHBoxLayout()
echo             for label in ["Copy", "Save", "Open Folder"]:
echo                 actions.addWidget(QPushButton(label))
echo             actions.addStretch()
echo             layout.addLayout(actions)
echo.
echo class ChatView(QWidget):
echo     def __init__(self, live, on_message=None):
echo         super().__init__()
echo         self.live = live
echo         self.on_message = on_message
echo         self.build()
echo.
echo     def build(self):
echo         layout = QVBoxLayout(self)
echo         top = QHBoxLayout()
echo         title = QLabel("Conversation")
echo         title.setObjectName("Title")
echo         clear = QPushButton("Clear")
echo         clear.clicked.connect(self.clear)
echo         top.addWidget(title)
echo         top.addStretch()
echo         top.addWidget(clear)
echo         layout.addLayout(top)
echo.
echo         self.scroll = QScrollArea()
echo         self.scroll.setWidgetResizable(True)
echo         self.inner = QWidget()
echo         self.cards = QVBoxLayout(self.inner)
echo         self.cards.setSpacing(14)
echo         self.cards.addStretch()
echo         self.scroll.setWidget(self.inner)
echo         layout.addWidget(self.scroll, 1)
echo.
echo         row = QHBoxLayout()
echo         self.input = QLineEdit()
echo         self.input.setPlaceholderText("Type a command or message...")
echo         self.input.returnPressed.connect(self.send)
echo         send = QPushButton("Send")
echo         send.setFixedWidth(110)
echo         send.clicked.connect(self.send)
echo         row.addWidget(self.input, 1)
echo         row.addWidget(send)
echo         layout.addLayout(row)
echo.
echo         self.add_card("workspace snapshot", True)
echo         self.add_card(self.live.safe(lambda: self.live.brain("workspace snapshot"), "Buster v9 ready."), False)
echo.
echo     def add_card(self, text, is_user=False):
echo         self.cards.insertWidget(self.cards.count()-1, ChatCard(text, is_user))
echo.
echo     def send(self):
echo         text = self.input.text().strip()
echo         if not text: return
echo         self.input.clear()
echo         self.add_card(text, True)
echo         try: reply = self.live.brain(text)
echo         except Exception as exc: reply = f"Command failed: {exc}"
echo         self.add_card(reply, False)
echo         if self.on_message: self.on_message()
echo.
echo     def clear(self):
echo         while self.cards.count() ^> 1:
echo             item = self.cards.takeAt(0)
echo             w = item.widget()
echo             if w: w.deleteLater()
) > buster\ui\v9\chat_view.py

REM face_window.py
(
echo from PySide6.QtCore import Qt, QTimer
echo from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
echo from buster.ui.v9.theme import STYLE
echo.
echo class FaceWindow(QWidget):
echo     def __init__(self):
echo         super().__init__()
echo         self.setWindowTitle("Buster Face")
echo         self.resize(300, 320)
echo         self.setWindowFlags(Qt.WindowStaysOnTopHint ^| Qt.Tool)
echo         self.setStyleSheet(STYLE)
echo         self.frames = ["◕     ◕\n   ◡", "⌒     ⌒\n   ◡", "◕     ◕\n   ▬", "⌒     ⌒\n   ▬"]
echo         self.i = 0
echo         layout = QVBoxLayout(self)
echo         layout.setAlignment(Qt.AlignCenter)
echo         self.face = QLabel(self.frames[0])
echo         self.face.setAlignment(Qt.AlignCenter)
echo         self.face.setStyleSheet("font-size:60px; color:#20a8ff;")
echo         self.status = QLabel("Thinking...")
echo         self.status.setAlignment(Qt.AlignCenter)
echo         self.status.setStyleSheet("font-size:24px; font-weight:bold; color:#20a8ff;")
echo         layout.addWidget(self.face)
echo         layout.addWidget(self.status)
echo         timer = QTimer(self)
echo         timer.timeout.connect(self.animate)
echo         timer.start(550)
echo         self.timer = timer
echo.
echo     def animate(self):
echo         self.i = (self.i + 1) %% len(self.frames)
echo         self.face.setText(self.frames[self.i])
) > buster\ui\v9\face_window.py

REM dashboard.py
(
echo from PySide6.QtCore import Qt, QTimer
echo from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
echo import psutil
echo from buster.ui.v9.theme import STYLE
echo.
echo class DashboardWindow(QWidget):
echo     def __init__(self, live):
echo         super().__init__()
echo         self.live = live
echo         self.setWindowTitle("Dashboard")
echo         self.resize(520,520)
echo         self.setWindowFlags(Qt.WindowStaysOnTopHint ^| Qt.Tool)
echo         self.setStyleSheet(STYLE)
echo         root = QVBoxLayout(self)
echo         title = QLabel("Dashboard")
echo         title.setObjectName("Title")
echo         root.addWidget(title)
echo         self.rows = {}
echo         for label in ["CPU","RAM","Disk","AI Mode","Voice","Vision","Git Branch","Project"]:
echo             row = QHBoxLayout()
echo             a = QLabel(label)
echo             b = QLabel("checking...")
echo             b.setStyleSheet("color:#35ff6b;")
echo             row.addWidget(a)
echo             row.addStretch()
echo             row.addWidget(b)
echo             root.addLayout(row)
echo             self.rows[label] = b
echo         btns = QHBoxLayout()
echo         btns.addWidget(QPushButton("Refresh"))
echo         btns.addWidget(QPushButton("Open Data"))
echo         btns.addWidget(QPushButton("Run Doctor"))
echo         root.addLayout(btns)
echo         self.timer = QTimer(self)
echo         self.timer.timeout.connect(self.refresh)
echo         self.timer.start(1500)
echo         self.refresh()
echo.
echo     def refresh(self):
echo         self.rows["CPU"].setText(f"{psutil.cpu_percent()}%%")
echo         mem = psutil.virtual_memory()
echo         self.rows["RAM"].setText(f"{mem.percent}%%")
echo         disk = psutil.disk_usage("C:\\")
echo         self.rows["Disk"].setText(f"{round(disk.free/(1024**3),1)} GB free")
echo         self.rows["AI Mode"].setText(self.live.safe(lambda: self.live.services.get("ai").quick_status(), "unknown"))
echo         self.rows["Voice"].setText(self.live.safe(lambda: self.live.services.get("voice").status(), "unknown"))
echo         self.rows["Vision"].setText(self.live.safe(lambda: self.live.services.get("vision").status(), "unknown"))
echo         self.rows["Git Branch"].setText(self.live.git_branch())
echo         self.rows["Project"].setText(__import__("pathlib").Path.cwd().name)
) > buster\ui\v9\dashboard.py

REM command_palette.py
(
echo from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget
echo from buster.ui.v9.theme import STYLE
echo.
echo class CommandPalette(QDialog):
echo     def __init__(self, parent=None):
echo         super().__init__(parent)
echo         self.setWindowTitle("Command Palette")
echo         self.resize(520,420)
echo         self.setStyleSheet(STYLE)
echo         layout = QVBoxLayout(self)
echo         self.search = QLineEdit()
echo         self.search.setPlaceholderText("Type a command...")
echo         layout.addWidget(self.search)
echo         self.list = QListWidget()
echo         self.list.addItems(["workspace snapshot","git status","python info","approved folders","repo summary","index project","check updates","settings"])
echo         layout.addWidget(self.list)
echo         self.search.textChanged.connect(self.filter)
echo         self.list.itemDoubleClicked.connect(self.accept)
echo.
echo     def filter(self, text):
echo         text = text.lower()
echo         for i in range(self.list.count()):
echo             item = self.list.item(i)
echo             item.setHidden(text not in item.text().lower())
echo.
echo     def selected_command(self):
echo         item = self.list.currentItem()
echo         return item.text() if item else self.search.text().strip()
) > buster\ui\v9\command_palette.py

REM main_window.py
(
echo from PySide6.QtCore import Qt, QTimer
echo from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel
echo from buster.ui.v9.theme import STYLE
echo from buster.ui.v9.live_services import V9LiveServices
echo from buster.ui.v9.sidebar import Sidebar
echo from buster.ui.v9.chat_view import ChatView
echo from buster.ui.v9.face_window import FaceWindow
echo from buster.ui.v9.dashboard import DashboardWindow
echo from buster.ui.v9.command_palette import CommandPalette
echo.
echo class V9MainWindow(QMainWindow):
echo     def __init__(self, services=None, settings=None):
echo         super().__init__()
echo         self.services = services
echo         self.settings = settings
echo         self.live = V9LiveServices(services, settings)
echo         self.face_window = None
echo         self.dashboard_window = None
echo         self.setWindowTitle("Buster v9.0 — Windows AI Desktop Companion")
echo         self.resize(1280,820)
echo         self.setStyleSheet(STYLE)
echo         self.build()
echo         self.timer = QTimer(self)
echo         self.timer.timeout.connect(self.refresh_live)
echo         self.timer.start(2500)
echo.
echo     def build(self):
echo         root = QWidget()
echo         self.setCentralWidget(root)
echo         outer = QHBoxLayout(root)
echo         outer.setContentsMargins(0,0,0,0)
echo         outer.setSpacing(0)
echo         self.sidebar = Sidebar(self.live, self.show_dashboard, self.show_face)
echo         main = QWidget()
echo         ml = QVBoxLayout(main)
echo         ml.setContentsMargins(28,22,28,18)
echo         top = QLabel("Buster Desktop AI OS\nYour AI Development Companion")
echo         top.setObjectName("Title")
echo         ml.addWidget(top)
echo         self.chat = ChatView(self.live, self.refresh_live)
echo         ml.addWidget(self.chat, 1)
echo         footer = QLabel("Context: buster-desktop-companion     Tokens: 1,248     Temp: 0.2")
echo         footer.setObjectName("Small")
echo         ml.addWidget(footer)
echo         outer.addWidget(self.sidebar)
echo         outer.addWidget(main,1)
echo.
echo     def refresh_live(self):
echo         self.sidebar.refresh()
echo.
echo     def show_face(self):
echo         if self.face_window is None:
echo             self.face_window = FaceWindow()
echo         self.face_window.show()
echo         self.face_window.raise_()
echo.
echo     def show_dashboard(self):
echo         if self.dashboard_window is None:
echo             self.dashboard_window = DashboardWindow(self.live)
echo         self.dashboard_window.show()
echo         self.dashboard_window.raise_()
echo.
echo     def keyPressEvent(self, event):
echo         if event.key() == Qt.Key_K and event.modifiers() ^& Qt.ControlModifier:
echo             dlg = CommandPalette(self)
echo             if dlg.exec():
echo                 cmd = dlg.selected_command()
echo                 if cmd:
echo                     self.chat.input.setText(cmd)
echo                     self.chat.send()
echo             return
echo         super().keyPressEvent(event)
) > buster\ui\v9\main_window.py

REM compatibility v9_shell.py
(
echo from buster.ui.v9.main_window import V9MainWindow
echo from buster.ui.v9.face_window import FaceWindow
) > buster\ui\v9\v9_shell.py

echo Modular v9 UI created.
pause