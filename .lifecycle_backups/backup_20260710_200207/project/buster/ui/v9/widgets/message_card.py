from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

class MessageCard(QFrame):
    def __init__(self, title, body, is_user=False):
        super().__init__()
        self.setObjectName("Card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)

        row = QHBoxLayout()
        name = QLabel(title)
        name.setStyleSheet("font-size:16px; font-weight:bold; color:#20a8ff;")
        row.addWidget(name)
        row.addStretch()
        layout.addLayout(row)

        text = QLabel(body)
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text.setStyleSheet("font-size:14px; color:#dcecff;")
        layout.addWidget(text)

        if not is_user:
            actions = QHBoxLayout()
            for label in ["Copy", "Save", "Open"]:
                actions.addWidget(QPushButton(label))
            actions.addStretch()
            layout.addLayout(actions)
