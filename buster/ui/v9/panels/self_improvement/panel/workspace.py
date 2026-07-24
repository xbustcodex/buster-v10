from __future__ import annotations

from typing import Any, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..mode_selector import ModeSelector
from ..execution_card import ExecutionCard
from ..findings_table import FindingsTable
from ..job_queue import JobQueue
from ..history_panel import HistoryPanel
from ..project_health_card import ProjectHealthCard
from ..finding_details_panel import FindingDetailsPanel


class WorkspaceBuilder:
    """Builds and manages UI components for SelfImprovementPanel."""

    def __init__(self, panel: QFrame, runtime_core: Any = None) -> None:
        self.panel = panel
        self.runtime_core = runtime_core

        self.status_label = QLabel("Ready", panel)
        self.expand_button = QPushButton("Expand View ⛶", panel)
        self.scan_button = QPushButton("Run Scan", panel)

        self.mode_selector = ModeSelector(runtime_core=runtime_core, parent=panel)
        self.execution_card = ExecutionCard(runtime_core=runtime_core, parent=panel)
        self.health_card = ProjectHealthCard(panel)

        self.tabs = QTabWidget(panel)
        self.findings = FindingsTable(runtime_core=runtime_core, parent=panel)
        self.finding_details = FindingDetailsPanel(panel)
        self.jobs = JobQueue(runtime_core=runtime_core, parent=panel)
        self.history = HistoryPanel(runtime_core=runtime_core, parent=panel)

    def build_layout(self) -> QVBoxLayout:
        root = QVBoxLayout(self.panel)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel("SELF IMPROVEMENT", self.panel)
        title.setObjectName("SelfImprovementTitle")
        self.status_label.setObjectName("SelfImprovementStatus")
        self.expand_button.setObjectName("ExpandButton")
        self.expand_button.setToolTip("Toggle maximized Findings workspace (or press ESC)")

        header.addWidget(title)
        header.addWidget(self.status_label)
        header.addStretch(1)
        header.addWidget(self.expand_button)
        header.addWidget(self.scan_button)
        root.addLayout(header)

        # Top dashboard cards
        root.addWidget(self.mode_selector)
        root.addWidget(self.execution_card)
        root.addWidget(self.health_card)

        # Findings splitter
        findings_page = QWidget(self.panel)
        findings_layout = QVBoxLayout(findings_page)
        findings_layout.setContentsMargins(0, 0, 0, 0)

        findings_splitter = QSplitter(Qt.Orientation.Horizontal, findings_page)
        findings_splitter.addWidget(self.findings)
        findings_splitter.addWidget(self.finding_details)
        findings_splitter.setStretchFactor(0, 3)
        findings_splitter.setStretchFactor(1, 2)
        findings_splitter.setSizes([760, 440])

        findings_layout.addWidget(findings_splitter)

        self.tabs.addTab(findings_page, "Findings")
        self.tabs.addTab(self.jobs, "Jobs")
        self.tabs.addTab(self.history, "History")

        root.addWidget(self.tabs, 1)
        return root

    def toggle_maximized(self, maximized: bool) -> None:
        self.mode_selector.setVisible(not maximized)
        self.execution_card.setVisible(not maximized)
        self.health_card.setVisible(not maximized)
        self.tabs.tabBar().setVisible(not maximized)

        if maximized:
            self.tabs.setCurrentIndex(0)
            self.expand_button.setText("Collapse View ❐")
            self.status_label.setText("Findings Workspace (Press ESC to restore)")
        else:
            self.expand_button.setText("Expand View ⛶")
            self.status_label.setText("Ready")

    def update_runtime_core(self, runtime_core: Any) -> None:
        self.runtime_core = runtime_core
        if hasattr(self.mode_selector, "set_runtime_core"):
            self.mode_selector.set_runtime_core(runtime_core)
        if hasattr(self.execution_card, "set_runtime_core"):
            self.execution_card.set_runtime_core(runtime_core)

        self.findings.runtime_core = runtime_core
        self.jobs.runtime_core = runtime_core
        self.history.runtime_core = runtime_core