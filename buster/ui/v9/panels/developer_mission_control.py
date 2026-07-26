from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from buster.ui.v9.panels.runtime_panel.runtime_workspace import RuntimeWorkspace


class PopoutWindow(QWidget):
    """Container window for popped-out panels styled with Buster dark theme."""

    window_closed = Signal(QWidget)

    def __init__(self, widget: QWidget, title: str, parent=None):
        super().__init__(parent, Qt.Window)
        self.widget = widget
        self.setWindowTitle(f"Buster - {title}")
        self.resize(1000, 600)
        
        # Apply the matching Buster dark theme style to popout windows
        self.setStyleSheet(
            """
            QWidget {
                background:#050B14;
                color:#EAF2FF;
                font-family:"Segoe UI";
            }
            QPushButton {
                background:#0A1E34;
                color:#BFD1E7;
                border:1px solid #15324E;
                border-radius:5px;
                padding:5px 12px;
                font-size:11px;
                font-weight:600;
            }
            QPushButton:hover {
                background:#0E2A49;
                color:#23B8FF;
            }
            """
        )
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header bar with Re-dock button
        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 12, 8)
        header.addWidget(QLabel(f"<b>{title.upper()}</b>"))

        self.redock_btn = QPushButton("Dock Back ↙")
        self.redock_btn.setStyleSheet(
            "background: #10253A; color: #23B8FF; border: 1px solid #15324E; padding: 4px 10px; border-radius: 4px;"
        )
        self.redock_btn.clicked.connect(self.close)
        header.addStretch()
        header.addWidget(self.redock_btn)

        layout.addLayout(header)
        layout.addWidget(widget, 1)

    def closeEvent(self, event):
        self.window_closed.emit(self.widget)
        super().closeEvent(event)


class DeveloperMissionControl(QWidget):
    """
    Unified Buster developer environment with pop-out panel capabilities.
    """

    def __init__(
        self,
        runtime_core=None,
        live=None,
        parent=None,
    ):
        super().__init__(parent)

        self.runtime_core = runtime_core
        self.live = live
        self._pages: dict[str, QWidget] = {}
        self._popouts: dict[str, PopoutWindow] = {}

        self.setWindowTitle("Buster Developer Mission Control")
        self.resize(1200, 800)
        self.setObjectName("DeveloperMissionControl")
        self.setStyleSheet(
            """
            QWidget#DeveloperMissionControl {
                background:#050B14;
                color:#EAF2FF;
                font-family:"Segoe UI";
            }

            QListWidget {
                background:#07111D;
                color:#BFD1E7;
                border:none;
                border-right:1px solid #15324E;
                outline:none;
                padding:8px;
                font-size:13px;
                font-weight:600;
            }

            QListWidget::item {
                padding:10px 9px;
                border-radius:7px;
                margin:2px 0;
            }

            QListWidget::item:selected {
                background:#0E2A49;
                color:#23B8FF;
            }

            QSplitter::handle {
                background:#10253A;
            }

            QPushButton {
                background:#0A1E34;
                color:#BFD1E7;
                border:1px solid #15324E;
                border-radius:5px;
                padding:5px 12px;
                font-size:11px;
                font-weight:600;
            }

            QPushButton:hover {
                background:#0E2A49;
                color:#23B8FF;
            }
            """
        )

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top Header Bar
        header = QHBoxLayout()
        header.setContentsMargins(18, 14, 18, 12)

        title_box = QVBoxLayout()
        title = QLabel("BUSTER DEVELOPER MISSION CONTROL")
        title.setStyleSheet("color:#23B8FF;font-size:20px;font-weight:800;letter-spacing:1px;")

        subtitle = QLabel("Projects · Runtime · Agents · Plugins · Terminal · Intelligence · Security")
        subtitle.setStyleSheet("color:#7894B5;font-size:11px;")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header.addLayout(title_box)
        header.addStretch()

        self.status_label = QLabel("● Runtime connected")
        self.status_label.setStyleSheet("color:#31D158;font-size:12px;font-weight:700;")
        header.addWidget(self.status_label)

        root.addLayout(header)

        # Horizontal Splitter: Navigation Menu | Main Workspace
        outer_splitter = QSplitter(Qt.Horizontal)
        root.addWidget(outer_splitter, 1)

        self.navigation = QListWidget()
        self.navigation.setFixedWidth(150)
        outer_splitter.addWidget(self.navigation)

        # Vertical Splitter: Active Page | Bottom Terminal Dock
        self.centre_splitter = QSplitter(Qt.Vertical)
        outer_splitter.addWidget(self.centre_splitter)

        # Workspace Area Container with Popout Header
        workspace_container = QWidget()
        workspace_layout = QVBoxLayout(workspace_container)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        ws_header = QHBoxLayout()
        ws_header.setContentsMargins(8, 4, 12, 4)
        ws_header.addStretch()
        self.popout_page_btn = QPushButton("Popout Active View ↗")
        self.popout_page_btn.clicked.connect(self._popout_active_page)
        ws_header.addWidget(self.popout_page_btn)
        workspace_layout.addLayout(ws_header)

        self.stack = QStackedWidget()
        workspace_layout.addWidget(self.stack, 1)
        self.centre_splitter.addWidget(workspace_container)

        # Terminal Dock Area Container with Popout Header
        terminal_container = QWidget()
        term_layout = QVBoxLayout(terminal_container)
        term_layout.setContentsMargins(0, 0, 0, 0)
        term_layout.setSpacing(0)

        term_header = QHBoxLayout()
        term_header.setContentsMargins(12, 4, 12, 4)
        term_lbl = QLabel("RUNTIME TERMINAL")
        term_lbl.setStyleSheet("color:#7894B5;font-size:11px;font-weight:700;")
        term_header.addWidget(term_lbl)
        term_header.addStretch()

        self.popout_term_btn = QPushButton("Popout Terminal ↗")
        self.popout_term_btn.clicked.connect(self._popout_terminal)
        term_header.addWidget(self.popout_term_btn)
        term_layout.addLayout(term_header)

        self.terminal_widget = self._create_tool_page(
            "Runtime Terminal",
            "buster.ui.v9.panels.terminal_panel",
            "TerminalPanel",
            fallback_text="Runtime terminal is unavailable.",
        )
        term_layout.addWidget(self.terminal_widget, 1)

        self.terminal_container = terminal_container
        self.centre_splitter.addWidget(self.terminal_container)
        self.centre_splitter.setSizes([500, 300])

        outer_splitter.setSizes([150, 1050])

        page_specs = [
            ("Runtime", self._create_runtime_page),
            (
                "Mission Control",
                lambda: self._create_tool_page(
                    "Mission Control",
                    "buster.ui.v9.panels.mission_control.mission_control_panel",
                    "MissionControlPanel",
                ),
            ),
            (
                "Master Security",
                lambda: self._create_tool_page(
                    "Master Security",
                    "buster.ui.v9.panels.master_mission_control.MasterMissionControl",
                    "MasterMissionControl",
                ),
            ),
            (
                "Projects",
                lambda: self._create_tool_page(
                    "Projects",
                    "buster.ui.v9.panels.project_panel",
                    "ProjectPanel",
                ),
            ),
            (
                "Agents",
                lambda: self._create_tool_page(
                    "Agent OS",
                    "buster.ui.v9.panels.agent_panel",
                    "AgentPanel",
                ),
            ),
            (
                "Plugins",
                lambda: self._create_tool_page(
                    "Plugin Manager",
                    "buster.ui.v9.panels.plugin_panel",
                    "PluginPanel",
                ),
            ),
            (
                "Workspace",
                lambda: self._create_tool_page(
                    "Workspace",
                    "buster.ui.v9.panels.workspace_panel",
                    "WorkspacePanel",
                ),
            ),
            (
                "Vision",
                lambda: self._create_tool_page(
                    "Vision",
                    "buster.ui.v9.panels.vision_panel",
                    "VisionPanel",
                ),
            ),
            (
                "Voice",
                lambda: self._create_tool_page(
                    "Voice",
                    "buster.ui.v9.panels.voice_panel",
                    "VoicePanel",
                ),
            ),
            (
                "Settings",
                lambda: self._create_tool_page(
                    "Settings",
                    "buster.ui.v9.panels.settings_panel",
                    "SettingsPanel",
                ),
            ),
            (
                "Integration Hub",
                lambda: self._create_tool_page(
                    "Integration Hub",
                    "buster.ui.v9.panels.integration_hub_panel",
                    "IntegrationHubPanel",
                ),
            ),
        ]

        for name, factory in page_specs:
            page = factory()
            self._pages[name] = page
            self.stack.addWidget(page)
            self.navigation.addItem(QListWidgetItem(name))

        self.navigation.currentRowChanged.connect(self._change_page)
        self.navigation.setCurrentRow(0)

    def _popout_terminal(self) -> None:
        if "terminal" in self._popouts:
            self._popouts["terminal"].raise_()
            return

        self.terminal_container.hide()
        win = PopoutWindow(self.terminal_widget, "Runtime Terminal", self)
        win.window_closed.connect(self._redock_terminal)
        self._popouts["terminal"] = win
        win.show()

    def _redock_terminal(self, widget: QWidget) -> None:
        if "terminal" in self._popouts:
            del self._popouts["terminal"]
        self.terminal_container.layout().addWidget(widget)
        self.terminal_container.show()

    def _popout_active_page(self) -> None:
        current_item = self.navigation.currentItem()
        if not current_item:
            return
        
        name = current_item.text()
        page = self._pages.get(name)
        if not page or name in self._popouts:
            return

        win = PopoutWindow(page, name, self)
        win.window_closed.connect(lambda w, n=name: self._redock_active_page(w, n))
        self._popouts[name] = win
        win.show()

    def _redock_active_page(self, widget: QWidget, name: str) -> None:
        if name in self._popouts:
            del self._popouts[name]
        self.stack.addWidget(widget)
        self.stack.setCurrentWidget(widget)

    def _create_runtime_page(self) -> QWidget:
        return RuntimeWorkspace(
            runtime_core=self.runtime_core,
            live=self.live,
        )

    def _create_tool_page(
        self,
        title: str,
        module_name: str,
        class_name: str,
        fallback_text: Optional[str] = None,
    ) -> QWidget:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)

            constructors: list[Callable[[], QWidget]] = [
                lambda: cls(self.live, self.runtime_core),
                lambda: cls(self.runtime_core, self.live),
                lambda: cls(self.live),
                lambda: cls(self.runtime_core),
                lambda: cls(parent=self),
                lambda: cls(),
            ]

            last_error: Optional[Exception] = None

            for constructor in constructors:
                try:
                    widget = constructor()
                    if isinstance(widget, QWidget):
                        return widget
                except TypeError as exc:
                    last_error = exc

            if last_error is not None:
                raise last_error

        except Exception as exc:
            return self._fallback_page(
                title,
                fallback_text or f"{title} could not be loaded.\n\n{exc}",
            )

        return self._fallback_page(
            title,
            fallback_text or f"{title} returned no widget.",
        )

    def _fallback_page(self, title: str, message: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)

        heading = QLabel(title.upper())
        heading.setStyleSheet("color:#23B8FF;font-size:20px;font-weight:800;")

        body = QLabel(message)
        body.setWordWrap(True)
        body.setStyleSheet("color:#9FB8D5;font-size:13px;")

        layout.addWidget(heading)
        layout.addWidget(body)
        layout.addStretch()
        return page

    def _change_page(self, index: int) -> None:
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)