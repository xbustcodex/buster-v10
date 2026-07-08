from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QApplication
from buster.ui.v9.theme import STYLE
from buster.ui.v9.live_services import V9LiveServices
from buster.ui.v9.sidebar import Sidebar
from buster.ui.v9.chat_view import ChatView
from buster.ui.v9.face_window import FaceWindow
from buster.ui.v9.dashboard import DashboardWindow
from buster.ui.v9.command_palette import CommandPalette

class V9MainWindow(QMainWindow):
    def __init__(self, services=None, settings=None):
        super().__init__()
        self.services = services
        self.settings = settings
        self.live = V9LiveServices(services, settings)
        self.face_window = None
        self.current_face_state = 'idle'
        self.dashboard_window = None

        self.setWindowTitle("Buster v9.0 — Windows AI Desktop Companion")
        self.resize(1280, 820)
        self.setStyleSheet(STYLE)
        self.build()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_live)
        self.timer.start(2500)

    def build(self):
        root = QWidget()
        self.setCentralWidget(root)

        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.sidebar = Sidebar(
            self.live,
            on_dashboard=self.show_dashboard,
            on_face=self.show_face,
            on_backend_tools=self.show_backend_tools,
            on_projects=self.show_projects,
            on_workspace=self.show_workspace,
            on_vision=self.show_vision,
            on_voice=self.show_voice,
            on_agents=self.show_agents,
            on_terminal=self.show_terminal,
            on_settings=self.show_settings,
            on_developer_checklist=self.show_developer_checklist,
        )

        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(28, 22, 28, 18)

        title = QLabel("Buster Desktop AI OS\nYour AI Development Companion")
        title.setObjectName("Title")
        main_layout.addWidget(title)

        self.chat = ChatView(self.live, self.refresh_live, self.set_face_state)
        main_layout.addWidget(self.chat, 1)

        footer = QLabel("Context: buster-desktop-companion     Tokens: 1,248     Temp: 0.2")
        footer.setObjectName("Small")
        main_layout.addWidget(footer)

        outer.addWidget(self.sidebar)
        outer.addWidget(main, 1)

    def refresh_live(self):
        self.sidebar.refresh()

    def show_face(self):
        if self.face_window is None:
            self.face_window = FaceWindow()
        self.face_window.set_state(self.current_face_state)
        self.face_window.show()
        self.face_window.raise_()
        
    def _show_tool_window(self, title, widget_cls, width=900, height=650):
        window = widget_cls()
        window.setWindowTitle(title)
        window.resize(width, height)
        window.show()
        window.raise_()

        self.tool_windows = getattr(self, "tool_windows", [])
        self.tool_windows.append(window)
        return window


    def _show_message_tool(self, title, message):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton

        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(520, 320)
        dlg.setStyleSheet(STYLE)

        layout = QVBoxLayout(dlg)

        heading = QLabel(title)
        heading.setObjectName("Title")
        layout.addWidget(heading)

        body = QLabel(message)
        body.setWordWrap(True)
        layout.addWidget(body)

        close = QPushButton("Close")
        close.clicked.connect(dlg.accept)
        layout.addWidget(close)

        dlg.exec()
 

    def show_projects(self):
        try:
            from buster.ui.v9.panels.project_panel import ProjectPanel
            self._show_tool_window("Projects", lambda: ProjectPanel(self.live), 900, 650)
        except Exception as e:
            self._show_message_tool("Projects", f"Projects panel error:\n{e}")


    def show_workspace(self):
        try:
            from buster.ui.v9.panels.workspace_panel import WorkspacePanel
            self._show_tool_window("Workspace", lambda: WorkspacePanel(self.live), 900, 650)
        except Exception as e:
            self._show_message_tool("Workspace", f"Workspace panel error:\n{e}")


    def show_vision(self):
        try:
            from buster.ui.widgets.vision_window import VisionWindow
            self._show_tool_window("Vision", VisionWindow, 900, 650)
        except Exception as e:
            self._show_message_tool(
                "Vision",
                f"Vision tools are available but the panel failed to open:\n{e}"
            )


    def show_voice(self):
        status = self.live.safe(
            lambda: self.live.services.get("voice").status(),
            "Voice service not connected."
        )
        self._show_message_tool("Voice", f"Voice status:\n\n{status}")


    def show_agents(self):
        status = self.live.safe(
            lambda: self.live.services.get("agents").status(),
            "Agent service not connected."
        )
        self._show_message_tool("Agents", f"Agents status:\n\n{status}")


    def show_terminal(self):
        self._show_message_tool(
            "Terminal",
            "Terminal panel placeholder.\n\nNext step: connect this to the runtime command console."
        )


    def show_settings(self):
        try:
            from buster.ui.settings_dialog import SettingsDialog
            dlg = SettingsDialog(self)
            dlg.exec()
        except Exception as e:
            self._show_message_tool("Settings", f"Settings dialog error:\n{e}")    

    def set_face_state(self, state):
        print("FACE STATE:", state)
        self.current_face_state = state

        if self.face_window is None:
            self.face_window = FaceWindow()
            self.face_window.show()

        self.face_window.set_state(state)
        self.face_window.raise_()
        QApplication.processEvents()

    def show_dashboard(self):
        if self.dashboard_window is None:
            self.dashboard_window = DashboardWindow(self.live)
        self.dashboard_window.show()
        self.dashboard_window.raise_()
        
    def show_backend_tools(self):
        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QLabel,
            QPushButton,
            QFrame,
            QMessageBox,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("Backend Tools")
        dlg.resize(420, 420)
        dlg.setStyleSheet(STYLE)

        layout = QVBoxLayout(dlg)

        title = QLabel("🧰 Backend Tools")
        title.setObjectName("Title")
        layout.addWidget(title)

        subtitle = QLabel("Runtime and developer panels")
        subtitle.setObjectName("Small")
        layout.addWidget(subtitle)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        layout.addWidget(divider)

        tools = [
            (
                "Runtime Dashboard",
                "buster.ui.v9.panels.runtime_overview_panel",
                "MissionControlRuntimeDashboard",
            ),
            (
                "Runtime Console",
                "buster.ui.v9.panels.runtime_console_panel",
                "RuntimeConsole",
            ),
            (
                "Mission Control",
                "buster.ui.v9.panels.mission_control_panel",
                "MissionControlV12",
            ),
            (
                "Live Runtime UI",
                "buster.ui.v9.panels.live_runtime_ui",
                "BusterLiveRuntimeUI",
            ),
        ]

        self.backend_windows = getattr(self, "backend_windows", [])

        for title, module_name, class_name in tools:
            btn = QPushButton(f"Open {title}")

            def open_tool(_, title=title, module_name=module_name, class_name=class_name):
                try:
                    module = __import__(module_name, fromlist=[class_name])
                    cls = getattr(module, class_name)

                    window = cls()
                    window.setWindowTitle(title)
                    window.resize(1200, 750)
                    window.setAttribute(Qt.WA_DeleteOnClose, True)

                    window.destroyed.connect(
                        lambda _, w=window: self.backend_windows.remove(w)
                        if w in self.backend_windows else None
                    )

                    window.show()
                    window.raise_()
                    self.backend_windows.append(window)
                except Exception as e:
                    QMessageBox.critical(self, "Backend Tool Error", str(e))

            btn.clicked.connect(open_tool)
            layout.addWidget(btn)

        layout.addStretch()
        dlg.exec()
        
    def show_developer_checklist(self):
        from buster.ui.v9.panels.developer_checklist_panel import DeveloperChecklistPanel
        self._show_tool_window(
            "Developer Checklist",
            lambda: DeveloperChecklistPanel(self.live),
            720,
            620,
        )    

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_K and event.modifiers() & Qt.ControlModifier:
            dlg = CommandPalette(self)
            if dlg.exec():
                cmd = dlg.selected_command()
                if cmd:
                    self.chat.input.setText(cmd)
                    self.chat.send()
            return

        super().keyPressEvent(event)
