from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QTextEdit

class VisionWindow(QWidget):
    def __init__(self, vision):
        super().__init__()
        self.vision = vision
        self.setWindowTitle("Buster Vision")
        self.resize(760, 620)

        layout = QVBoxLayout(self)
        self.image = QLabel("Vision not started")
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setMinimumSize(640, 480)
        self.info = QTextEdit()
        self.info.setReadOnly(True)
        self.info.setMaximumHeight(110)

        buttons = QHBoxLayout()
        for label, func in [("Start", self.vision.start), ("Stop", self.vision.stop), ("Photo", self.vision.take_photo), ("Faces", self.vision.detect_faces), ("QR", self.vision.scan_qr)]:
            b = QPushButton(label)
            b.clicked.connect(lambda checked=False, f=func: self.info.append(f()))
            buttons.addWidget(b)

        layout.addWidget(self.image)
        layout.addLayout(buttons)
        layout.addWidget(self.info)

        self.vision.frame_ready.connect(self.on_frame)
        self.vision.result_ready.connect(self.on_result)

    def on_frame(self, qimage):
        self.image.setPixmap(QPixmap.fromImage(qimage).scaled(self.image.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def on_result(self, result):
        self.info.setPlainText(
            f"FPS: {result.fps:.1f}\n"
            f"Faces: {len(result.faces)}\n"
            f"Objects: {len(result.objects)}\n"
            f"QR/Barcode: {len(result.qr_codes)}"
        )
