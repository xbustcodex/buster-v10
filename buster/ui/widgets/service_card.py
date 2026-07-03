from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

class ServiceCard(QFrame):
    def __init__(self, title, status="ONLINE"):
        super().__init__()
        layout = QVBoxLayout(self)
        self.title = QLabel(title)
        self.title.setObjectName("CardTitle")
        self.status = QLabel(status)
        layout.addWidget(self.title)
        layout.addWidget(self.status)

    def set_status(self, text):
        self.status.setText(text)
