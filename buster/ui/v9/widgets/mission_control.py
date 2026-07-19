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
        ai = self.live.ai_info()

        self.rows["AI"].setText(
            f"AI: {ai['provider_label']}"
        )

        self.rows["Project"].setText(
            f"Project: {Path.cwd().name}"
        )

        self.rows["Git"].setText(
            f"Git: {self.live.git_branch()}"
        )

        self.rows["Voice"].setText(
            "Voice: "
            + self.live.safe(
                lambda: self.live.services.get("voice").status(),
                "unknown",
            )
        )

        self.rows["Vision"].setText(
            "Vision: "
            + self.live.safe(
                lambda: self.live.services.get("vision").status(),
                "unknown",
            )
        )

        self.rows["CPU"].setText(
            f"CPU: {psutil.cpu_percent():.1f}%"
        )

        self.rows["RAM"].setText(
            f"RAM: {psutil.virtual_memory().percent:.1f}%"
        )
        
        
        