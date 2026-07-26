from __future__ import annotations

import json
import os
from typing import Optional, Any, Dict

try:
    from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QLabel
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QGroupBox = object


class GrowthLedgerCard(QGroupBox if PYSIDE6_AVAILABLE else object):
    """Displays Cognitive Rhythm, Hurdles Patched, and Toolbelt state."""

    def __init__(self, parent: Optional[Any] = None):
        if not PYSIDE6_AVAILABLE:
            return
        super().__init__("LEARNING INSIGHTS / GROWTH LEDGER", parent)
        self._setup_ui()
        self.refresh_ledger()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.rhythm_lbl = QLabel("Cognitive Rhythm: Active Development Mode")
        self.hurdles_lbl = QLabel("Growth Ledger: 0 Hurdles Patched in Dream Sandbox")
        self.tools_lbl = QLabel("Toolbelt: 0 Self-Built Tools Registered")

        for lbl in (self.rhythm_lbl, self.hurdles_lbl, self.tools_lbl):
            lbl.setStyleSheet("color: #23B8FF; font-size: 11px; font-weight: bold;")
            layout.addWidget(lbl)

    def _get_ledger_path(self) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        current_dir = base_dir
        while current_dir and os.path.basename(current_dir) != "buster-v10":
            parent = os.path.dirname(current_dir)
            if parent == current_dir:
                break
            current_dir = parent
        return os.path.join(current_dir, "buster", "brain", "growth_ledger_state.json")

    def refresh_ledger(self) -> None:
        if not PYSIDE6_AVAILABLE:
            return

        ledger_path = self._get_ledger_path()
        if os.path.exists(ledger_path):
            try:
                with open(ledger_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                rhythm = data.get("cognitive_rhythm", "Active Development Mode")
                hurdles = len(data.get("hurdles", []))
                tools = len(data.get("toolbelt", []))

                self.rhythm_lbl.setText(f"Cognitive Rhythm: {rhythm}")
                self.hurdles_lbl.setText(f"Growth Ledger: {hurdles} Hurdles Patched in Dream Sandbox")
                self.tools_lbl.setText(f"Toolbelt: {tools} Self-Built Tool Registered" if tools == 1 else f"Toolbelt: {tools} Self-Built Tools Registered")
            except Exception:
                pass

    def update_ledger(self, ledger_data: Optional[Dict[str, Any]] = None) -> None:
        self.refresh_ledger()