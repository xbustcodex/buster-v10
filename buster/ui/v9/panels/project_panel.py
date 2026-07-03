from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class ProjectPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("Project Explorer")
        title.setObjectName("Title")
        layout.addWidget(title)
        layout.addWidget(QLabel("Project tree coming next."))
