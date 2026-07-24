# buster/ui/v9/panels/evolution_panel/evolution_panel.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QListWidget
from PySide6.QtCore import Slot, QTime

from buster.ui.v9.panels.evolution_panel.level_card import LevelCard
from buster.ui.v9.panels.evolution_panel.drive_card import DriveCard
from buster.ui.v9.panels.evolution_panel.skills_card import SkillsCard

class EvolutionPanel(QWidget):
    def __init__(self, live=None, runtime_core=None, parent=None):
        super().__init__(parent)
        self.live = live
        self.runtime_core = runtime_core or getattr(live, "kernel_core", None) or getattr(live, "runtime_core", None)
        
        self.init_ui()
        self.connect_events()

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

        # --- TIMELINE WIDGET INJECTION ---
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

    def connect_events(self):
        """Connects subscriptions safely through the active runtime event_bus."""
        if not self.runtime_core:
            return

        bus = getattr(self.runtime_core, "event_bus", None) or getattr(self.runtime_core, "dispatcher", None)
        
        if bus:
            # Helper function to extract payload safely regardless of event wrapper structure
            def _wrap(callback):
                def _handler(event_data):
                    payload = getattr(event_data, "payload", event_data) if not isinstance(event_data, dict) else event_data
                    callback(payload)
                return _handler

            if hasattr(bus, "subscribe"):
                bus.subscribe("evolution.changed", _wrap(self.refresh_identity_telemetry))
                bus.subscribe("level.progressed", _wrap(self.handle_level_up_log))
                bus.subscribe("experience.recorded", _wrap(self.handle_xp_log))
            elif hasattr(bus, "on"):
                bus.on("evolution.changed", _wrap(self.refresh_identity_telemetry))
                bus.on("level.progressed", _wrap(self.handle_level_up_log))
                bus.on("experience.recorded", _wrap(self.handle_xp_log))

    @Slot(dict)
    def refresh_identity_telemetry(self, identity_data: dict):
        """Dynamic slot handler targeted directly from the core Event Bus."""
        if hasattr(self.level_card, "update_data"):
            self.level_card.update_data(identity_data)
        if hasattr(self.drive_card, "update_data"):
            self.drive_card.update_data(identity_data.get("drives_matrix", {}))
        if hasattr(self.skills_card, "update_data"):
            self.skills_card.update_data(identity_data)

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