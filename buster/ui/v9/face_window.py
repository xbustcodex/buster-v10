from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from buster.ui.v9.theme import STYLE
from buster.ui.v9.widgets.animated_avatar import AnimatedAvatar

class FaceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Buster Face")
        self.resize(320, 340)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout(self)
        self.avatar = AnimatedAvatar("idle")
        layout.addWidget(self.avatar)

    def set_state(self, state):
        self.avatar.set_state(state)
