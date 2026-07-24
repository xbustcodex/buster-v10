"""
Task Panel & Real-Time Agent Dashboard for Buster Mission Control (v10.7)
Visualizes active workflows, scheduled tasks, and live execution updates.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger("buster.ui.task_panel")


class TaskPanel(QWidget):
    """Real-time monitoring panel for agents, tasks, and orchestrator workflows."""

    def __init__(self, orchestrator=None, event_bus=None, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.event_bus = event_bus

        self._build_ui()

        # Connect event bus listeners if available
        if self.event_bus:
            self.event_bus.subscribe("orchestrator:workflow_started", self._on_workflow_event)
            self.event_bus.subscribe("orchestrator:task_completed", self._on_workflow_event)
            self.event_bus.subscribe("healing:exception_caught", self._on_healing_event)

        # Refresh UI timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_task_table)
        self._refresh_timer.start(2000)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        title = QLabel("AGENT TASK MONITOR & ORCHESTRATOR DASHBOARD")
        title.setStyleSheet("color: #23B8FF; font-size: 18px; font-weight: 800; letter-spacing: 1px;")
        layout.addWidget(title)

        # Workflow Task Table
        self.task_table = QTableWidget(0, 4)
        self.task_table.setHorizontalHeaderLabels(["Workflow ID", "Goal / Task", "Assigned Agent", "Status"])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.task_table.setStyleSheet("""
            QTableWidget {
                background-color: #050B14;
                gridline-color: #15324E;
                color: #DCEBFF;
                border: 1px solid #15324E;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #081827;
                color: #23B8FF;
                font-weight: bold;
                border: 1px solid #15324E;
                padding: 4px;
            }
        """)
        layout.addWidget(self.task_table)

        # Execution Logs Area
        log_label = QLabel("Live Agent Execution Log:")
        log_label.setStyleSheet("color: #7894B5; font-size: 11px; font-weight: 700;")
        layout.addWidget(log_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #03070D;
                color: #31D158;
                font-family: Consolas, monospace;
                font-size: 11px;
                border: 1px solid #15324E;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.log_output)

        # Control Bar
        control_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh Status")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: #175A94; color: #FFFFFF; border: none;
                border-radius: 4px; padding: 6px 12px; font-weight: bold;
            }
            QPushButton:hover { background: #23B8FF; color: #050B14; }
        """)
        self.refresh_btn.clicked.connect(self._refresh_task_table)
        control_layout.addWidget(self.refresh_btn)
        control_layout.addStretch()

        layout.addLayout(control_layout)

    def _refresh_task_table(self) -> None:
        """Polls active workflows from orchestrator and updates the table."""
        if not self.orchestrator or not hasattr(self.orchestrator, "active_workflows"):
            return

        workflows = self.orchestrator.active_workflows
        self.task_table.setRowCount(0)

        for wf_id, wf_data in workflows.items():
            row = self.task_table.rowCount()
            self.task_table.insertRow(row)

            self.task_table.setItem(row, 0, QTableWidgetItem(wf_id))
            self.task_table.setItem(row, 1, QTableWidgetItem(wf_data.get("goal", "N/A")))
            self.task_table.setItem(row, 2, QTableWidgetItem("Orchestrator"))
            self.task_table.setItem(row, 3, QTableWidgetItem(wf_data.get("status", "UNKNOWN")))

    def _on_workflow_event(self, event_name: str, payload: dict) -> None:
        """Handles inbound events from orchestrator."""
        msg = f"[{event_name.upper()}] {payload}\n"
        self.log_output.append(msg)
        self._refresh_task_table()

    def _on_healing_event(self, event_name: str, payload: dict) -> None:
        """Handles self-healing log entries."""
        msg = f"[SELF-HEAL] Caught error in task {payload.get('task_id')}: {payload.get('error')}\n"
        self.log_output.append(msg)