# buster/ui/v9/panels/evolution_panel/level_card.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt

class LevelCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Title Block
        self.title_label = QLabel("BUSTER EVOLUTION", self)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #00FFCC;")
        layout.addWidget(self.title_label)

        # Level display
        self.tier_label = QLabel("Level 12 — Engineer", self)
        self.tier_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.tier_label)

        # XP Bar Layout
        xp_layout = QHBoxLayout()
        self.xp_bar = QProgressBar(self)
        self.xp_bar.setRange(0, 100)
        self.xp_bar.setValue(78)
        self.xp_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #444; border-radius: 4px; text-align: center; height: 18px; }
            QProgressBar::chunk { background-color: #00FFCC; }
        """)
        xp_layout.addWidget(self.xp_bar)
        layout.addLayout(xp_layout)

        # Stats Subgrid
        stats_layout = QVBoxLayout()
        self.trust_label = QLabel("Capability Trust Factor: 94%", self)
        self.permissions_label = QLabel("Current Access: Local Git, Python Execution, File Refactoring", self)
        self.permissions_label.setWordWrap(True)
        self.permissions_label.setStyleSheet("color: #AAAAAA; font-size: 12px;")
        
        stats_layout.addWidget(self.trust_label)
        stats_layout.addWidget(self.permissions_label)
        layout.addLayout(stats_layout)

        # Next Unlock Boundaries
        self.unlock_card = QLabel("Next Unlock Tier: Architect (Requires Security Review & 500 Tasks Completed)", self)
        self.unlock_card.setStyleSheet("color: #FFB300; font-size: 11px; font-style: italic; border-top: 1px solid #333; padding-top: 8px;")
        layout.addWidget(self.unlock_card)

    def update_data(self, ctx: dict):
        """Updates internal telemetry elements using state maps."""
        self.tier_label.setText(ctx.get("title", "Level 0 — Observer"))
        self.xp_bar.setValue(ctx.get("xp_pct", 0))
        self.trust_label.setText(f"Capability Trust Factor: {ctx.get('trust', '90.0%')}")
        
        level = ctx.get("level", 1)
        if level >= 3:
            self.permissions_label.setText("Current Access: Git Commits, Automated Refactoring, Local Execution Loops")
            self.unlock_card.setText("Next Unlock Tier: Architect (Requires 350 Tasks & Security Review clearance)")
        else:
            self.permissions_label.setText("Current Access: Read-Only Diagnostics, File Adjustments with Approval")
            self.unlock_card.setText("Next Unlock Tier: Developer (Requires 50 Total Code Evaluations Completed)")