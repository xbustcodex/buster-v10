from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QProgressBar

class MetricCard(QFrame):
    def __init__(self, title, value=0):
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        self.label = QLabel(title)
        self.label.setStyleSheet("font-size:13px; color:#8ea6c8;")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.value = QLabel("0%")
        layout.addWidget(self.label)
        layout.addWidget(self.bar)
        layout.addWidget(self.value)
        self.set_value(value)

    def set_value(self, value):
        try:
            n = int(float(value))
        except Exception:
            n = 0
        self.bar.setValue(max(0, min(100, n)))
        self.value.setText(f"{n}%")
