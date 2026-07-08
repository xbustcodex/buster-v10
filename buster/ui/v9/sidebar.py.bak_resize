from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton
from buster.ui.v9.widgets.mission_control import MissionControl

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

        self.mission = MissionControl(self.live)
        layout.addWidget(self.mission)

    def refresh(self):
        self.quick.setText(self.live.quick_info())
        if hasattr(self, "mission"):
            self.mission.refresh()
