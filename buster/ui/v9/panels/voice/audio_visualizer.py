"""
audio_visualizer.py - Canvas Widget for Realtime Audio Spectrum Rendering
Supports Waveform, Frequency Spectrum, and Heatmap Spectrogram views.
"""

import numpy as np
from PySide6.QtCore import QPoint
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget


class AudioVisualizer(QWidget):
    """Widget for audio visualization rendering"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_data = np.zeros(1024)
        self.fft_data = np.zeros(512)
        self.mode = "waveform"  # waveform, spectrum, spectrogram
        self.setMinimumHeight(150)
        self.setMinimumWidth(400)

    def update_data(self, audio_data: np.ndarray):
        """Update active audio buffer"""
        self.audio_data = audio_data[:1024]
        self.fft_data = np.abs(np.fft.fft(self.audio_data))[:512]
        self.update()

    def set_mode(self, mode: str):
        """Set visualization display mode"""
        self.mode = mode
        self.update()

    def paintEvent(self, event):
        """Render viewport canvas"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background Fill
        painter.fillRect(self.rect(), QColor(26, 26, 26))

        if self.mode == "waveform":
            self._draw_waveform(painter)
        elif self.mode == "spectrum":
            self._draw_spectrum(painter)
        elif self.mode == "spectrogram":
            self._draw_spectrogram(painter)

    def _draw_waveform(self, painter: QPainter):
        """Draw dynamic oscillating oscilloscope lines"""
        if len(self.audio_data) < 2:
            return

        width = self.width()
        height = self.height()
        center_y = height // 2

        max_val = np.max(np.abs(self.audio_data)) or 1
        normalized = self.audio_data / max_val

        step = max(1, len(normalized) // width)

        painter.setPen(QPen(QColor(78, 201, 176), 2))

        points = []
        for i in range(0, len(normalized), step):
            x = int(i / len(normalized) * width)
            y = int(center_y + normalized[i] * height * 0.4)
            points.append(QPoint(x, y))

        if len(points) > 1:
            painter.drawPolyline(points)

        # Ambient Glow Overlay
        glow_color = QColor(78, 201, 176, 50)
        painter.setPen(QPen(glow_color, 8))
        if len(points) > 1:
            painter.drawPolyline(points)

    def _draw_spectrum(self, painter: QPainter):
        """Draw vertical FFT frequency equalizer bars"""
        if len(self.fft_data) < 2:
            return

        width = self.width()
        height = self.height()

        max_val = np.max(self.fft_data) or 1
        normalized = self.fft_data / max_val

        bar_width = width / len(normalized)

        for i, value in enumerate(normalized):
            x = int(i * bar_width)
            bar_height = int(value * height * 0.8)
            y = height - bar_height

            intensity = value * 255
            color = QColor(
                int(78 + intensity * 0.5),
                int(201 - intensity * 0.3),
                int(176 - intensity * 0.4)
            )

            painter.fillRect(x, y, max(1, int(bar_width)), bar_height, color)

    def _draw_spectrogram(self, painter: QPainter):
        """Draw simplified color intensity heatmap spectrum"""
        if len(self.fft_data) < 2:
            return

        width = self.width()
        height = self.height()

        max_val = np.max(self.fft_data) or 1
        normalized = self.fft_data / max_val

        bar_width = width / len(normalized)

        for i, value in enumerate(normalized):
            x = int(i * bar_width)
            bar_height = int(value * height * 0.8)
            y = height - bar_height

            if value > 0.8:
                color = QColor(255, 0, 0)
            elif value > 0.6:
                color = QColor(255, 128, 0)
            elif value > 0.4:
                color = QColor(255, 255, 0)
            elif value > 0.2:
                color = QColor(0, 255, 0)
            else:
                color = QColor(0, 128, 255)

            painter.fillRect(x, y, max(1, int(bar_width)), bar_height, color)