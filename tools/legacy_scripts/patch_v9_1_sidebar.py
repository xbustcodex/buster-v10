from pathlib import Path

p = Path("buster/ui/v9/sidebar.py")
text = p.read_text(encoding="utf-8")

if "MissionControl" not in text:
    text = text.replace(
        "from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton\n",
        "from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton\nfrom buster.ui.v9.widgets.mission_control import MissionControl\n",
    )

text = text.replace(
'''        self.quick = QLabel(self.live.quick_info())
        self.quick.setObjectName("Small")
        self.quick.setStyleSheet("color:#b7c9e8; font-size:13px;")
        layout.addWidget(self.quick)''',
'''        self.quick = QLabel(self.live.quick_info())
        self.quick.setObjectName("Small")
        self.quick.setStyleSheet("color:#b7c9e8; font-size:13px;")
        layout.addWidget(self.quick)

        self.mission = MissionControl(self.live)
        layout.addWidget(self.mission)'''
)

text = text.replace(
'''    def refresh(self):
        self.quick.setText(self.live.quick_info())''',
'''    def refresh(self):
        self.quick.setText(self.live.quick_info())
        if hasattr(self, "mission"):
            self.mission.refresh()'''
)

p.write_text(text, encoding="utf-8")
print("Mission Control wired into sidebar.")
