from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
import psutil
from pathlib import Path

class MissionControl(QFrame):
    def __init__(self, live):
        super().__init__()
        self.live = live
        self.setObjectName("Card")
        self.rows = {}
        self.build()

    def build(self):
        layout = QVBoxLayout(self)

        title = QLabel("MISSION CONTROL")
        title.setStyleSheet("font-size:14px; font-weight:bold; color:#20a8ff;")
        layout.addWidget(title)

        for key in ["AI", "Project", "Git", "Voice", "Vision", "CPU", "RAM"]:
            label = QLabel()
            label.setStyleSheet("font-size:13px; color:#b7c9e8;")
            layout.addWidget(label)
            self.rows[key] = label

        self.refresh()

    def refresh(self):
        self.rows["AI"].setText("AI: " + self.live.safe(lambda: self.live.services.get("ai").quick_status(), "unknown"))
        self.rows["Project"].setText("Project: " + Path.cwd().name)
        self.rows["Git"].setText("Git: " + self.live.git_branch())
        self.rows["Voice"].setText("Voice: " + self.live.safe(lambda: self.live.services.get("voice").status(), "unknown"))
        self.rows["Vision"].setText("Vision: " + self.live.safe(lambda: self.live.services.get("vision").status(), "unknown"))
        self.rows["CPU"].setText(f"CPU: {psutil.cpu_percent()}%")
        self.rows["RAM"].setText(f"RAM: {psutil.virtual_memory().percent}%")
