from __future__ import annotations

import json
import os
from typing import Optional, Any, Sequence

try:
    from PySide6.QtWidgets import (
        QGroupBox,
        QVBoxLayout,
        QListWidget,
        QPushButton,
        QHBoxLayout,
        QMessageBox,
    )
    from PySide6.QtCore import Signal
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QGroupBox = object

from buster.mission_control.snapshot import CircuitSnapshot


class CircuitBreakerCard(QGroupBox if PYSIDE6_AVAILABLE else object):
    """Monitors circuit breaker states and provides reset controls."""

    reset_requested = Signal(str) if PYSIDE6_AVAILABLE else None

    def __init__(self, parent: Optional[Any] = None):
        if not PYSIDE6_AVAILABLE:
            return
        super().__init__("CIRCUIT BREAKERS", parent)
        self.setMinimumHeight(180)
        self._setup_ui()
        self.refresh_circuits()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(8)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            """
            QListWidget {
                background-color: #07111D;
                border: 1px solid #15324E;
                border-radius: 4px;
                color: #DCEBFF;
                font-size: 11px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 6px;
            }
            """
        )
        layout.addWidget(self.list_widget, 1)

        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton("Reset Selected Circuit")
        self.reset_btn.clicked.connect(self._on_reset)
        btn_layout.addWidget(self.reset_btn)
        layout.addLayout(btn_layout)

    def _get_dlq_state_path(self) -> str:
        """Finds buster/brain/dlq_state.json relative to project root."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        current_dir = base_dir
        while current_dir and os.path.basename(current_dir) != "buster-v10":
            parent = os.path.dirname(current_dir)
            if parent == current_dir:
                break
            current_dir = parent
        return os.path.join(current_dir, "buster", "brain", "dlq_state.json")

    def refresh_circuits(self) -> None:
        """Reads dlq_state.json directly if snapshot data isn't provided."""
        if not PYSIDE6_AVAILABLE:
            return

        self.list_widget.clear()
        dlq_path = self._get_dlq_state_path()

        if os.path.exists(dlq_path):
            try:
                with open(dlq_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                circuits = data.get("circuits", {})
                if not circuits:
                    self.list_widget.addItem("(No circuit breakers registered)")
                    return

                for name, info in circuits.items():
                    status = info.get("status", "CLOSED")
                    fails = info.get("failure_count", 0)
                    icon = "🟢" if "CLOSED" in status else "🔴"
                    item_text = f"{name:<15} | State: {status} {icon} | Failures: {fails}"
                    self.list_widget.addItem(item_text)
            except Exception:
                self.list_widget.addItem("(No circuit breakers registered)")

    def update_circuits(self, circuits: Optional[Sequence[CircuitSnapshot]] = None) -> None:
        if not PYSIDE6_AVAILABLE:
            return

        if not circuits:
            self.refresh_circuits()
            return

        self.list_widget.clear()
        for cb in circuits:
            crit_flag = " [CRITICAL]" if cb.is_critical else ""
            status_icon = "🟢" if "CLOSED" in str(cb.state).upper() else "🔴"
            self.list_widget.addItem(
                f"{cb.circuit_id:<15} | State: {cb.state} {status_icon}{crit_flag} | Failures: {cb.failure_count}"
            )

    def _on_reset(self) -> None:
        item = self.list_widget.currentItem()
        if item and "|" in item.text():
            cid = item.text().split("|")[0].strip()
            reply = QMessageBox.question(
                self,
                "Permission Check",
                f"Are you sure you want to manually reset circuit '{cid}'?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes and self.reset_requested:
                self.reset_requested.emit(cid)