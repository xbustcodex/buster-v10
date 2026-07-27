# buster/ui/v9/panels/evolution_panel/drive_card.py
from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class DriveCard(QWidget):
    """Operational drives including verification and autonomy readiness."""

    DRIVE_DEFINITIONS = (
        ("Helping", "helping"),
        ("Builder", "builder"),
        ("Learning", "learning"),
        ("Protection", "protection"),
        ("Curiosity", "curiosity"),
        ("Verification", "verification"),
        ("Autonomy readiness", "autonomy"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bars: dict[str, tuple[QProgressBar, QLabel]] = {}
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 14, 15, 15)
        layout.setSpacing(8)

        title = QLabel("CORE OPERATIONAL DRIVES")
        title.setStyleSheet(
            "font-weight:900;color:#23B8FF;font-size:13px;"
            "letter-spacing:1px;background:transparent;"
        )
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        for row, (label_text, key) in enumerate(self.DRIVE_DEFINITIONS):
            label = QLabel(label_text)
            label.setMinimumWidth(125)
            label.setStyleSheet(
                "color:#C7D8EA;font-size:11px;background:transparent;"
            )

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(13)
            bar.setStyleSheet(
                """
                QProgressBar {
                    background:#081522;
                    border:1px solid #244560;
                    border-radius:4px;
                }
                QProgressBar::chunk {
                    background:#23B8FF;
                    border-radius:3px;
                }
                """
            )

            value_label = QLabel("0%")
            value_label.setMinimumWidth(40)
            value_label.setStyleSheet(
                "color:#EAF2FF;font-weight:800;font-size:11px;"
                "background:transparent;"
            )

            grid.addWidget(label, row, 0)
            grid.addWidget(bar, row, 1)
            grid.addWidget(value_label, row, 2)
            self.bars[key] = (bar, value_label)

        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        self.summary_label = QLabel(
            "Drive values are derived from learning, successful outcomes, "
            "safety policy and autonomy readiness."
        )
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(
            "color:#7894B5;font-size:10px;background:transparent;"
        )
        layout.addWidget(self.summary_label)

    def update_data(self, drives_matrix: dict[str, Any]) -> None:
        for key, (bar, value_label) in self.bars.items():
            raw = drives_matrix.get(key, 0)
            try:
                value = float(raw)
            except (TypeError, ValueError):
                value = 0

            if 0 <= value <= 1:
                value *= 100

            value = int(max(0, min(100, value)))
            bar.setValue(value)
            value_label.setText(f"{value}%")
