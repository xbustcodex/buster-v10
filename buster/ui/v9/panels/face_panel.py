from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget
from buster.ui.v9.widgets.animated_avatar import AnimatedAvatar


class FacePanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        # Main layout configuration
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Title Label
        self.title = QLabel("Assistant")
        self.title.setObjectName("Title")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)

        # Animated Avatar
        self.avatar = AnimatedAvatar("idle")
        layout.addWidget(
            self.avatar, 0, Qt.AlignmentFlag.AlignCenter
        )  # Centers avatar within layout

    def set_state(self, state: str):
        """Updates the animation state of the avatar."""
        if hasattr(self.avatar, "set_state"):
            self.avatar.set_state(state)