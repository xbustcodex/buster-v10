from __future__ import annotations

import math
import random

from PySide6.QtCore import QPoint, QPointF, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget


class AvatarCanvas(QWidget):
    VALID_STATES = {
        "idle", "thinking", "speaking", "working", "listening",
        "success", "warning", "error", "sleeping", "confused", "excited",
    }

    COLORS = {
        "idle": QColor("#25B9FF"),
        "thinking": QColor("#FFBF2F"),
        "speaking": QColor("#20E3B2"),
        "working": QColor("#7A8CFF"),
        "listening": QColor("#55D7FF"),
        "success": QColor("#31D158"),
        "warning": QColor("#FF9F0A"),
        "error": QColor("#FF453A"),
        "sleeping": QColor("#8E8E93"),
        "confused": QColor("#FF8A65"),
        "excited": QColor("#FFD60A"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = "idle"
        self.pulse = 0
        self.blink = False
        self.blink_ticks = 0
        self.look_ticks = 0
        self.eye_direction = QPoint(0, 0)
        self.setMinimumSize(420, 420)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(50)

    def set_state(self, state: str) -> None:
        state = str(state or "idle").lower()
        self.state = state if state in self.VALID_STATES else "idle"
        self.update()

    def _tick(self) -> None:
        self.pulse = (self.pulse + 1) % 360
        self.blink_ticks += 1
        if not self.blink and self.blink_ticks > random.randint(60, 100):
            self.blink = True
            self.blink_ticks = 0
        elif self.blink and self.blink_ticks > 4:
            self.blink = False
            self.blink_ticks = 0

        self.look_ticks += 1
        if self.look_ticks > random.randint(80, 150):
            self.eye_direction = QPoint(random.randint(-10, 10), random.randint(-7, 7))
            self.look_ticks = 0
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = float(self.width()), float(self.height())
        cx, cy = w / 2, h / 2 - 8
        accent = self.COLORS[self.state]

        glow = QRadialGradient(cx, cy, min(w, h) * 0.62)
        c = QColor(accent); c.setAlpha(70)
        glow.setColorAt(0.0, c)
        glow.setColorAt(0.45, QColor(8, 25, 49, 130))
        glow.setColorAt(1.0, QColor(2, 8, 18, 0))
        p.fillRect(self.rect(), glow)

        p.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 45), 1))
        for i in range(5):
            r = 170 + i * 27 + math.sin(math.radians(self.pulse)) * 4
            p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))

        p.setBrush(QColor("#111F33"))
        p.setPen(QPen(QColor("#9FB7CF"), 7))
        p.drawEllipse(QRectF(cx-145, cy-145, 290, 290))

        p.setBrush(QColor("#020812"))
        p.setPen(QPen(accent, 5))
        p.drawEllipse(QRectF(cx-125, cy-125, 250, 250))

        for side in (-1, 1):
            x = cx + side * 148
            p.setBrush(QColor("#10203A"))
            p.setPen(QPen(QColor("#AFC6DF"), 4))
            p.drawRoundedRect(QRectF(x-18, cy-38, 36, 86), 15, 15)
            p.setBrush(accent); p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(x-8, cy-26, 16, 62), 7, 7)

        eye_y = cy - 34
        if self.state == "sleeping" or self.blink:
            p.setPen(QPen(accent, 7, Qt.SolidLine, Qt.RoundCap))
            for side in (-1, 1):
                ex = cx + side * 58
                p.drawArc(QRectF(ex-24, eye_y-6, 48, 22), 10*16, 160*16)
        else:
            for side in (-1, 1):
                ex = cx + side * 58 + self.eye_direction.x() * 0.6
                ey = eye_y + self.eye_direction.y() * 0.6
                eg = QRadialGradient(ex, ey, 36)
                eg.setColorAt(0.0, accent)
                eg.setColorAt(0.55, QColor("#0076C8"))
                eg.setColorAt(1.0, QColor(0, 80, 160, 0))
                p.setBrush(eg); p.setPen(Qt.NoPen)
                p.drawEllipse(QRectF(ex-34, ey-34, 68, 68))
                p.setBrush(QColor("#051326")); p.setPen(QPen(accent, 6))
                p.drawEllipse(QRectF(ex-27, ey-27, 54, 54))
                p.setBrush(accent); p.setPen(Qt.NoPen)
                p.drawEllipse(QRectF(ex-11, ey-11, 22, 22))
                p.setBrush(QColor("#001020")); p.drawEllipse(QRectF(ex-5, ey-5, 10, 10))
                p.setBrush(QColor("white")); p.drawEllipse(QRectF(ex+5, ey-10, 9, 9))

        mouth_y = cy + 65
        p.setPen(QPen(accent, 7, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        if self.state in {"speaking", "listening", "excited"}:
            opening = 24 + math.sin(math.radians(self.pulse * 5)) * 7
            p.setBrush(accent); p.setPen(Qt.NoPen)
            p.drawEllipse(QRectF(cx-28, mouth_y-opening/2, 56, opening))
        elif self.state in {"thinking", "working", "warning", "error", "confused"}:
            p.drawLine(QPointF(cx-30, mouth_y), QPointF(cx+30, mouth_y))
        else:
            p.drawArc(QRectF(cx-43, mouth_y-23, 86, 49), 200*16, 140*16)

        p.end()
