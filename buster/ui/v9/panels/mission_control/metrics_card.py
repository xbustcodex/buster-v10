from __future__ import annotations
from typing import Optional, Any, Dict

try:
    from PySide6.QtWidgets import QGroupBox, QGridLayout, QLabel
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QGroupBox = object


class MetricsCard(QGroupBox if PYSIDE6_AVAILABLE else object):
    """Displays core telemetry metrics."""

    def __init__(self, parent: Optional[Any] = None):
        if not PYSIDE6_AVAILABLE:
            return
        super().__init__("SYSTEM METRICS", parent)
        layout = QGridLayout(self)

        self.lbl_completed = QLabel("Completed: 0")
        self.lbl_failed = QLabel("Failed: 0")
        self.lbl_fail_rate = QLabel("Failure Rate: 0.0%")
        self.lbl_trips = QLabel("Circuit Trips: 0")

        layout.addWidget(self.lbl_completed, 0, 0)
        layout.addWidget(self.lbl_failed, 0, 1)
        layout.addWidget(self.lbl_fail_rate, 1, 0)
        layout.addWidget(self.lbl_trips, 1, 1)

    def update_metrics(
        self, completed: int, failed: int, metrics: Dict[str, float]
    ) -> None:
        if not PYSIDE6_AVAILABLE:
            return
        fail_rate = metrics.get("failure_rate", 0.0) * 100
        trips = int(metrics.get("circuit_trips", 0))

        self.lbl_completed.setText(f"Completed: {completed}")
        self.lbl_failed.setText(f"Failed: {failed}")
        self.lbl_fail_rate.setText(f"Failure Rate: {fail_rate:.1f}%")
        self.lbl_trips.setText(f"Circuit Trips: {trips}")