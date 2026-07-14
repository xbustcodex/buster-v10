import time
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QImage
from buster.vision.settings import VisionSettings
from buster.vision.camera import Camera
from buster.vision.frame_processor import FrameProcessor
from buster.vision.overlay import OverlayRenderer
from buster.vision.snapshot import SnapshotManager

class VisionEngine(QObject):
    frame_ready = Signal(object)
    result_ready = Signal(object)

    def __init__(self, bus=None):
        super().__init__()
        self.bus = bus
        self.settings = VisionSettings()
        self.camera = None
        self.processor = None
        self.overlay = None
        self.snapshots = SnapshotManager(self.settings.snapshots_dir)
        self.loaded = False
        self.active = False
        self.state = "lazy"
        self.last_frame = None
        self.last_result = None
        self.last_time = time.time()
        self.fps = 0.0
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)

    def _lazy_load(self):
        if self.loaded:
            return
        self.state = "loading"
        self.camera = Camera(self.settings.camera_index, self.settings.width, self.settings.height)
        self.processor = FrameProcessor(self.settings)
        self.overlay = OverlayRenderer()
        self.loaded = True
        self.state = "loaded"

    def start(self):
        if self.active:
            return "Vision is already running."
        self._lazy_load()
        if not self.camera.open():
            self.state = "error"
            return "Could not open webcam. Check Windows camera permission or camera index."
        self.active = True
        self.state = "running"
        self.timer.start(int(1000 / max(1, self.settings.fps_limit)))
        if self.bus:
            self.bus.emit("vision_status", status="active")
        return "Vision started. Webcam is live."

    def stop(self):
        self.timer.stop()
        if self.camera:
            self.camera.close()
        self.active = False
        self.state = "stopped"
        if self.bus:
            self.bus.emit("vision_status", status="stopped")
        return "Vision stopped."

    def _tick(self):
        if not self.camera or not self.processor:
            return
        frame = self.camera.read()
        if frame is None:
            return
        now = time.time()
        self.fps = 1.0 / max(0.001, now - self.last_time)
        self.last_time = now
        result = self.processor.process(frame, fps=self.fps)
        display = self.overlay.draw(frame.copy(), result)
        self.last_frame = frame
        self.last_result = result
        self.frame_ready.emit(self.cv_to_qimage(display))
        self.result_ready.emit(result)

    def cv_to_qimage(self, frame):
        import cv2
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        return QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()

    def take_photo(self):
        if self.last_frame is None:
            return "No camera frame available yet. Start vision first."
        return f"Vision snapshot saved: {self.snapshots.save(self.last_frame)}"

    def detect_faces(self):
        if not self.last_result:
            return "No vision result yet. Start vision first."
        count = len(self.last_result.faces)
        return f"Detected {count} face(s)." if count == 0 else f"Detected {count} face(s): " + ", ".join([f.label for f in self.last_result.faces])

    def learn_face(self, name="Adam"):
        if self.last_frame is None or self.last_result is None:
            return "No camera frame available yet. Start vision first."
        return self.processor.learn_face(name, self.last_frame, self.last_result.faces)

    def identify_face(self):
        if self.last_frame is None or self.last_result is None:
            return "No camera frame available yet. Start vision first."
        return self.processor.identify_face(self.last_frame, self.last_result.faces)

    def face_status(self):
        if not self.processor:
            return "Face recognizer has not loaded yet. Start vision first."
        return self.processor.face_recognizer.status()

    def detect_objects(self):
        if not self.last_result:
            return "No vision result yet. Start vision first."
        if not self.last_result.objects:
            return "Detected 0 objects."
        labels = {}
        for item in self.last_result.objects:
            labels[item.label] = labels.get(item.label, 0) + 1
        return "Detected objects: " + ", ".join([f"{count} {label}" for label, count in labels.items()]) + "."

    def scan_qr(self):
        if not self.last_result:
            return "No vision result yet. Start vision first."
        if not self.processor.qr.ready:
            return "QR scanner needs pyzbar installed. Run: python -m pip install pyzbar"
        if not self.last_result.qr_codes:
            return "No QR or barcode found."
        return "QR/barcode: " + " | ".join([x.get("text", "") for x in self.last_result.qr_codes])

    def read_text(self):
        if self.last_frame is None:
            return "No camera frame available yet. Start vision first."
        return self.processor.ocr.read_frame(self.last_frame)

    def status(self):
        if not self.loaded:
            return "Vision lazy loaded. Say start vision to load camera and YOLO."
        return f"Vision {'active' if self.active else 'standby'}. FPS {self.fps:.1f}. {self.processor.status()}"
