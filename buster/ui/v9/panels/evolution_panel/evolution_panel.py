# buster/ui/v9/panels/evolution_panel/evolution_panel.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QListWidget
from PySide6.QtCore import Slot, QTime

from buster.ui.v9.panels.evolution_panel.level_card import LevelCard
from buster.ui.v9.panels.evolution_panel.drive_card import DriveCard
from buster.ui.v9.panels.evolution_panel.skills_card import SkillsCard

class EvolutionPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setObjectName("EvolutionPanel")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll window to avoid panel compression clipping
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        container.setStyleSheet("QWidget { background-color: #1E1E1E; }")
        content_layout = QVBoxLayout(container)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(15, 15, 15, 15)

        # Instantiating custom sub-module cards
        self.level_card = LevelCard(container)
        self.drive_card = DriveCard(container)
        self.skills_card = SkillsCard(container)

        # Style box containment injections
        card_style = "QWidget { background-color: #252526; border-radius: 6px; }"
        self.level_card.setStyleSheet(card_style)
        self.drive_card.setStyleSheet(card_style)
        self.skills_card.setStyleSheet(card_style)

        content_layout.addWidget(self.level_card)
        content_layout.addWidget(self.drive_card)
        content_layout.addWidget(self.skills_card)

        # --- NEW TIMELINE WIDGET INJECTION ---
        timeline_label = QLabel("EVOLUTION EVENT LOG", container)
        timeline_label.setStyleSheet("color: #8E8E8E; font-size: 10px; font-weight: bold; letter-spacing: 1px; margin-top: 5px;")
        content_layout.addWidget(timeline_label)

        self.timeline_log = QListWidget(container)
        self.timeline_log.setFixedHeight(120)
        self.timeline_log.setStyleSheet("""
            QListWidget { 
                background-color: #161617; 
                border: 1px solid #2D2D30; 
                border-radius: 4px; 
                color: #D4D4D4; 
                font-family: 'Consolas', 'Courier New', monospace; 
                font-size: 11px; 
                padding: 5px;
            }
        """)
        content_layout.addWidget(self.timeline_log)
        content_layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # --- NEW EXTENSIONS (APPENDED AT END OF INITIALIZATION SETUP) ---
        from buster.core.event_bus import main_event_bus
        
        # Subscribe the display components directly to the consolidated system change topic
        main_event_bus.subscribe("evolution.changed", lambda event: self.refresh_identity_telemetry(event.payload))
        main_event_bus.subscribe("level.progressed", lambda event: self.handle_level_up_log(event.payload))
        main_event_bus.subscribe("experience.recorded", lambda event: self.handle_xp_log(event.payload))

    @Slot(dict)
    def refresh_identity_telemetry(self, identity_data: dict):
        """Dynamic slot handler targeted directly from the core Event Bus."""
        self.level_card.update_data(identity_data)
        self.drive_card.update_data(identity_data.get("drives_matrix", {}))
        self.skills_card.update_data(identity_data)

    # --- NEW LOGGING SLOTS APPENDED TO THE CLASS ---
    def _add_timeline_entry(self, text: str):
        """Helper to prepend timestamps and keep the timeline auto-scrolling."""
        timestamp = QTime.currentTime().toString("hh:mm")
        self.timeline_log.addItem(f"{timestamp}  {text}")
        self.timeline_log.scrollToBottom()

    @Slot(dict)
    def handle_xp_log(self, payload: dict):
        """Appends interactive experience shifts directly into the view ledger."""
        action = payload.get("action_type", "operation").replace("_", " ").title()
        xp = payload.get("xp_gained", 0)
        xp_str = f"+{xp} XP" if xp >= 0 else f"{xp} XP"
        self._add_timeline_entry(f"{xp_str:<10} {action} completed")

    @Slot(dict)
    def handle_level_up_log(self, payload: dict):
        """Appends explicit level milestones to the running timeline log."""
        lvl = payload.get("level", 1)
        rank = payload.get("permission_rank", "Operator")
        self._add_timeline_entry(f"{'Level Up':<10} Promoted to {rank} (Lv. {lvl})")