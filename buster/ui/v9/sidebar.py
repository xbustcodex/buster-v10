from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton
from buster.ui.v9.widgets.mission_control import MissionControl


class Sidebar(QFrame):
    def __init__(
        self,
        live,
        on_dashboard=None,
        on_face=None,
        on_backend_tools=None,
        on_projects=None,
        on_workspace=None,
        on_vision=None,
        on_voice=None,
        on_agents=None,
        on_terminal=None,
        on_settings=None,
        on_developer_checklist=None,
        on_notifications=None,
        on_runtime_timeline=None,
    ):
        super().__init__()
        self.live = live
        self.on_dashboard = on_dashboard
        self.on_face = on_face
        self.on_backend_tools = on_backend_tools
        self.on_projects = on_projects
        self.on_workspace = on_workspace
        self.on_vision = on_vision
        self.on_voice = on_voice
        self.on_agents = on_agents
        self.on_terminal = on_terminal
        self.on_settings = on_settings
        self.on_developer_checklist = on_developer_checklist
        self.on_notifications = on_notifications
        self.on_runtime_timeline = on_runtime_timeline
        self.setObjectName("Sidebar")
        self.setMinimumWidth(270)
        self.setMaximumWidth(360)
        self.build()
        

    def build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 18)
        layout.setSpacing(10)

        logo = QLabel("🅱  BUSTER")
        logo.setObjectName("Logo")
        layout.addWidget(logo)

        sub = QLabel("v9.0 Desktop AI OS")
        sub.setObjectName("Small")
        layout.addWidget(sub)

        layout.addSpacing(14)

        items = [
            ("🏠  Dashboard", self.on_dashboard),
            ("💬  Chat", None),
            ("📁  Projects", self.on_projects),
            ("🧠  Workspace", self.on_workspace),
            ("👁  Vision", self.on_vision),
            ("🔊  Voice", self.on_voice),
            ("🤖  Agents", self.on_agents),
            ("🖥  Terminal", self.on_terminal),
            ("🔔  Notifications", self.on_notifications),
            ("📜  Runtime Timeline", self.on_runtime_timeline),
            ("🛠  Developer Tools", self.on_backend_tools),
            ("🛠  Developer Checklist", self.on_developer_checklist),
            ("⚙  Settings", self.on_settings),
            ("😊  Face Popup", self.on_face),
        ]

        for label, callback in items:
            btn = QPushButton(label)

            if "Chat" in label:
                btn.setObjectName("Active")

            if callback:
                btn.clicked.connect(callback)

            layout.addWidget(btn)

        layout.addSpacing(12)

        quick_title = QLabel("QUICK INFO")
        quick_title.setObjectName("Small")
        layout.addWidget(quick_title)

        self.quick = QLabel(self.live.quick_info())
        self.quick.setObjectName("Small")
        self.quick.setWordWrap(True)
        self.quick.setStyleSheet("color:#b7c9e8; font-size:12px;")
        layout.addWidget(self.quick)

        self.mission = MissionControl(self.live)
        layout.addWidget(self.mission)

        layout.addStretch()

    def refresh(self):
        self.quick.setText(self.live.quick_info())
        if hasattr(self, "mission"):
            self.mission.refresh()