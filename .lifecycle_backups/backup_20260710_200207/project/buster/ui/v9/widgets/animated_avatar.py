from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from buster.ui.v9.widgets.avatar_canvas import AvatarCanvas


class AnimatedAvatar(QFrame):
    DETAILS = {
        "idle": "Buster is ready.",
        "thinking": "Planning the next action.",
        "speaking": "Responding to you.",
        "working": "A runtime task is active.",
        "listening": "Listening for your command.",
        "success": "Operation completed successfully.",
        "warning": "Something needs attention.",
        "error": "An operation failed.",
        "sleeping": "The runtime is idle.",
        "confused": "More information may be needed.",
        "excited": "A major milestone was reached.",
    }

    def __init__(self, state="idle", parent=None):
        super().__init__(parent)
        self.setObjectName("AvatarCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        self.canvas = AvatarCanvas(self)
        self.state_label = QLabel()
        self.state_label.setAlignment(Qt.AlignCenter)
        self.state_label.setStyleSheet("font-size:28px;font-weight:700;color:#23B8FF;")
        self.detail_label = QLabel()
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("font-size:14px;color:#9FB8D5;padding:4px 12px 10px 12px;")
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.state_label)
        layout.addWidget(self.detail_label)
        self.set_state(state)

    def set_state(self, state: str, detail: str | None = None) -> None:
        state = str(state or "idle").lower()
        self.canvas.set_state(state)
        self.state_label.setText(state.title())
        self.detail_label.setText(detail or self.DETAILS.get(state, "Buster is active."))
