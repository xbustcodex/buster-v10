"""
vision_panel.py - Cleaned Buster Vision UI Panel
Imports the dedicated VisionEngine module for UI rendering and camera interactions.
"""

import sys
import time
import os
from PySide6.QtCore import Slot, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QSplitter, QScrollArea, QFrame, QStatusBar, QSizePolicy
)

try:
    # Package relative import (if imported within the buster package hierarchy)
    from .vision.vision_engine import VisionEngine, VisionResult, VisionMode
except ImportError:
    # Absolute import fallback (works from root execution)
    from buster.ui.v9.panels.vision.vision_engine import VisionEngine, VisionResult, VisionMode


try:
    from buster.runtime.core import BusterRuntimeCore
except ImportError:
    BusterRuntimeCore = None


class VisionPanel(QWidget):
    """Main Vision Panel Widget connected to VisionEngine"""

    def __init__(self, live=None, parent=None, runtime_core=None):
        if live is not None and not isinstance(live, QWidget):
            if BusterRuntimeCore and isinstance(live, BusterRuntimeCore):
                if runtime_core is None:
                    runtime_core = live
                live = None
        if parent is not None and not isinstance(parent, QWidget):
            if runtime_core is None and BusterRuntimeCore and isinstance(parent, BusterRuntimeCore):
                runtime_core = parent
            parent = None

        super().__init__(parent)
        self.live = live
        self.runtime_core = runtime_core

        self.vision = VisionEngine()
        self.current_result = VisionResult()

        self.recording_active = False

        self.setup_ui()
        self.connect_signals()
        self.apply_dark_theme()

        self.vision.frame_ready.connect(self.update_frame)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("👁️ Buster Vision")
        title_label.setStyleSheet("font-size: 13pt; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.status_indicator = QLabel("● Ready")
        self.status_indicator.setStyleSheet("color: #4ec9b0; font-weight: bold;")
        header_layout.addWidget(self.status_indicator)

        self.fps_label = QLabel("FPS: 0.0")
        self.fps_label.setStyleSheet("color: #569cd6; font-weight: bold; margin-left: 8px;")
        header_layout.addWidget(self.fps_label)
        layout.addWidget(header_widget)

        content_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(content_splitter, 1)

        # Dynamic Camera Label
        self.image_label = QLabel("Camera Offline")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(160, 120)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #141414;
                border: 2px solid #2a2a2a;
                border-radius: 6px;
                color: #555555;
            }
        """)
        content_splitter.addWidget(self.image_label)

        # Scroll Area for Control Panel
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(6)
        bottom_layout.setContentsMargins(4, 4, 4, 4)

        # Controls Button Layout
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(4)

        self.start_btn = QPushButton("▶ Start")
        self.start_btn.setStyleSheet(self.get_button_style("#4ec9b0"))
        self.button_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setStyleSheet(self.get_button_style("#f44747"))
        self.stop_btn.setEnabled(False)
        self.button_layout.addWidget(self.stop_btn)

        self.track_btn = QPushButton("🎯 Tracking")
        self.track_btn.setStyleSheet(self.get_button_style("#dcdcaa"))
        self.button_layout.addWidget(self.track_btn)

        self.record_btn = QPushButton("📹 Record")
        self.record_btn.setStyleSheet(self.get_button_style("#ce9178"))
        self.button_layout.addWidget(self.record_btn)

        self.photo_btn = QPushButton("📸 Photo")
        self.photo_btn.setStyleSheet(self.get_button_style("#569cd6"))
        self.button_layout.addWidget(self.photo_btn)

        modes = [
            ("👤 Faces", VisionMode.FACES),
            ("📱 QR", VisionMode.QR),
            ("⚡ Edge", VisionMode.EDGE),
            ("🔄 Normal", VisionMode.NORMAL),
        ]

        for label, mode in modes:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #252526;
                    color: #cccccc;
                    border: 1px solid #3c3c3c;
                    padding: 4px 8px;
                    border-radius: 4px;
                }
                QPushButton:hover { background-color: #333333; }
                QPushButton:checked { border-color: #4ec9b0; background-color: #1e3a2f; }
            """)
            btn.clicked.connect(lambda checked, m=mode: self.set_vision_mode(m))
            self.button_layout.addWidget(btn)
            setattr(self, f"mode_{mode.value}_btn", btn)

        self.button_layout.addStretch()
        bottom_layout.addLayout(self.button_layout)

        # Info & Log Console
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(70)
        self.info_text.setStyleSheet("""
            QTextEdit {
                background-color: #111111;
                color: #b5cea8;
                border: 1px solid #2d2d2d;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                font-size: 8pt;
            }
        """)
        info_layout.addWidget(self.info_text)
        bottom_layout.addWidget(info_widget)

        scroll_area.setWidget(bottom_widget)
        content_splitter.addWidget(scroll_area)
        content_splitter.setStretchFactor(0, 4)
        content_splitter.setStretchFactor(1, 1)

        # Footer Status
        status_bar = QStatusBar()
        status_bar.setStyleSheet("background-color: #181818; color: #777777; border-top: 1px solid #2a2a2a;")
        self.status_label = QLabel("System Idle")
        status_bar.addWidget(self.status_label)
        layout.addWidget(status_bar)

    def connect_signals(self):
        self.start_btn.clicked.connect(self.start_camera)
        self.stop_btn.clicked.connect(self.stop_camera)
        self.track_btn.clicked.connect(self.toggle_tracking)
        self.record_btn.clicked.connect(self.toggle_recording)
        self.photo_btn.clicked.connect(self.take_photo)

        self.vision.result_ready.connect(self.update_info)
        self.vision.status_changed.connect(self.update_status)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #d4d4d4; font-family: 'Segoe UI', sans-serif; }
            QPushButton { background-color: #2d2d2d; color: #cccccc; border: none; padding: 4px 10px; border-radius: 4px; }
            QPushButton:hover { background-color: #3d3d3d; }
            QSplitter::handle { background-color: #2a2a2a; }
        """)

    def get_button_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {color};
                color: #121212;
                padding: 4px 10px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {color}dd; }}
        """

    @Slot(QImage)
    def update_frame(self, qimage: QImage):
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        if self.current_result:
            self.fps_label.setText(f"FPS: {self.current_result.fps:.1f}")

    @Slot(VisionResult)
    def update_info(self, result: VisionResult):
        self.current_result = result
        log_lines = []
        if result.faces:
            log_lines.append(f"👤 Detected Faces: {len(result.faces)}")
        if result.qr_codes:
            log_lines.append(f"📱 QR Codes: {', '.join(result.qr_codes)}")
        if log_lines:
            self.info_text.setText("\n".join(log_lines))

    @Slot(str)
    def update_status(self, status: str):
        self.status_label.setText(status)

    @Slot()
    def start_camera(self):
        self.vision.start_camera(0)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_indicator.setText("● Active")
        self.status_indicator.setStyleSheet("color: #4ec9b0; font-weight: bold;")

    @Slot()
    def stop_camera(self):
        self.vision.stop_camera()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.image_label.clear()
        self.image_label.setText("Camera Offline")
        self.status_indicator.setText("● Stopped")
        self.status_indicator.setStyleSheet("color: #f44747; font-weight: bold;")

    @Slot()
    def toggle_tracking(self):
        self.vision.tracking_active = not self.vision.tracking_active
        state = "Enabled" if self.vision.tracking_active else "Disabled"
        self.track_btn.setText("⏹ Stop Track" if self.vision.tracking_active else "🎯 Tracking")
        self.info_text.append(f"🎯 Target Tracking {state}")

    @Slot()
    def toggle_recording(self):
        self.recording_active = not self.recording_active
        state = "Started" if self.recording_active else "Stopped"
        self.record_btn.setText("⏹ Stop Rec" if self.recording_active else "📹 Record")
        self.info_text.append(f"🎥 Video Recording {state}")

    @Slot()
    def take_photo(self):
        if self.vision.running:
            save_dir = os.path.join(os.getcwd(), "screenshots")
            os.makedirs(save_dir, exist_ok=True)
            filename = os.path.join(save_dir, f"snapshot_{int(time.time())}.jpg")
            pixmap = self.image_label.pixmap()
            if pixmap:
                pixmap.save(filename, "JPG")
                self.info_text.append(f"📸 Saved snapshot: {filename}")

    @Slot()
    def set_vision_mode(self, mode: VisionMode):
        self.vision.set_mode(mode)
        for mode_enum in VisionMode:
            btn = getattr(self, f"mode_{mode_enum.value}_btn", None)
            if btn:
                btn.setChecked(mode == mode_enum)

    def closeEvent(self, event):
        self.vision.stop_camera()
        self.vision.quit()
        self.vision.wait()
        event.accept()