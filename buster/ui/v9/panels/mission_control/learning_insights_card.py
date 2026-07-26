from __future__ import annotations

import json
import os
from typing import Optional, Any, Sequence, Dict

try:
    from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QLabel
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QGroupBox = object

from buster.brain.buster_rhythm import BusterRhythm


class LearningInsightsCard(QGroupBox if PYSIDE6_AVAILABLE else object):
    """Displays observational insights, cognitive state, and self-built toolbelt."""

    def __init__(self, parent: Optional[Any] = None):
        if not PYSIDE6_AVAILABLE:
            return
        super().__init__("LEARNING INSIGHTS & GROWTH LEDGER", parent)
        
        self.setStyleSheet(
            """
            QGroupBox {
                background: #07111D;
                border: 1px solid #15324E;
                border-radius: 8px;
                margin-top: 12px;
                font-weight: bold;
                color: #23B8FF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 8px;
            }
            QLabel {
                color: #8EA2C0;
                font-size: 11px;
            }
            """
        )
        self.rhythm = BusterRhythm()
        self._setup_ui()
        self.refresh_insights()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        self.state_label = QLabel("Cognitive Rhythm: <b>Evaluating...</b>")
        self.hurdle_stats = QLabel("Growth Ledger: <b>0 Hurdles Resolved</b>")
        self.toolbelt_label = QLabel("Toolbelt: <b>0 Self-Built Utilities Active</b>")

        layout.addWidget(self.state_label)
        layout.addWidget(self.hurdle_stats)
        layout.addWidget(self.toolbelt_label)
        layout.addStretch()

    def refresh_insights(self) -> None:
        if not PYSIDE6_AVAILABLE:
            return

        # 1. Update Circadian Life State
        status = self.rhythm.get_blackboard_status()
        state_str = status["current_state"]
        self.state_label.setText(
            f"Cognitive Rhythm: <font color='#31D158'><b>{state_str}</b></font> ({status['day_of_week']})"
        )

        # 2. Dynamically resolve buster/brain/growth_ledger.json
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Walk up from buster/ui/v9/panel/mission_control to project root
        project_root = os.path.abspath(os.path.join(base_dir, "..", "..", "..", "..", ".."))
        ledger_path = os.path.join(project_root, "buster", "brain", "growth_ledger.json")

        resolved_count = 0
        tools_count = 0

        if os.path.exists(ledger_path):
            try:
                with open(ledger_path, "r", encoding="utf-8") as f:
                    ledger = json.load(f)
                    hurdles = ledger.get("hurdles", [])
                    resolved_count = sum(1 for h in hurdles if h.get("status") == "Resolved in Dream Mode")
                    tools_count = len(ledger.get("toolbelt", []))
            except Exception:
                pass

        self.hurdle_stats.setText(
            f"Growth Ledger: <font color='#23B8FF'><b>{resolved_count} Hurdles Patched</b></font> in Dream Sandbox"
        )
        self.toolbelt_label.setText(
            f"Toolbelt: <font color='#FFC107'><b>{tools_count} Self-Built Tools</b></font> Registered"
        )

    def update_insights(self, insights: Any = None) -> None:
        """Called by MissionControlPanel timer pulse."""
        self.refresh_insights()