from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

class StatusCard(QFrame):
    def __init__(self, title, value="unknown"):
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.title.setStyleSheet("font-size:13px; color:#8ea6c8;")
        self.value = QLabel(value)
        self.value.setStyleSheet("font-size:18px; font-weight:bold; color:#35ff6b;")
        layout.addWidget(self.title)
        layout.addWidget(self.value)

    def set_value(self, value):
        self.value.setText(str(value))
