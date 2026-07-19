from __future__ import annotations

import json
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QLabel,
    QSplitter,
)

from PySide6.QtGui import QTextCursor


class RuntimeInspectorPanel(QWidget):
    """
    Runtime Inspector UI

    Displays RuntimeInspector data:

        runtime
        dispatcher
        registry
        sdk
        services
        agents
        jobs
        workflow
        orchestrator
        blackboard
        memory
        health
        statistics
        diagnostics
        snapshot
    """

    SECTIONS = [
        ("Runtime", "runtime_summary"),
        ("Runtime Engine", "runtime"),
        ("Dispatcher", "dispatcher"),
        ("Registry", "registry"),
        ("SDK", "sdk"),
        ("Services", "services"),
        ("Agents", "agents"),
        ("Jobs", "jobs"),
        ("Workflow", "workflow"),
        ("Orchestrator", "orchestrator"),
        ("Blackboard", "blackboard"),
        ("Agent Memory", "agent_memory"),
        ("Health", "health"),
        ("Statistics", "statistics"),
        ("Diagnostics", "diagnostics"),
        ("Snapshot", "snapshot"),
    ]

    def __init__(
        self,
        runtime_core=None,
        parent=None,
    ):
        super().__init__(parent)

        self.runtime_core = runtime_core

        self.current_section = "snapshot"

        self.build_ui()

        self.start_refresh()

    # -------------------------------------------------

    def build_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            10,
            10,
            10,
            10,
        )

        header = QHBoxLayout()

        self.title = QLabel(
            "Runtime Inspector"
        )

        self.refresh_button = QPushButton(
            "🔄 Refresh"
        )

        self.copy_button = QPushButton(
            "📋 Copy JSON"
        )

        self.refresh_button.clicked.connect(
            self.refresh
        )

        self.copy_button.clicked.connect(
            self.copy_json
        )

        header.addWidget(self.title)

        header.addStretch()

        header.addWidget(
            self.refresh_button
        )

        header.addWidget(
            self.copy_button
        )

        layout.addLayout(header)

        splitter = QSplitter(
            Qt.Horizontal
        )

        self.menu = QListWidget()

        for name, method in self.SECTIONS:

            item = QListWidgetItem(name)

            item.setData(
                Qt.UserRole,
                method,
            )

            self.menu.addItem(item)

        self.menu.currentItemChanged.connect(
            self.section_changed
        )

        self.viewer = QPlainTextEdit()

        self.viewer.setReadOnly(True)

        self.viewer.setStyleSheet(
            """
            QPlainTextEdit {
                background:#07111d;
                color:#d9e7ff;
                font-family:Consolas;
                font-size:12px;
            }
            """
        )

        splitter.addWidget(
            self.menu
        )

        splitter.addWidget(
            self.viewer
        )

        splitter.setStretchFactor(
            1,
            1,
        )

        layout.addWidget(
            splitter
        )

        self.status = QLabel(
            "Ready"
        )

        layout.addWidget(
            self.status
        )

        self.menu.setCurrentRow(
            0
        )

    # -------------------------------------------------

    def section_changed(
        self,
        current,
        previous=None,
    ):

        if not current:
            return

        self.current_section = current.data(
            Qt.UserRole
        )

        self.refresh()

    # -------------------------------------------------

    def refresh(self):

        if not self.runtime_core:
            self.viewer.setPlainText(
                "No Runtime Core connected."
            )
            return

        inspector = (
            self.runtime_core.inspector
        )

        try:

            method = getattr(
                inspector,
                self.current_section,
            )

            data = method()

            text = json.dumps(
                data,
                indent=4,
                default=str,
                sort_keys=True,
            )

            self.viewer.setPlainText(
                text
            )

            self.status.setText(
                f"Updated {datetime.now().strftime('%H:%M:%S')}"
            )

        except Exception as exc:

            self.viewer.setPlainText(
                json.dumps(
                    {
                        "error": str(exc)
                    },
                    indent=4,
                )
            )

    # -------------------------------------------------

    def copy_json(self):

        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(
            self.viewer.toPlainText()
        )

    # -------------------------------------------------

    def start_refresh(self):

        self.timer = QTimer(self)

        self.timer.timeout.connect(
            self.refresh
        )

        self.timer.start(
            2000
        )