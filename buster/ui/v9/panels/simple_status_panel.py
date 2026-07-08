from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton


class SimpleStatusPanel(QWidget):
    def __init__(self, title="Panel", message="", live=None):
        super().__init__()
        self.panel_title = title
        self.message = message
        self.live = live

        self.setWindowTitle(title)
        self.resize(720, 520)

        layout = QVBoxLayout(self)

        heading = QLabel(title)
        heading.setObjectName("Title")
        layout.addWidget(heading)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

        close = QPushButton("Close")
        close.clicked.connect(self.close)
        layout.addWidget(close)

        self.refresh()

    def refresh(self):
        self.output.setPlainText(self.message)
