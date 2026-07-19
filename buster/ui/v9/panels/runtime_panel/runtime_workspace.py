from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTabWidget,
)

from .overview_panel import MissionControlRuntimeDashboard
from .timeline_panel import RuntimeTimelinePanel
from .console_panel import RuntimeConsole
from .live_panel import BusterLiveRuntimeUI
from .inspector_panel import RuntimeInspectorPanel


class RuntimeWorkspace(QWidget):
    """
    Main Runtime Workspace.

    Hosts all Runtime panels using the shared RuntimeCore.

        Overview
        Timeline
        Console
        Live
        Inspector
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

        self.setObjectName("RuntimeWorkspace")

        self.build_ui()

    # ---------------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            5,
            5,
            5,
            5,
        )

        layout.setSpacing(10)

        title = QLabel(
            "Runtime Workspace"
        )

        title.setStyleSheet(
            """
            QLabel{
                color:#23B8FF;
                font-size:16px;
                font-weight:800;
            }
            """
        )

        layout.addWidget(title)

        self.tabs = QTabWidget()

        self.tabs.setDocumentMode(True)

        self.tabs.setMovable(False)

        self.tabs.setTabPosition(
            QTabWidget.North
        )

        layout.addWidget(
            self.tabs,
            1,
        )

        #
        # Panels
        #
        
        self.overview_panel = MissionControlRuntimeDashboard(
            runtime_core=self.runtime_core,
        )

        self.timeline_panel = RuntimeTimelinePanel(
            runtime_core=self.runtime_core,
        )

        self.console_panel = RuntimeConsole()

        self.live_panel = BusterLiveRuntimeUI()

        self.inspector_panel = RuntimeInspectorPanel(
            runtime_core=self.runtime_core,
        )


        #
        # Tabs
        #

        self.tabs.addTab(
            self.overview_panel,
            "Overview",
        )

        self.tabs.addTab(
            self.timeline_panel,
            "Timeline",
        )

        self.tabs.addTab(
            self.console_panel,
            "Console",
        )

        self.tabs.addTab(
            self.live_panel,
            "Live",
        )

        self.tabs.addTab(
            self.inspector_panel,
            "Inspector",
        )

        self.tabs.currentChanged.connect(
            self.tab_changed,
        )

    # ---------------------------------------------------------

    def tab_changed(
        self,
        index: int,
    ):

        widget = self.tabs.widget(index)

        if widget is None:
            return

        #
        # refresh panel if supported
        #

        if hasattr(widget, "refresh"):

            try:
                widget.refresh()
            except Exception:
                pass

        elif hasattr(widget, "reload_history"):

            try:
                widget.reload_history()
            except Exception:
                pass

    # ---------------------------------------------------------

    def refresh(self):

        for panel in (
            self.overview_panel,
            self.timeline_panel,
            self.console_panel,
            self.live_panel,
            self.inspector_panel,
        ):

            try:

                if hasattr(panel, "refresh"):
                    panel.refresh()

                elif hasattr(panel, "reload_history"):
                    panel.reload_history()

            except Exception:
                pass

    # ---------------------------------------------------------

    def shutdown(self):

        for panel in (
            self.overview_panel,
            self.timeline_panel,
            self.console_panel,
            self.live_panel,
            self.inspector_panel,
        ):

            try:

                if hasattr(panel, "shutdown"):
                    panel.shutdown()

            except Exception:
                pass

    # ---------------------------------------------------------

    def closeEvent(
        self,
        event,
    ):

        self.shutdown()

        super().closeEvent(event)