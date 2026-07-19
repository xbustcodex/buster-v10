
from __future__ import annotations

from typing import Any, Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class RepairPlanPanel(QFrame):
    """Read-only UI for displaying a structured RepairPlan."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RepairPlanPanel")

        self.setFrameShape(QFrame.StyledPanel)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Repair Plan")
        title.setStyleSheet("font-size:16px;font-weight:600;")
        root.addWidget(title)

        self.status = QLabel("")
        root.addWidget(self.status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        root.addWidget(self.progress)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        root.addLayout(grid)

        self.goal = QLabel("-")
        self.goal.setWordWrap(True)

        self.risk = QLabel("-")
        self.files = QLabel("-")
        self.effort = QLabel("-")

        grid.addWidget(QLabel("<b>Goal</b>"), 0, 0)
        grid.addWidget(self.goal, 0, 1)

        grid.addWidget(QLabel("<b>Risk</b>"), 1, 0)
        grid.addWidget(self.risk, 1, 1)

        grid.addWidget(QLabel("<b>Files</b>"), 2, 0)
        grid.addWidget(self.files, 2, 1)

        grid.addWidget(QLabel("<b>Effort</b>"), 3, 0)
        grid.addWidget(self.effort, 3, 1)

        root.addWidget(QLabel("<b>Steps</b>"))
        self.steps = QListWidget()
        root.addWidget(self.steps)

        root.addWidget(QLabel("<b>Warnings</b>"))
        self.warnings = QListWidget()
        root.addWidget(self.warnings)

        footer = QHBoxLayout()
        self.provider = QLabel("")
        self.model = QLabel("")
        self.cached = QLabel("")
        footer.addWidget(self.provider)
        footer.addStretch()
        footer.addWidget(self.model)
        footer.addStretch()
        footer.addWidget(self.cached)
        root.addLayout(footer)

        self.clear()

    def clear(self) -> None:
        self.goal.setText("-")
        self.risk.setText("-")
        self.files.setText("-")
        self.effort.setText("-")
        self.steps.clear()
        self.warnings.clear()
        self.provider.clear()
        self.model.clear()
        self.cached.clear()
        self.status.clear()
        self.progress.hide()

    def set_busy(self, busy: bool, message: str = "") -> None:
        self.status.setText(message)
        self.progress.setVisible(busy)

    def show_plan(self, plan: Mapping[str, Any]) -> None:
        self.set_busy(False)
        self.goal.setText(str(plan.get("goal", "-")))
        risk = str(plan.get("risk", "medium")).lower()
        colours = {
            "low": "#3cb371",
            "medium": "#d4a017",
            "high": "#ff8c00",
            "critical": "#d32f2f",
        }
        self.risk.setText(risk.title())
        self.risk.setStyleSheet(f"font-weight:600;color:{colours.get(risk,'white')};")
        self.files.setText(str(plan.get("estimated_files", "-")))
        self.effort.setText(str(plan.get("estimated_effort", "-")))

        self.steps.clear()
        for step in plan.get("steps", []):
            QListWidgetItem(str(step), self.steps)

        self.warnings.clear()
        for warning in plan.get("warnings", []):
            QListWidgetItem(str(warning), self.warnings)

        self.provider.setText(f"Provider: {plan.get('provider','')}")
        self.model.setText(f"Model: {plan.get('model','')}")
        self.cached.setText("Cached" if plan.get("cached") else "")
