from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton, QComboBox
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
        on_tasks=None,
        on_terminal=None,
        on_settings=None,
        on_developer_checklist=None,
        on_notifications=None,
        on_runtime_timeline=None,
        on_self_improvement=None,
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
        self.on_tasks = on_tasks
        self.on_terminal = on_terminal
        self.on_settings = on_settings
        self.on_developer_checklist = on_developer_checklist
        self.on_notifications = on_notifications
        self.on_runtime_timeline = on_runtime_timeline
        self.on_self_improvement = on_self_improvement
        self.setObjectName("Sidebar")
        self.setMinimumWidth(190)
        self.setMaximumWidth(220)
        self.build()

    def build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(6)

        logo = QLabel("🅱  BUSTER")
        logo.setObjectName("Logo")
        layout.addWidget(logo)

        sub = QLabel("v10.4 Buster Desktop AI OS")
        sub.setObjectName("Small")
        layout.addWidget(sub)

        layout.addSpacing(8)

        # Main active status tab remains visible to orient the workspace
        active_chat_btn = QPushButton("💬  Chat Active")
        active_chat_btn.setObjectName("Active")
        layout.addWidget(active_chat_btn)

        # Dropdown Navigation Panel
        self.nav_dropdown = QComboBox()
        self.nav_dropdown.setObjectName("NavDropdown")
        
        # Mapping drop options directly to callbacks
        self.nav_mapping = {
            "⚡ Select Tools / Panels...": lambda: None,
            "🏠  Dashboard": self.on_dashboard,
            "📋  Tasks & Agents": self.on_tasks,
            "📁  Projects": self.on_projects,
            "🧠  Workspace": self.on_workspace,
            "🧠  Self Improvement": self.on_self_improvement,
            "👁  Vision": self.on_vision,
            "🔊  Voice": self.on_voice,
            "🤖  Agents": self.on_agents,
            "🖥  Terminal": self.on_terminal,
            "🔔  Notifications": self.on_notifications,
            "📜  Runtime Timeline": self.on_runtime_timeline,
            "🛠  Developer Tools": self.on_backend_tools,
            "🛠  Developer Checklist": self.on_developer_checklist,
            "⚙  Settings": self.on_settings,
            "😊  Face Popup": self.on_face,
        }

        self.nav_dropdown.addItems(list(self.nav_mapping.keys()))
        self.nav_dropdown.currentIndexChanged.connect(self._handle_navigation)
        layout.addWidget(self.nav_dropdown)

        # Generous breathing gap for layout assets
        layout.addSpacing(16)

        quick_title = QLabel("QUICK INFO")
        quick_title.setObjectName("Small")
        layout.addWidget(quick_title)

        self.quick = QLabel(self.live.quick_info())
        self.quick.setObjectName("Small")
        self.quick.setWordWrap(True)
        self.quick.setStyleSheet("color:#b7c9e8; font-size:12px; margin-bottom: 4px;")
        layout.addWidget(self.quick)

        self.mission = MissionControl(self.live)
        layout.addWidget(self.mission)

        layout.addStretch()

    def _handle_navigation(self, index):
        """Executes targeted window frames and cleanly resets dropdown choice."""
        text = self.nav_dropdown.itemText(index)
        callback = self.nav_mapping.get(text)
        
        if callback and index != 0:
            try:
                callback()
            except Exception as e:
                print(f"Navigation selection failed: {e}")
            
            # Auto-reset to default view option after action triggers
            self.nav_dropdown.setCurrentIndex(0)

    def refresh(self):
        self.quick.setText(self.live.quick_info())
        if hasattr(self, "mission"):
            self.mission.refresh()