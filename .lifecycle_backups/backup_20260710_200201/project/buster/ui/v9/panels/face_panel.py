from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from buster.ui.v9.widgets.animated_avatar import AnimatedAvatar

class FacePanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        title = QLabel("Assistant")
        title.setObjectName("Title")
        layout.addWidget(title)

        self.avatar = AnimatedAvatar("idle")
        layout.addWidget(self.avatar)

    def set_state(self, state):
        self.avatar.set_state(state)
