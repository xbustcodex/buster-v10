"""
vision_engine.py - Standalone Vision Engine & Tracker Module
Handles camera capture, frame processing, and object tracking in a dedicated QThread.
"""

import cv2
import numpy as np
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
from enum import Enum

from PySide6.QtCore import QThread, Signal, QMutex, QElapsedTimer
from PySide6.QtGui import QImage




# ==================== Data Models ====================

@dataclass
class VisionResult:
    """Vision processing result payload"""
    fps: float = 0.0
    faces: List[Tuple[int, int, int, int]] = field(default_factory=list)
    objects: List[Tuple[str, float, int, int, int, int]] = field(default_factory=list)
    qr_codes: List[str] = field(default_factory=list)
    barcodes: List[str] = field(default_factory=list)
    text_detected: List[str] = field(default_factory=list)


class VisionMode(Enum):
    NORMAL = "normal"
    FACES = "faces"
    OBJECTS = "objects"
    QR = "qr"
    TEXT = "text"
    EDGE = "edge"
    SEGMENT = "segment"


# ==================== Tracker Class ====================

class CentroidTracker:
    """
    High-performance, robust Centroid & IoU Object Tracker.
    Maintains persistent IDs across occlusions using Euclidean distance matching.
    """
    def __init__(self, max_disappeared: int = 20, max_distance: float = 100.0):
        self.next_object_id = 0
        self.objects: Dict[int, Tuple[int, int]] = {}
        self.bboxes: Dict[int, Tuple[int, int, int, int]] = {}
        self.labels: Dict[int, str] = {}
        self.confidences: Dict[int, float] = {}
        self.disappeared: Dict[int, int] = {}
        self.trails: Dict[int, deque] = defaultdict(lambda: deque(maxlen=30))
        self.colors: Dict[int, Tuple[int, int, int]] = {}
        
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def register(self, centroid: Tuple[int, int], bbox: Tuple[int, int, int, int], label: str, confidence: float):
        obj_id = self.next_object_id
        self.objects[obj_id] = centroid
        self.bboxes[obj_id] = bbox
        self.labels[obj_id] = label
        self.confidences[obj_id] = confidence
        self.disappeared[obj_id] = 0
        self.trails[obj_id].append(centroid)
        self.colors[obj_id] = (
            int(np.random.randint(80, 255)),
            int(np.random.randint(80, 255)),
            int(np.random.randint(80, 255))
        )
        self.next_object_id += 1

    def deregister(self, object_id: int):
        del self.objects[object_id]
        del self.bboxes[object_id]
        del self.labels[object_id]
        del self.confidences[object_id]
        del self.disappeared[object_id]
        del self.trails[object_id]
        del self.colors[object_id]

    def update(self, rects: List[Tuple[Tuple[int, int, int, int], str, float]]) -> Dict[int, Tuple[int, int, int, int]]:
        if len(rects) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            return self.bboxes

        input_centroids = np.zeros((len(rects), 2), dtype="int")
        input_rects = []
        input_labels = []
        input_confs = []

        for i, (bbox, label, conf) in enumerate(rects):
            x, y, w, h = bbox
            cX = int(x + (w / 2.0))
            cY = int(y + (h / 2.0))
            input_centroids[i] = (cX, cY)
            input_rects.append(bbox)
            input_labels.append(label)
            input_confs.append(conf)

        if len(self.objects) == 0:
            for i in range(0, len(input_centroids)):
                self.register(input_centroids[i], input_rects[i], input_labels[i], input_confs[i])
        else:
            object_ids = list(self.objects.keys())
            object_centroids = list(self.objects.values())

            D = np.linalg.norm(np.array(object_centroids)[:, np.newaxis] - input_centroids, axis=2)
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows, used_cols = set(), set()

            for (row, col) in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue
                if D[row, col] > self.max_distance:
                    continue

                object_id = object_ids[row]
                self.objects[object_id] = input_centroids[col]
                self.bboxes[object_id] = input_rects[col]
                self.labels[object_id] = input_labels[col]
                self.confidences[object_id] = input_confs[col]
                self.disappeared[object_id] = 0
                self.trails[object_id].append(input_centroids[col])

                used_rows.add(row)
                used_cols.add(col)

            unused_rows = set(range(0, D.shape[0])).difference(used_rows)
            unused_cols = set(range(0, D.shape[1])).difference(used_cols)

            for row in unused_rows:
                object_id = object_ids[row]
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)

            for col in unused_cols:
                self.register(input_centroids[col], input_rects[col], input_labels[col], input_confs[col])

        return self.bboxes

    def draw_tracks(self, frame: np.ndarray):
        for obj_id, bbox in self.bboxes.items():
            x, y, w, h = bbox
            color = self.colors.get(obj_id, (0, 255, 0))
            label = self.labels.get(obj_id, "Target")
            conf = self.confidences.get(obj_id, 1.0)

            # Draw Box
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2, cv2.LINE_AA)

            # Draw Label Tag
            tag = f"ID:{obj_id} {label} {conf:.2f}"
            (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (x, max(0, y - th - 6)), (x + tw + 6, y), color, -1)
            cv2.putText(frame, tag, (x + 3, max(th, y - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

            # Draw Tracking Trail
            trail = self.trails[obj_id]
            for i in range(1, len(trail)):
                if trail[i - 1] is None or trail[i] is None:
                    continue
                thickness = int(np.sqrt(30 / float(i + 1)) * 1.5)
                cv2.line(frame, trail[i - 1], trail[i], color, max(1, thickness), cv2.LINE_AA)

    def clear(self):
        self.objects.clear()
        self.bboxes.clear()
        self.labels.clear()
        self.confidences.clear()
        self.disappeared.clear()
        self.trails.clear()
        self.colors.clear()
        self.next_object_id = 0


# ==================== Vision Processing Engine ====================

class VisionEngine(QThread):
    frame_ready = Signal(QImage)
    result_ready = Signal(VisionResult)
    status_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.camera = None
        self.running = False
        self.mode = VisionMode.NORMAL
        self.mutex = QMutex()
        
        self.face_cascade = None
        self.qr_detector = None
        
        self.frame_count = 0
        self.fps_timer = QElapsedTimer()
        self.fps = 0.0

        self.tracker = CentroidTracker()
        self.tracking_active = False

        self._init_detectors()

    def _init_detectors(self):
        try:
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(face_cascade_path)
            self.qr_detector = cv2.QRCodeDetector()
            self.status_changed.emit("Vision engine initialized")
        except Exception as e:
            self.status_changed.emit(f"Detector init error: {str(e)}")

    def start_camera(self, camera_id: int = 0):
        self.mutex.lock()
        try:
            if self.camera is not None:
                self.camera.release()

            self.camera = cv2.VideoCapture(camera_id)
            if not self.camera.isOpened():
                self.camera.release()
                self.camera = None
                self.running = False
                self.status_changed.emit(f"Error opening camera {camera_id}")
                return

            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)

            self.running = True
            self.fps_timer.start()
            self.frame_count = 0

            if not self.isRunning():
                self.start()

            self.status_changed.emit(f"Camera {camera_id} started")
        except Exception as exc:
            self.running = False
            self.status_changed.emit(f"Error starting camera: {exc}")
        finally:
            self.mutex.unlock()

    def stop_camera(self):
        self.mutex.lock()
        try:
            self.running = False
            if self.camera is not None:
                self.camera.release()
                self.camera = None
        finally:
            self.mutex.unlock()
        self.status_changed.emit("Camera stopped")

    def set_mode(self, mode: VisionMode):
        self.mode = mode
        self.status_changed.emit(f"Mode: {mode.value}")

    def run(self):
        frame_counter = 0
        while self.running:
            self.mutex.lock()
            if self.camera is None or not self.camera.isOpened():
                self.mutex.unlock()
                self.msleep(10)
                continue

            ret, frame = self.camera.read()
            self.mutex.unlock()

            if not ret:
                continue

            frame_counter += 1
            processed_frame, result = self._process_frame(frame, frame_counter)

            # FPS Calculation
            self.frame_count += 1
            if self.fps_timer.elapsed() >= 1000:
                self.fps = self.frame_count * 1000.0 / self.fps_timer.elapsed()
                self.frame_count = 0
                self.fps_timer.restart()
            result.fps = self.fps

            # Convert Frame to QImage
            height, width, _ = processed_frame.shape
            bytes_per_line = 3 * width
            qimage = QImage(processed_frame.data, width, height, bytes_per_line, QImage.Format_RGB888).copy()

            self.frame_ready.emit(qimage)
            self.result_ready.emit(result)

            self.msleep(15)

    def _process_frame(self, frame: np.ndarray, frame_counter: int) -> Tuple[np.ndarray, VisionResult]:
        result = VisionResult()
        processed = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        detections = []

        if self.mode == VisionMode.FACES or self.tracking_active:
            if frame_counter % 2 == 0 and self.face_cascade:
                gray = cv2.cvtColor(processed, cv2.COLOR_RGB2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))
                for (x, y, w, h) in faces:
                    result.faces.append((int(x), int(y), int(w), int(h)))
                    detections.append(((int(x), int(y), int(w), int(h)), "Face", 0.92))

        if self.mode == VisionMode.QR:
            processed, result.qr_codes = self._scan_qr(processed)

        elif self.mode == VisionMode.EDGE:
            processed = self._detect_edges(processed)

        if self.tracking_active:
            self.tracker.update(detections)
            self.tracker.draw_tracks(processed)

        return processed, result

    def _scan_qr(self, frame: np.ndarray) -> Tuple[np.ndarray, List[str]]:
        qr_codes = []
        try:
            data, bbox, _ = self.qr_detector.detectAndDecode(frame)
            if data:
                qr_codes.append(data)
                if bbox is not None:
                    bbox = bbox.astype(int)
                    cv2.polylines(frame, [bbox], True, (0, 255, 0), 2)
                    cv2.putText(frame, f"QR: {data}", (bbox[0][0][0], bbox[0][0][1] - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        except Exception:
            pass
        return frame, qr_codes

    def _detect_edges(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)