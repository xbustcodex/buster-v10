try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
except Exception:
    QWidget = object
    QVBoxLayout = None
    QLabel = None

class WorkingMemoryGoalWidget(QWidget):
    def __init__(self, parent=None):
        try:
            super().__init__(parent)
            layout = QVBoxLayout(self)
            self.title = QLabel("Working Memory + Goal Loop")
            self.status = QLabel("No active mission")
            layout.addWidget(self.title)
            layout.addWidget(self.status)
        except Exception:
            self.status = None

    def update_model(self, model):
        text = f"{model.get('mission_title', 'No mission')} | goals: {model.get('active_goals', 0)}"
        if self.status is not None:
            self.status.setText(text)
        return text
