# buster/ui/v9/panels/developer_mission_control.py
from __future__ import annotations

from typing import Callable, Optional

import importlib
import inspect

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableView,
    QTextEdit,
    QTreeView,
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
        
        self.setStyleSheet(
            """
            QWidget {
                background:#0B1726;
                color:#EAF2FF;
                font-family:"Segoe UI";
            }
            QPushButton {
                background:#16304A;
                color:#E4EEF8;
                border:1px solid #15324E;
                border-radius:5px;
                padding:5px 12px;
                font-size:11px;
                font-weight:600;
            }
            QPushButton:hover {
                background:#1C4163;
                color:#23B8FF;
            }
            """
        )
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

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
    Unified Buster developer environment with robust pop-out pane handling and explicit dark-themed UI components.
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
        self._full_page_views = {"Plugins", "Integration Hub"}
        self._terminal_docked_sizes = [620, 180]

        self.setWindowTitle("Buster Developer Mission Control")
        self.resize(1200, 800)
        self.setObjectName("DeveloperMissionControl")
        
        # Scoped stylesheet ensuring shell widgets don't accidentally leak unwanted background properties into specific cards
        self.setStyleSheet(
            """
            QWidget#DeveloperMissionControl {
                background:#0B1726;
                color:#EAF2FF;
                font-family:"Segoe UI";
            }

            QWidget#DeveloperMissionControl QListWidget {
                background:#0E1D2E;
                color:#EAF2FF;
                border:none;
                border-right:1px solid #15324E;
                outline:none;
                padding:8px;
                font-size:13px;
                font-weight:600;
            }

            QWidget#DeveloperMissionControl QListWidget::item {
                background:#16304A;
                color:#EAF2FF;
                padding:10px 9px;
                border-radius:7px;
                margin:3px 0;
                border:1px solid #15324E;
            }

            QWidget#DeveloperMissionControl QListWidget::item:hover {
                background:#1C4163;
                color:#23B8FF;
                border:1px solid #23B8FF;
            }

            QWidget#DeveloperMissionControl QListWidget::item:selected {
                background:#20527A;
                color:#23B8FF;
                font-weight:bold;
                border:1px solid #23B8FF;
            }

            QWidget#DeveloperMissionControl QSplitter::handle {
                background:#173955;
            }

            QWidget#DeveloperMissionControl QPushButton {
                background:#16304A;
                color:#E4EEF8;
                border:1px solid #15324E;
                border-radius:5px;
                padding:5px 12px;
                font-size:11px;
                font-weight:600;
            }

            QWidget#DeveloperMissionControl QPushButton:hover {
                background:#1C4163;
                color:#23B8FF;
            }
            """
        )

        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(18, 14, 18, 12)

        title_box = QVBoxLayout()
        title = QLabel("BUSTER DEVELOPER MISSION CONTROL")
        title.setStyleSheet("color:#23B8FF;font-size:20px;font-weight:800;letter-spacing:1px;background:transparent;")

        subtitle = QLabel("Projects · Runtime · Agents · Plugins · Terminal · Intelligence · Security")
        subtitle.setStyleSheet("color:#AFC6DF;font-size:11px;background:transparent;")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header.addLayout(title_box)
        header.addStretch()

        self.status_label = QLabel("● Runtime connected")
        self.status_label.setStyleSheet("color:#31D158;font-size:12px;font-weight:700;background:transparent;")
        header.addWidget(self.status_label)

        root.addLayout(header)

        outer_splitter = QSplitter(Qt.Horizontal)
        root.addWidget(outer_splitter, 1)

        self.navigation = QListWidget()
        self.navigation.setFixedWidth(170)
        outer_splitter.addWidget(self.navigation)

        self.centre_splitter = QSplitter(Qt.Vertical)
        outer_splitter.addWidget(self.centre_splitter)

        workspace_container = QWidget()
        workspace_container.setStyleSheet("background:#0B1726;")
        workspace_layout = QVBoxLayout(workspace_container)
        workspace_layout.setContentsMargins(8, 0, 8, 4)
        workspace_layout.setSpacing(0)

        ws_header = QHBoxLayout()
        ws_header.setContentsMargins(8, 4, 12, 4)
        ws_header.addStretch()
        self.popout_page_btn = QPushButton("Popout Active View ↗")
        self.popout_page_btn.clicked.connect(self._popout_active_page)
        ws_header.addWidget(self.popout_page_btn)
        workspace_layout.addLayout(ws_header)

        self.stack = QStackedWidget()
        self.stack.setMinimumHeight(320)
        self.stack.setStyleSheet("background:transparent;")
        workspace_layout.addWidget(self.stack, 1)
        self.centre_splitter.addWidget(workspace_container)

        terminal_container = QWidget()
        terminal_container.setStyleSheet("background:#0B1726;")
        term_layout = QVBoxLayout(terminal_container)
        term_layout.setContentsMargins(0, 0, 0, 0)
        term_layout.setSpacing(0)

        term_header = QHBoxLayout()
        term_header.setContentsMargins(12, 4, 12, 4)
        term_lbl = QLabel("RUNTIME TERMINAL")
        term_lbl.setStyleSheet("color:#AFC6DF;font-size:11px;font-weight:700;background:transparent;")
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
        self.terminal_container.setMinimumHeight(90)
        self.centre_splitter.addWidget(self.terminal_container)
        self.centre_splitter.setChildrenCollapsible(True)
        self.centre_splitter.setStretchFactor(0, 4)
        self.centre_splitter.setStretchFactor(1, 1)
        self.centre_splitter.setSizes(self._terminal_docked_sizes)

        outer_splitter.setSizes([170, 1030])

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
            ("Projects", self._create_projects_page),
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
            ("Workspace", self._create_workspace_page),
            (
                "Vision",
                lambda: self._create_tool_page(
                    "Vision",
                    "buster.ui.v9.panels.vision.vision_panel",
                    "VisionPanel",
                    fallback_text="Vision panel module could not be found. Check if it's named vision_panel.py directly in panels.",
                ),
            ),
            (
                "Voice",
                lambda: self._create_tool_page(
                    "Voice",
                    "buster.ui.v9.panels.voice.voice_panel",
                    "VoicePanel",
                    fallback_text="Voice panel module could not be found. Check if it's named voice_panel.py directly in panels.",
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

        sizes = self.centre_splitter.sizes()
        if len(sizes) == 2 and sizes[1] > 0:
            self._terminal_docked_sizes = sizes

        self.terminal_container.hide()
        win = PopoutWindow(self.terminal_widget, "Runtime Terminal", self)
        win.window_closed.connect(self._redock_terminal)
        self._popouts["terminal"] = win
        win.show()

    def _redock_terminal(self, widget: QWidget) -> None:
        if "terminal" in self._popouts:
            del self._popouts["terminal"]

        self.terminal_container.layout().addWidget(widget)

        current_item = self.navigation.currentItem()
        current_name = current_item.text() if current_item else ""

        if current_name in self._full_page_views:
            self.terminal_container.hide()
            self.centre_splitter.setSizes([1, 0])
        else:
            self.terminal_container.show()
            self.centre_splitter.setSizes(self._terminal_docked_sizes)

    def _popout_active_page(self) -> None:
        current_item = self.navigation.currentItem()
        if not current_item:
            return
        
        name = current_item.text()
        page = self._pages.get(name)
        if not page or name in self._popouts:
            return

        self.stack.removeWidget(page)

        win = PopoutWindow(page, name, self)
        win.window_closed.connect(lambda w, n=name: self._redock_active_page(w, n))
        self._popouts[name] = win
        win.show()

    def _redock_active_page(self, widget: QWidget, name: str) -> None:
        if name in self._popouts:
            del self._popouts[name]
        
        self.stack.addWidget(widget)
        self._pages[name] = widget
        self.stack.setCurrentWidget(widget)

    def _create_runtime_page(self) -> QWidget:
        return RuntimeWorkspace(
            runtime_core=self.runtime_core,
            live=self.live,
        )

    def _create_projects_page(self) -> QWidget:
        page = self._create_tool_page(
            "Projects",
            "buster.ui.v9.panels.project_panel",
            "ProjectPanel",
        )
        return self._apply_light_work_surface(page, "Projects")

    def _create_workspace_page(self) -> QWidget:
        page = self._create_tool_page(
            "Workspace",
            "buster.ui.v9.panels.workspace_panel",
            "WorkspacePanel",
        )
        return self._apply_light_work_surface(page, "Workspace")

    def _apply_light_work_surface(
        self,
        page: QWidget,
        page_name: str,
    ) -> QWidget:
        """
        Give Projects and Workspace an IDE-style light work surface while
        leaving the Developer Mission Control shell and terminal dark.
        """
        page.setObjectName(f"{page_name}LightSurface")
        page.setAttribute(Qt.WA_StyledBackground, True)

        page.setStyleSheet(
            f"""
            QWidget#{page_name}LightSurface {{
                background:#F4F6F9;
                color:#18202A;
                font-family:"Segoe UI";
            }}

            QWidget#{page_name}LightSurface QWidget {{
                color:#18202A;
            }}

            QWidget#{page_name}LightSurface QFrame,
            QWidget#{page_name}LightSurface QScrollArea,
            QWidget#{page_name}LightSurface QScrollArea > QWidget > QWidget {{
                background:#FFFFFF;
                color:#18202A;
                border-color:#D6DDE6;
            }}

            QWidget#{page_name}LightSurface QLabel {{
                background:transparent;
                color:#18202A;
            }}

            QWidget#{page_name}LightSurface QTreeView,
            QWidget#{page_name}LightSurface QListView,
            QWidget#{page_name}LightSurface QListWidget,
            QWidget#{page_name}LightSurface QTableView,
            QWidget#{page_name}LightSurface QTextEdit,
            QWidget#{page_name}LightSurface QPlainTextEdit,
            QWidget#{page_name}LightSurface QLineEdit {{
                background:#FFFFFF;
                color:#18202A;
                border:1px solid #D6DDE6;
                selection-background-color:#CFE8FF;
                selection-color:#102030;
                alternate-background-color:#F7F9FC;
            }}

            QWidget#{page_name}LightSurface QTreeView::item,
            QWidget#{page_name}LightSurface QListView::item,
            QWidget#{page_name}LightSurface QListWidget::item {{
                color:#18202A;
                background:transparent;
                padding:3px;
            }}

            QWidget#{page_name}LightSurface QTreeView::item:hover,
            QWidget#{page_name}LightSurface QListView::item:hover,
            QWidget#{page_name}LightSurface QListWidget::item:hover {{
                background:#EAF4FF;
            }}

            QWidget#{page_name}LightSurface QTreeView::item:selected,
            QWidget#{page_name}LightSurface QListView::item:selected,
            QWidget#{page_name}LightSurface QListWidget::item:selected {{
                background:#CFE8FF;
                color:#102030;
            }}

            QWidget#{page_name}LightSurface QHeaderView::section {{
                background:#EEF2F6;
                color:#18202A;
                border:0;
                border-right:1px solid #D6DDE6;
                border-bottom:1px solid #D6DDE6;
                padding:6px;
                font-weight:700;
            }}

            QWidget#{page_name}LightSurface QPushButton {{
                background:#F3F5F7;
                color:#18202A;
                border:1px solid #C8D0DA;
                border-radius:6px;
                padding:6px 12px;
                font-size:11px;
                font-weight:600;
            }}

            QWidget#{page_name}LightSurface QPushButton:hover {{
                background:#E7EEF6;
                border-color:#7EBBEE;
                color:#0B5FA5;
            }}

            QWidget#{page_name}LightSurface QPushButton:pressed {{
                background:#D9E8F5;
            }}

            QWidget#{page_name}LightSurface QSplitter::handle {{
                background:#D6DDE6;
            }}

            QWidget#{page_name}LightSurface QScrollBar:vertical {{
                background:#F1F3F6;
                width:12px;
                margin:0;
            }}

            QWidget#{page_name}LightSurface QScrollBar::handle:vertical {{
                background:#B9C4D0;
                min-height:24px;
                border-radius:5px;
                margin:2px;
            }}

            QWidget#{page_name}LightSurface QScrollBar:horizontal {{
                background:#F1F3F6;
                height:12px;
                margin:0;
            }}

            QWidget#{page_name}LightSurface QScrollBar::handle:horizontal {{
                background:#B9C4D0;
                min-width:24px;
                border-radius:5px;
                margin:2px;
            }}
            """
        )

        return page

    def _create_tool_page(
        self,
        title: str,
        module_name: str,
        class_name: str,
        fallback_text: Optional[str] = None,
    ) -> QWidget:
        """
        Import and construct a panel without assuming one fixed constructor.

        Constructor parameters are matched by name first. Compatibility
        fallbacks are then attempted independently so one bad call does not
        prevent a valid constructor from being tried.
        """
        errors: list[str] = []

        try:
            module = importlib.import_module(module_name)
            cls = getattr(module, class_name)
        except Exception as exc:
            return self._fallback_page(
                title,
                fallback_text
                or (
                    f"{title} could not be imported.\n\n"
                    f"{module_name}.{class_name}\n{exc}"
                ),
            )

        # Prefer explicit keyword construction based on the panel signature.
        try:
            signature = inspect.signature(cls)
            kwargs = {}

            for name, parameter in signature.parameters.items():
                if name == "self":
                    continue
                if name in {"runtime_core", "runtime", "core"}:
                    kwargs[name] = self.runtime_core
                elif name in {"live", "live_services", "services"}:
                    kwargs[name] = self.live
                elif name == "parent":
                    kwargs[name] = self

            widget = cls(**kwargs)
            if isinstance(widget, QWidget):
                return widget

            errors.append(
                f"keyword constructor returned {type(widget).__name__}"
            )
        except Exception as exc:
            errors.append(f"keyword constructor: {exc}")

        constructors: list[tuple[str, Callable[[], QWidget]]] = [
            (
                "live, runtime_core",
                lambda: cls(self.live, self.runtime_core),
            ),
            (
                "runtime_core, live",
                lambda: cls(self.runtime_core, self.live),
            ),
            ("runtime_core", lambda: cls(self.runtime_core)),
            ("live", lambda: cls(self.live)),
            ("parent", lambda: cls(parent=self)),
            ("empty", lambda: cls()),
        ]

        for label, constructor in constructors:
            try:
                widget = constructor()
                if isinstance(widget, QWidget):
                    return widget
                errors.append(
                    f"{label}: returned {type(widget).__name__}"
                )
            except Exception as exc:
                errors.append(f"{label}: {exc}")

        details = "\n".join(f"• {error}" for error in errors)
        return self._fallback_page(
            title,
            fallback_text
            or (
                f"{title} could not be created.\n\n"
                f"{module_name}.{class_name}\n\n"
                f"Attempts:\n{details}"
            ),
        )

    def _fallback_page(self, title: str, message: str) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background:#102238; color:#F4F8FC;")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)

        heading = QLabel(title.upper())
        heading.setStyleSheet("color:#23B8FF;font-size:20px;font-weight:800;background:transparent;")

        body = QLabel(message)
        body.setWordWrap(True)
        body.setStyleSheet("color:#D0E1F2;font-size:13px;background:transparent;")

        layout.addWidget(heading)
        layout.addWidget(body)
        layout.addStretch()
        return page

    def _change_page(self, index: int) -> None:
        if not 0 <= index < self.navigation.count():
            return

        item = self.navigation.item(index)
        if item is None:
            return

        page_name = item.text()
        page = self._pages.get(page_name)
        if page is None:
            return

        self.stack.setCurrentWidget(page)
        self._update_terminal_visibility(page_name)

    def _update_terminal_visibility(self, page_name: str) -> None:
        """
        Hide the shared terminal on full-page plugin workspaces.

        Plugins and Integration Hub receive the full vertical centre area.
        The terminal returns to its previous splitter height on all other
        pages, unless it is currently popped out into a separate window.
        """
        if page_name in self._full_page_views:
            if self.terminal_container.isVisible():
                sizes = self.centre_splitter.sizes()
                if len(sizes) == 2 and sizes[1] > 0:
                    self._terminal_docked_sizes = sizes

            self.terminal_container.hide()
            self.centre_splitter.setSizes([1, 0])
            return

        if "terminal" in self._popouts:
            self.terminal_container.hide()
            self.centre_splitter.setSizes([1, 0])
            return

        self.terminal_container.show()

        if (
            len(self._terminal_docked_sizes) != 2
            or self._terminal_docked_sizes[1] <= 0
        ):
            self._terminal_docked_sizes = [620, 180]

        self.centre_splitter.setSizes(self._terminal_docked_sizes)
