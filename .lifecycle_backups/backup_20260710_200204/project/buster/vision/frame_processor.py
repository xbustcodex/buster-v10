from buster.vision.types import VisionResult
from buster.vision.face_detection import FaceDetector
from buster.vision.face_recognition import FaceRecognizer
from buster.vision.object_detection import ObjectDetector
from buster.vision.ocr import OCREngine
from buster.vision.qr_scanner import QRScanner

class FrameProcessor:
    def __init__(self, settings):
        self.settings = settings
        self.face_detector = FaceDetector()
        self.face_recognizer = FaceRecognizer()
        self.object_detector = ObjectDetector(settings)
        self.ocr = OCREngine()
        self.qr = QRScanner()

    def process(self, frame, fps=0.0):
        if frame is None:
            return VisionResult([], [], [], "", fps, 0, 0)
        h, w = frame.shape[:2]
        faces = self.face_detector.process(frame) if self.settings.enable_faces else []
        faces = self.face_recognizer.recognize(frame, faces)
        objects = self.object_detector.process(frame) if self.settings.enable_objects else []
        qr_codes = self.qr.scan(frame) if self.settings.enable_qr else []
        text = self.ocr.read_frame(frame) if self.settings.enable_ocr else ""
        return VisionResult(faces, objects, qr_codes, text, fps, w, h)

    def learn_face(self, name, frame, faces):
        return self.face_recognizer.learn(name, frame, faces)

    def identify_face(self, frame, faces):
        return self.face_recognizer.identify_best(frame, faces)

    def status(self):
        return (
            f"Faces: {'ready' if self.face_detector.ready else 'not ready'}, "
            f"Recognition: {self.face_recognizer.status()}, "
            f"Objects: {self.object_detector.status()}, "
            f"QR: {'ready' if self.qr.ready else 'pyzbar not installed'}, "
            f"OCR: scaffold"
        )
