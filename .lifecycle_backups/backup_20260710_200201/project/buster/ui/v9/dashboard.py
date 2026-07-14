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
