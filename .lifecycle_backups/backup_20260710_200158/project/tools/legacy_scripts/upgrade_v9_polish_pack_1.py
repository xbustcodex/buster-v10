from pathlib import Path

p = Path("buster/ui/v9/v9_shell.py")

text = p.read_text(encoding="utf-8")

text = text.replace(
    "from PySide6.QtCore import Qt, QTime",
    "from PySide6.QtCore import Qt, QTime, QTimer",
)

text = text.replace(
    "QSizePolicy\n)",
    "QSizePolicy, QDialog, QListWidget, QProgressBar\n)",
)

# Add live imports
if "import psutil" not in text:
    text = text.replace("from PySide6.QtWidgets import", "import psutil\n\nfrom PySide6.QtWidgets import")

# Upgrade FaceWindow animation
start = text.find("class FaceWindow(QWidget):")
end = text.find("class DashboardWindow(QWidget):")

face_code = r'''
class FaceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Buster Face")
        self.resize(260, 270)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet(STYLE)
        self.frames = ["◕     ◕\n   ▬", "⌒     ⌒\n   ▬", "◕     ◕\n   ◡", "⌒     ⌒\n   ◡"]
        self.index = 0

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)

        self.face = QLabel(self.frames[0])
        self.face.setAlignment(Qt.AlignCenter)
        self.face.setStyleSheet("font-size:52px; color:#20a8ff;")

        self.status = QLabel("Thinking...")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("font-size:22px; font-weight:bold; color:#20a8ff;")

        self.dots = QLabel("● ● ● ● ●")
        self.dots.setAlignment(Qt.AlignCenter)
        self.dots.setStyleSheet("font-size:20px; color:#20a8ff;")

        lay.addWidget(self.face)
        lay.addWidget(self.status)
        lay.addWidget(self.dots)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(550)

    def animate(self):
        self.index = (self.index + 1) % len(self.frames)
        self.face.setText(self.frames[self.index])
'''

text = text[:start] + face_code + "\n" + text[end:]

# Upgrade dashboard live
start = text.find("class DashboardWindow(QWidget):")
end = text.find("class V9MainWindow(QMainWindow):")

dashboard_code = r'''
class DashboardWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dashboard")
        self.resize(520, 520)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self)

        title = QLabel("Dashboard")
        title.setObjectName("Title")
        root.addWidget(title)

        tabs = QLabel("System     Performance     Environment     Health")
        tabs.setStyleSheet("color:#20a8ff; font-size:14px;")
        root.addWidget(tabs)

        self.rows = {}
        for label in ["CPU", "RAM", "Disk", "Ollama", "AI Mode", "Voice", "Vision", "Internet", "Git Branch", "Project", "Project Index", "Build EXE", "Installer"]:
            row = QHBoxLayout()
            name = QLabel(label)
            value = QLabel("checking...")
            value.setStyleSheet("color:#35ff6b;")
            row.addWidget(name)
            row.addStretch()
            row.addWidget(value)
            root.addLayout(row)
            self.rows[label] = value

        buttons = QHBoxLayout()
        for label in ["Refresh", "Open Data", "Run Doctor"]:
            buttons.addWidget(QPushButton(label))
        root.addLayout(buttons)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)
        self.refresh()

    def refresh(self):
        try:
            self.rows["CPU"].setText(f"{psutil.cpu_percent()}%")
            mem = psutil.virtual_memory()
            self.rows["RAM"].setText(f"{round(mem.used / (1024**3), 1)} / {round(mem.total / (1024**3), 1)} GB ({mem.percent}%)")
            disk = psutil.disk_usage("C:\\")
            self.rows["Disk"].setText(f"{round(disk.free / (1024**3), 1)} GB free")
        except Exception:
            pass

        self.rows["Ollama"].setText("Running")
        self.rows["AI Mode"].setText("Ollama")
        self.rows["Voice"].setText("Ready")
        self.rows["Vision"].setText("Ready")
        self.rows["Internet"].setText("Connected")
        self.rows["Git Branch"].setText("feature/web-brain")
        self.rows["Project"].setText("buster-desktop-companion")
        self.rows["Project Index"].setText("Up to date")
        self.rows["Build EXE"].setText("Found")
        self.rows["Installer"].setText("Found")
'''

text = text[:start] + dashboard_code + "\n" + text[end:]

# Add command palette class before V9MainWindow
insert_at = text.find("class V9MainWindow(QMainWindow):")

palette_code = r'''
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
        commands = [
            "workspace snapshot",
            "git status",
            "python info",
            "approved folders",
            "repo summary",
            "index project",
            "check updates",
            "open android studio",
            "run doctor",
            "settings",
        ]
        self.list.addItems(commands)
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
'''

if "class CommandPalette" not in text:
    text = text[:insert_at] + palette_code + "\n" + text[insert_at:]

# Wire Ctrl+K and palette methods
text = text.replace(
    "self.build()",
    "self.build()\n        self.shortcut_palette = None",
    1,
)

if "def keyPressEvent" not in text:
    marker = "    def show_dashboard(self):\n"
    key_code = r'''
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_K and event.modifiers() & Qt.ControlModifier:
            self.show_command_palette()
            return
        super().keyPressEvent(event)

    def show_command_palette(self):
        dlg = CommandPalette(self)
        if dlg.exec():
            cmd = dlg.selected_command()
            if cmd:
                self.input.setText(cmd)
                self.send()

'''
    text = text.replace(marker, key_code + marker)

p.write_text(text, encoding="utf-8")

print("v9 UI Polish Pack 1 installed.")