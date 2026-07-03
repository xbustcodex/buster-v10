from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from buster.ui.v9.widgets.avatar_canvas import AvatarCanvas

class AnimatedAvatar(QFrame):
    def __init__(self, state="idle"):
        super().__init__()
        self.setObjectName("Card")

        layout = QVBoxLayout(self)

        self.canvas = AvatarCanvas()
        self.label = QLabel(state.title())
        self.label.setStyleSheet("font-size:20px; font-weight:bold; color:#20a8ff;")
        self.label.setAlignment(Qt.AlignCenter) if False else None

        layout.addWidget(self.canvas)
        layout.addWidget(self.label)

        self.set_state(state)

    def set_state(self, state):
        self.canvas.set_state(state)
        self.label.setText(state.title())
