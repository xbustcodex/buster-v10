from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtWidgets import QWidget

class AvatarCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "idle"
        self.pulse = 0
        self.setMinimumSize(220, 220)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(80)

    def set_state(self, state):
        self.state = state
        self.update()

    def tick(self):
        self.pulse = (self.pulse + 1) % 100
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w // 2
        cy = h // 2

        glow = 40 + (self.pulse % 40)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(32, 168, 255, 35))
        p.drawEllipse(cx - glow, cy - glow, glow * 2, glow * 2)

        p.setBrush(QColor(8, 20, 38))
        p.setPen(QPen(QColor(32, 168, 255), 4))
        p.drawEllipse(cx - 70, cy - 70, 140, 140)

        eye_y = cy - 20
        mouth_y = cy + 32

        if self.state == "thinking":
            eye_color = QColor(255, 210, 80)
            mouth = "flat"
        elif self.state == "speaking":
            eye_color = QColor(80, 255, 180)
            mouth = "open"
        elif self.state == "error":
            eye_color = QColor(255, 80, 80)
            mouth = "flat"
        elif self.state == "success":
            eye_color = QColor(80, 255, 120)
            mouth = "smile"
        else:
            eye_color = QColor(32, 168, 255)
            mouth = "smile"

        p.setBrush(eye_color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(cx - 38, eye_y, 18, 18)
        p.drawEllipse(cx + 20, eye_y, 18, 18)

        p.setPen(QPen(eye_color, 5))

        if mouth == "open":
            p.drawEllipse(cx - 16, mouth_y - 8, 32, 22)
        elif mouth == "flat":
            p.drawLine(cx - 24, mouth_y, cx + 24, mouth_y)
        else:
            p.drawArc(cx - 30, mouth_y - 18, 60, 35, 200 * 16, 140 * 16)

        p.end()
