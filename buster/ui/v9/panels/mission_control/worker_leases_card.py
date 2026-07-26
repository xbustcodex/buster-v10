from __future__ import annotations
from typing import Optional, Any, Sequence

try:
    from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QListWidget
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QGroupBox = object

from buster.mission_control.snapshot import WorkerLeaseSnapshot


class WorkerLeasesCard(QGroupBox if PYSIDE6_AVAILABLE else object):
    """Displays active worker pool leases."""

    def __init__(self, parent: Optional[Any] = None):
        if not PYSIDE6_AVAILABLE:
            return
        super().__init__("ACTIVE WORKER LEASES", parent)
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("background-color: #0f172a; color: #f8fafc;")
        layout.addWidget(self.list_widget)

    def update_leases(self, leases: Sequence[WorkerLeaseSnapshot]) -> None:
        if not PYSIDE6_AVAILABLE:
            return
        self.list_widget.clear()
        if not leases:
            self.list_widget.addItem("(No active worker leases)")
            return

        for lease in leases:
            self.list_widget.addItem(
                f"[{lease.role}] {lease.worker_id} -> Task {lease.task_id} ({lease.remaining_seconds:.1f}s remaining)"
            )