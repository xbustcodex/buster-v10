from PySide6.QtCore import QTimer
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QWidget

class FaceWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.state = "standby"
        self.frame = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(45)

    def set_state(self, state):
        self.state = state
        self.update()

    def tick(self):
        self.frame = (self.frame + 1) % 180
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#02070d"))
        p.setPen(QPen(QColor("#00c8ff"), 5))
        w, h = self.width(), self.height()
        eye_r = min(w, h) // 12
        blink = self.frame % 110 in [0, 1, 2]
        y = h // 2 - 40 + int((self.frame % 40) / 8)
        if self.state == "listening":
            y += int((self.frame % 14) - 7)
        x1, x2 = w // 2 - 100, w // 2 + 100
        if blink and self.state == "standby":
            p.drawLine(x1-eye_r, y, x1+eye_r, y)
            p.drawLine(x2-eye_r, y, x2+eye_r, y)
        else:
            p.drawEllipse(x1-eye_r, y-eye_r, eye_r*2, eye_r*2)
            p.drawEllipse(x2-eye_r, y-eye_r, eye_r*2, eye_r*2)
        mouth_y = h // 2 + 65
        if self.state == "speaking":
            for i in range(11):
                x = w // 2 - 65 + i * 13
                amp = 4 + ((self.frame + i * 5) % 20)
                p.drawLine(x, mouth_y-amp, x, mouth_y+amp)
        elif self.state == "thinking":
            for i in range(10):
                p.drawEllipse(w//2 - 55 + i*12, mouth_y, 6, 6)
        elif self.state == "listening":
            for i in range(16):
                x = w // 2 - 100 + i * 13
                amp = 4 + ((self.frame + i * 2) % 16)
                p.drawLine(x, mouth_y-amp, x, mouth_y+amp)
        else:
            p.drawLine(w//2 - 38, mouth_y, w//2 + 38, mouth_y)
