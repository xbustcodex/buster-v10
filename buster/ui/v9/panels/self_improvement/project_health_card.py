from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class ProjectHealthCard(QFrame):
    """Compact health summary calculated from current findings."""

    CATEGORY_LABELS = {
        "syntax": "Syntax",
        "tests": "Tests",
        "safety": "Git Safety",
        "architecture": "Architecture",
        "todo": "TODOs",
        "performance": "Performance",
    }

    WEIGHTS = {
        "critical": 30,
        "high": 18,
        "medium": 8,
        "low": 2,
        "info": 1,
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("ProjectHealthCard")
        self._build_ui()
        self._apply_styles()
        self.set_findings([])

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(7)

        header = QHBoxLayout()
        title = QLabel("PROJECT HEALTH", self)
        title.setObjectName("ProjectHealthTitle")

        self.score_label = QLabel("100%", self)
        self.score_label.setObjectName("ProjectHealthScore")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.score_label)
        root.addLayout(header)

        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        root.addWidget(self.progress)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(4)

        self.category_values: dict[str, QLabel] = {}

        categories = [
            "syntax",
            "tests",
            "safety",
            "architecture",
            "todo",
            "performance",
        ]

        for index, category in enumerate(categories):
            row = index // 3
            column = (index % 3) * 2

            label = QLabel(self.CATEGORY_LABELS[category], self)
            label.setObjectName("ProjectHealthCaption")

            value = QLabel("✓", self)
            value.setObjectName("ProjectHealthValue")

            grid.addWidget(label, row, column)
            grid.addWidget(value, row, column + 1)

            self.category_values[category] = value

        root.addLayout(grid)

        self.summary_label = QLabel("No active findings.", self)
        self.summary_label.setObjectName("ProjectHealthSummary")
        root.addWidget(self.summary_label)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QFrame#ProjectHealthCard {
                background-color: #151a22;
                border: 1px solid #2a3442;
                border-radius: 10px;
            }

            QLabel#ProjectHealthTitle {
                color: #23b8ff;
                font-size: 12px;
                font-weight: 800;
            }

            QLabel#ProjectHealthScore {
                color: #ffffff;
                font-size: 14px;
                font-weight: 800;
            }

            QLabel#ProjectHealthCaption {
                color: #7f8b99;
                font-size: 10px;
                font-weight: 600;
            }

            QLabel#ProjectHealthValue {
                color: #dbe3eb;
                font-size: 10px;
                font-weight: 700;
            }

            QLabel#ProjectHealthSummary {
                color: #8f9baa;
                font-size: 10px;
            }

            QProgressBar {
                background-color: #202833;
                border: none;
                border-radius: 4px;
            }

            QProgressBar::chunk {
                background-color: #22c55e;
                border-radius: 4px;
            }
            """
        )

    def set_findings(self, findings: Iterable[Any]) -> None:
        normalized = [
            dict(item)
            for item in findings
            if isinstance(item, Mapping)
        ]

        severity_counts = Counter(
            str(item.get("severity", "info")).lower()
            for item in normalized
        )
        category_counts = Counter(
            str(item.get("category", "other")).lower()
            for item in normalized
        )

        penalty = sum(
            self.WEIGHTS.get(severity, 1) * count
            for severity, count in severity_counts.items()
        )
        score = max(0, min(100, 100 - penalty))

        self.score_label.setText(f"{score}%")
        self.progress.setValue(score)

        for category, value_label in self.category_values.items():
            count = category_counts.get(category, 0)
            value_label.setText("✓" if count == 0 else f"⚠ {count}")

        high_count = (
            severity_counts.get("critical", 0)
            + severity_counts.get("high", 0)
        )

        if not normalized:
            summary = "No active findings."
        elif high_count:
            summary = (
                f"{len(normalized)} finding(s), including "
                f"{high_count} high-priority issue(s)."
            )
        else:
            summary = f"{len(normalized)} finding(s), no high-priority issues."

        self.summary_label.setText(summary)
