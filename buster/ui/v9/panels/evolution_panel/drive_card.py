# buster/ui/v9/panels/evolution_panel/drive_card.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar

class DriveCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bars = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        title = QLabel("CORE OPERATIONAL DRIVES", self)
        title.setStyleSheet("font-weight: bold; color: #33B5E5; margin-bottom: 5px;")
        layout.addWidget(title)

        drives = [
            ("Helping Drive", "helping", "#4285F4"),
            ("Builder Drive", "builder", "#00C851"),
            ("Learning Drive", "learning", "#AA66CC"),
            ("Protection Drive", "protection", "#FF4444"),
            ("Curiosity Drive", "curiosity", "#FFBB33")
        ]

        for label_text, key, color in drives:
            row = QHBoxLayout()
            lbl = QLabel(label_text, self)
            lbl.setMinimumWidth(110)
            
            pbar = QProgressBar(self)
            pbar.setRange(0, 100)
            pbar.setFixedHeight(12)
            pbar.setTextVisible(False)
            pbar.setStyleSheet(f"""
                QProgressBar {{ border: 1px solid #333; background: #222; border-radius: 3px; }}
                QProgressBar::chunk {{ background-color: {color}; }}
            """)
            
            val_lbl = QLabel("50%", self)
            val_lbl.setMinimumWidth(35)
            
            row.addWidget(lbl)
            row.addWidget(pbar)
            row.addWidget(val_lbl)
            layout.addLayout(row)
            
            self.bars[key] = (pbar, val_lbl)

    def update_data(self, drives_matrix: dict):
        for key, (pbar, val_lbl) in self.bars.items():
            if key in drives_matrix:
                val = int(drives_matrix[key])
                pbar.setValue(val)
                val_lbl.setText(f"{val}%")