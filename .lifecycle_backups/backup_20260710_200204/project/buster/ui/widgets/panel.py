from PySide6.QtWidgets import QFrame
class Panel(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
