from __future__ import annotations
from typing import Optional, Any

try:
    from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QMessageBox
    from PySide6.QtCore import Signal
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QGroupBox = object


class DLQCard(QGroupBox if PYSIDE6_AVAILABLE else object):
    """Dead Letter Queue inspector with safe retry & dismiss commands."""

    retry_requested = Signal(str) if PYSIDE6_AVAILABLE else None
    dismiss_requested = Signal(str) if PYSIDE6_AVAILABLE else None

    def __init__(self, parent: Optional[Any] = None):
        if not PYSIDE6_AVAILABLE:
            return
        super().__init__("DEAD LETTER QUEUE (DLQ)", parent)
        layout = QVBoxLayout(self)

        self.dlq_list = QListWidget()
        self.dlq_list.setStyleSheet("background-color: #0f172a; color: #f8fafc;")
        layout.addWidget(self.dlq_list)

        btn_layout = QHBoxLayout()
        self.retry_btn = QPushButton("Retry Item")
        self.retry_btn.clicked.connect(self._on_retry)
        self.dismiss_btn = QPushButton("Dismiss")
        self.dismiss_btn.clicked.connect(self._on_dismiss)

        btn_layout.addWidget(self.retry_btn)
        btn_layout.addWidget(self.dismiss_btn)
        layout.addLayout(btn_layout)

    def update_dlq(self, dlq_count: int) -> None:
        if not PYSIDE6_AVAILABLE:
            return
        self.dlq_list.clear()
        if dlq_count == 0:
            self.dlq_list.addItem("DLQ is empty (0 failed items)")
        else:
            for i in range(dlq_count):
                self.dlq_list.addItem(f"DLQ-Record-{i+1}: Task Execution Failure")

    def _on_retry(self) -> None:
        curr = self.dlq_list.currentItem()
        if curr and "DLQ-Record" in curr.text():
            self.retry_requested.emit(curr.text())

    def _on_dismiss(self) -> None:
        curr = self.dlq_list.currentItem()
        if curr and "DLQ-Record" in curr.text():
            reply = QMessageBox.question(
                self, "Confirm Dismiss", f"Are you sure you want to dismiss {curr.text()}?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.dismiss_requested.emit(curr.text())