from __future__ import annotations
from typing import Optional, Any

try:
    from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
    from PySide6.QtCore import Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QFrame = object


class HealthCard(QFrame if PYSIDE6_AVAILABLE else object):
    """Displays overall system health badge and quick summary metrics."""

    def __init__(self, parent: Optional[Any] = None):
        if not PYSIDE6_AVAILABLE:
            return
        super().__init__(parent)
        self.setObjectName("HealthCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            """
            QFrame#HealthCard {
                background: #07111D;
                border: 1px solid #15324E;
                border-radius: 8px;
                padding: 10px;
            }
            """
        )
        
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        
        self.title_label = QLabel("<span style='color: #8EA2C0; font-size: 11px; font-weight: 700;'>SYSTEM HEALTH</span>")
        
        # Fixed clipping: replaced <h2> with styled span and proper line-height
        self.status_badge = QLabel("<span style='color: #31D158; font-size: 18px; font-weight: 800; line-height: 24px;'>HEALTHY ●</span>")
        
        self.details_label = QLabel("<span style='color: #BFD1E7; font-size: 11px;'>All circuits normal</span>")

        layout.addWidget(self.title_label)
        layout.addWidget(self.status_badge)
        layout.addWidget(self.details_label)
        layout.addStretch()

    def update_state(self, health: str, dlq_count: int, failed_tasks: int) -> None:
        if not PYSIDE6_AVAILABLE:
            return
            
        color_map = {
            "HEALTHY": ("#31D158", "All circuits & workers operational"),
            "DEGRADED": ("#FFC107", f"Degraded performance ({dlq_count} in DLQ)"),
            "CRITICAL": ("#FF4D4D", f"Critical alerts active ({failed_tasks} failed)"),
        }
        color, desc = color_map.get(health, ("#8EA2C0", "Unknown State"))
        self.status_badge.setText(f"<span style='color: {color}; font-size: 18px; font-weight: 800; line-height: 24px;'>{health} ●</span>")
        self.details_label.setText(f"<span style='color: #BFD1E7; font-size: 11px;'>{desc}</span>")