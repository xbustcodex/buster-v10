
"""
vision_panel.py - Buster Vision Panel with PySide6
A comprehensive vision processing panel with camera control, face detection, QR scanning, and more.
"""

import sys
import cv2
import numpy as np
import json
import time
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum
from buster.runtime.core import BusterRuntimeCore
import uuid
from collections import defaultdict

# ==================== Data Models ====================

@dataclass
class VisionResult:
    """Vision processing result"""
    fps: float = 0.0
    faces: List[Tuple[int, int, int, int]] = None
    objects: List[Tuple[str, float, int, int, int, int]] = None
    qr_codes: List[str] = None
    barcodes: List[str] = None
    text_detected: List[str] = None
    
    def __post_init__(self):
        self.faces = self.faces or []
        self.objects = self.objects or []
        self.qr_codes = self.qr_codes or []
        self.barcodes = self.barcodes or []
        self.text_detected = self.text_detected or []
        
# ==================== Advanced Tracker Classes ====================

class TrackedObject:
    """Represents a tracked object with history"""
    def __init__(self, tracker, bbox, label="Object", confidence=1.0):
        self.id = str(uuid.uuid4())[:8]
        self.tracker = tracker
        self.bbox = bbox
        self.label = label
        self.confidence = confidence
        self.trail = []
        self.frames_since_update = 0
        self.max_trail_length = 30
        self.color = (np.random.randint(50, 255), 
                      np.random.randint(50, 255), 
                      np.random.randint(50, 255))
        self.last_seen = time.time()
        self.predicted_bbox = bbox
        
    def update(self, bbox, confidence=1.0):
        self.bbox = bbox
        self.confidence = confidence
        self.frames_since_update = 0
        self.last_seen = time.time()
        center_x = bbox[0] + bbox[2] // 2
        center_y = bbox[1] + bbox[3] // 2
        self.trail.append((center_x, center_y))
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)
    
    def predict_next_position(self):
        if len(self.trail) >= 3:
            dx = self.trail[-1][0] - self.trail[-2][0]
            dy = self.trail[-1][1] - self.trail[-2][1]
            next_x = self.trail[-1][0] + dx
            next_y = self.trail[-1][1] + dy
            self.predicted_bbox = (
                next_x - self.bbox[2]//2,
                next_y - self.bbox[3]//2,
                self.bbox[2],
                self.bbox[3]
            )
        return self.predicted_bbox

class AdvancedTracker:
    """Advanced object tracking with multiple algorithms"""
    
    def __init__(self, tracker_type='auto', max_objects=10, min_confidence=0.3):
        self.max_objects = max_objects
        self.min_confidence = min_confidence
        self.tracked_objects = []
        self.frame_width = 640
        self.frame_height = 480
        self.next_id = 0
        self.mutex = QMutex()
        self.tracker_type = self._get_best_available_tracker()
        self._track_skip_counter = 0
        self._track_skip_max = 2  # Only track every 2nd frame
        
        if self.tracker_type:
            print(f"✅ AdvancedTracker initialized with: {self.tracker_type}")
        else:
            print("⚠️ AdvancedTracker: No real tracker available - using dummy")
    
    def _get_best_available_tracker(self):
        if hasattr(cv2, 'TrackerCSRT_create'):
            return 'CSRT'
        elif hasattr(cv2, 'TrackerKCF_create'):
            return 'KCF'
        elif hasattr(cv2, 'TrackerMedianFlow_create'):
            return 'MEDIANFLOW'
        elif hasattr(cv2, 'legacy'):
            if hasattr(cv2.legacy, 'TrackerCSRT_create'):
                return 'legacy_CSRT'
            elif hasattr(cv2.legacy, 'TrackerKCF_create'):
                return 'legacy_KCF'
        elif hasattr(cv2, 'Tracker_create'):
            return 'GENERIC'
        else:
            return None
    
    def create_tracker(self, tracker_type=None):
        tracker_type = tracker_type or self.tracker_type
        try:
            if tracker_type == 'CSRT' and hasattr(cv2, 'TrackerCSRT_create'):
                return cv2.TrackerCSRT_create()
            elif tracker_type == 'KCF' and hasattr(cv2, 'TrackerKCF_create'):
                return cv2.TrackerKCF_create()
            elif tracker_type == 'MEDIANFLOW' and hasattr(cv2, 'TrackerMedianFlow_create'):
                return cv2.TrackerMedianFlow_create()
            elif hasattr(cv2, 'legacy'):
                if tracker_type == 'legacy_CSRT' and hasattr(cv2.legacy, 'TrackerCSRT_create'):
                    return cv2.legacy.TrackerCSRT_create()
                elif tracker_type == 'legacy_KCF' and hasattr(cv2.legacy, 'TrackerKCF_create'):
                    return cv2.legacy.TrackerKCF_create()
            elif hasattr(cv2, 'Tracker_create'):
                return cv2.Tracker_create()
        except Exception as e:
            print(f"Error creating tracker: {e}")
        
        class DummyTracker:
            def __init__(self):
                self.bbox = None
            def init(self, frame, bbox):
                self.bbox = bbox
                return True
            def update(self, frame):
                return True, self.bbox if self.bbox else (0, 0, 100, 100)
        return DummyTracker()
    
    def init_tracker(self, frame, bbox, label="Object", confidence=1.0):
        tracker = self.create_tracker()
        try:
            if tracker and tracker.init(frame, bbox):
                obj = TrackedObject(tracker, bbox, label, confidence)
                self.tracked_objects.append(obj)
                return obj
        except Exception as e:
            print(f"Error initializing tracker: {e}")
        return None
    
    def update(self, frame):
        if not self.tracked_objects:
            return []
        
        # Skip frames for performance
        self._track_skip_counter = (self._track_skip_counter + 1) % self._track_skip_max
        if self._track_skip_counter != 0:
            return self.tracked_objects
        
        updated_objects = []
        objects_to_remove = []
        
        self.mutex.lock()
        try:
            for obj in self.tracked_objects:
                try:
                    success, bbox = obj.tracker.update(frame)
                    if success:
                        bbox = tuple(map(int, bbox))
                        obj.update(bbox)
                        updated_objects.append(obj)
                        obj.frames_since_update = 0
                    else:
                        obj.frames_since_update += 1
                        if obj.frames_since_update > 30:
                            objects_to_remove.append(obj)
                except Exception as e:
                    objects_to_remove.append(obj)
            
            for obj in objects_to_remove:
                if obj in self.tracked_objects:
                    self.tracked_objects.remove(obj)
        finally:
            self.mutex.unlock()
        
        return updated_objects
    
    def draw_tracks(
        self,
        frame,
        show_trail=True,
        show_bbox=True,
        show_label=True,
    ):
        for obj in self.tracked_objects:
            x, y, w, h = map(int, obj.bbox)

            if show_bbox:
                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    obj.color,
                    2,
                    cv2.LINE_AA,
                )

                if obj.confidence > 0.5:
                    label = f"{obj.label} {obj.confidence:.2f}"

                    cv2.rectangle(
                        frame,
                        (x, max(0, y - 22)),
                        (x + 120, y),
                        obj.color,
                        -1,
                    )

                    cv2.putText(
                        frame,
                        label,
                        (x + 5, max(12, y - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.4,
                        (255, 255, 255),
                        1,
                        cv2.LINE_AA,
                    )

            if show_trail and len(obj.trail) > 1:
                points = np.array(
                    obj.trail,
                    dtype=np.int32,
                ).reshape((-1, 1, 2))

                cv2.polylines(
                    frame,
                    [points],
                    False,
                    obj.color,
                    2,
                    cv2.LINE_AA,
                )

                predicted = obj.predict_next_position()
                px, py, pw, ph = map(int, predicted)

                cv2.rectangle(
                    frame,
                    (px, py),
                    (px + pw, py + ph),
                    obj.color,
                    1,
                    cv2.LINE_AA,
                )

            if show_label:
                cv2.putText(
                    frame,
                    f"ID:{obj.id}",
                    (x, y + h + 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    obj.color,
                    1,
                    cv2.LINE_AA,
                )
    
    def clear(self):
        self.tracked_objects = []
        self.next_id = 0

class FaceTracker(AdvancedTracker):
    """Specialized face tracker with recognition capabilities"""
    
    def __init__(self, max_faces=10, recognition_model=None):
        super().__init__(tracker_type='auto', max_objects=max_faces)
        self.face_encodings = {}
        self.face_names = {}
        self.recognition_model = recognition_model
        self._detect_counter = 0
        self._detect_skip = 3  # Only detect faces every 3rd frame for performance
        
        try:
            self.face_detector = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            self.eye_detector = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_eye.xml'
            )
        except Exception as e:
            print(f"Error initializing face detector: {e}")
            self.face_detector = None
            self.eye_detector = None
        
    def detect_faces(self, frame):
        """Detect faces in frame - optimized with skip"""
        if self.face_detector is None:
            return []
        
        # Skip frames for performance
        self._detect_counter = (self._detect_counter + 1) % self._detect_skip
        if self._detect_counter != 0:
            return []
        
        try:
            # Resize frame for faster detection
            h, w = frame.shape[:2]
            scale = 0.5
            small_frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
            
            gray = cv2.cvtColor(small_frame, cv2.COLOR_RGB2GRAY)
            faces = self.face_detector.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
            
            # Scale back coordinates
            detected_faces = []
            for (x, y, w, h) in faces:
                x = int(x / scale)
                y = int(y / scale)
                w = int(w / scale)
                h = int(h / scale)
                detected_faces.append((x, y, w, h, 0.8))
            
            return detected_faces
            
        except Exception as e:
            print(f"Error detecting faces: {e}")
            return []
    
    def update_faces(self, frame, detected_faces):
        self.update(frame)
        for (x, y, w, h, confidence) in detected_faces:
            bbox = (x, y, w, h)
            matched = False
            for obj in self.tracked_objects:
                if self._iou(bbox, obj.bbox) > 0.3:
                    new_tracker = self.create_tracker()
                    if new_tracker and new_tracker.init(frame, bbox):
                        obj.tracker = new_tracker
                        obj.update(bbox, confidence)
                        matched = True
                        break
            if not matched and len(self.tracked_objects) < self.max_objects:
                self.init_tracker(frame, bbox, "Face", confidence)
    
    def _iou(self, bbox1, bbox2):
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        intersection = (x_right - x_left) * (y_bottom - y_top)
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        return intersection / union if union > 0 else 0

class VisionMode(Enum):
    NORMAL = "normal"
    FACES = "faces"
    OBJECTS = "objects"
    QR = "qr"
    TEXT = "text"
    EDGE = "edge"
    SEGMENT = "segment"

# ==================== Vision Processing Engine ====================

class VisionEngine(QThread):
    """Background thread for vision processing"""
    
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
        self.object_detector = None
        self.qr_detector = None
        
        self.frame_count = 0
        self.fps_timer = QElapsedTimer()
        self.fps = 0.0
        
        self.face_tracker = None
        self.advanced_tracker = None
        self.tracking_active = False
        self.motion_detection_active = False
        self.prev_frame = None
        
        self._init_detectors()
        
    def _init_detectors(self):
        try:
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(face_cascade_path)
            self.qr_detector = cv2.QRCodeDetector()
            self.object_detector = None
            self.status_changed.emit("Vision engine initialized")
        except Exception as e:
            self.status_changed.emit(f"Error initializing detectors: {str(e)}")
    
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
                self.status_changed.emit(
                    f"Error opening camera {camera_id}"
                )
                return

            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)

            self.running = True
            self.fps_timer.start()
            self.frame_count = 0

            if not self.isRunning():
                self.start()

            self.status_changed.emit(
                f"Camera {camera_id} started"
            )

        except Exception as exc:
            self.running = False
            self.status_changed.emit(
                f"Error starting camera: {exc}"
            )

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
        """Main processing loop with performance optimizations"""
        frame_counter = 0
        process_every_n = 2  # Process every 2nd frame for performance
        
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
            
            # Process frame
            processed_frame, result = self._process_frame(frame)
            
            # Update FPS
            self.frame_count += 1
            if self.fps_timer.elapsed() >= 1000:
                self.fps = self.frame_count * 1000 / self.fps_timer.elapsed()
                self.frame_count = 0
                self.fps_timer.restart()
            result.fps = self.fps
            
            # Convert to QImage
            height, width, channel = processed_frame.shape
            bytes_per_line = 3 * width
            qimage = QImage(processed_frame.data, width, height, bytes_per_line, QImage.Format_RGB888).copy()
            
            # Emit signals
            self.frame_ready.emit(qimage)
            self.result_ready.emit(result)
            
            # Process tracking - only if tracking is active and not too often
            if self.tracking_active and frame_counter % 2 == 0:
                try:
                    tracking_frame = processed_frame.copy()
                    face_count = 0
                    obj_count = 0
                    
                    # Face tracking
                    if self.face_tracker:
                        # Update existing trackers first
                        self.face_tracker.update(tracking_frame)
                        face_count = len(self.face_tracker.tracked_objects)
                        
                        # Only detect new faces every few frames
                        if frame_counter % 6 == 0:
                            detected_faces = self.face_tracker.detect_faces(tracking_frame)
                            if detected_faces:
                                self.face_tracker.update_faces(tracking_frame, detected_faces)
                                face_count = len(self.face_tracker.tracked_objects)
                        
                        if face_count > 0:
                            self.face_tracker.draw_tracks(tracking_frame, show_trail=True, show_bbox=True)
                    
                    # Object tracking
                    if self.advanced_tracker:
                        self.advanced_tracker.update(tracking_frame)
                        obj_count = len(self.advanced_tracker.tracked_objects)
                        if obj_count > 0:
                            self.advanced_tracker.draw_tracks(tracking_frame, show_trail=True, show_bbox=True)
                    
                    # Update stats
                    if hasattr(self, 'face_tracker') and self.face_tracker:
                        face_count = len(self.face_tracker.tracked_objects)
                    if hasattr(self, 'advanced_tracker') and self.advanced_tracker:
                        obj_count = len(self.advanced_tracker.tracked_objects)
                    
                    # Emit tracking data
                    if face_count > 0 or obj_count > 0:
                        tracking_qimage = QImage(tracking_frame.data, width, height, bytes_per_line, QImage.Format_RGB888).copy()
                        self.frame_ready.emit(tracking_qimage)
                        self.status_changed.emit(f"🎯 Tracking: {face_count} faces, {obj_count} objects")
                        
                except Exception as e:
                    print(f"Tracking error: {e}")
            
            self.msleep(20)  # Control frame rate ~30fps
    
    def _process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, VisionResult]:
        result = VisionResult()
        processed = frame.copy()
        processed = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
        
        if self.mode == VisionMode.FACES:
            processed, result.faces = self._detect_faces(processed)
        elif self.mode == VisionMode.QR:
            processed, result.qr_codes = self._scan_qr(processed)
        elif self.mode == VisionMode.EDGE:
            processed = self._detect_edges(processed)
        elif self.mode == VisionMode.TEXT:
            processed, result.text_detected = self._detect_text(processed)
        
        return processed, result
    
    def _detect_faces(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Tuple[int, int, int, int]]]:
        if self.face_cascade is None:
            return frame, []
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"Face", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return frame, [(x, y, w, h) for (x, y, w, h) in faces]
    
    def _scan_qr(self, frame: np.ndarray) -> Tuple[np.ndarray, List[str]]:
        qr_codes = []
        try:
            data, bbox, _ = self.qr_detector.detectAndDecode(frame)
            if data:
                qr_codes.append(data)
                if bbox is not None:
                    bbox = bbox.astype(int)
                    cv2.polylines(frame, [bbox], True, (0, 255, 0), 2)
                    cv2.putText(frame, f"QR: {data}", (bbox[0][0][0], bbox[0][0][1]-10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        except Exception as e:
            pass
        return frame, qr_codes
    
    def _detect_edges(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
    
    def _detect_text(self, frame: np.ndarray) -> Tuple[np.ndarray, List[str]]:
        return frame, ["Text detection placeholder"]

# ==================== Vision Panel Widget ====================

class VisionPanel(QWidget):
    """Main vision panel widget"""
    
    def __init__(self, live=None, parent=None, runtime_core=None):
        if live is not None and not isinstance(live, QWidget):
            if isinstance(live, BusterRuntimeCore):
                if runtime_core is None:
                    runtime_core = live
                live = None
        if parent is not None and not isinstance(parent, QWidget):
            if runtime_core is None and isinstance(parent, BusterRuntimeCore):
                runtime_core = parent
            parent = None
        
        super().__init__(parent)
        self.live = live
        self.runtime_core = runtime_core
        
        self.vision = VisionEngine()
        self.current_result = VisionResult()
        
        self.tracking_active = False
        self.motion_detection_active = False
        self.face_recognition_active = False
        self.recording_active = False
        self.prev_frame = None
        self.motion_threshold = 5000
        self.known_faces = {}
        self.video_writer = None
        self.recording_filename = ""
        
        self.advanced_tracker = None
        self.face_tracker = None
        self._prev_gray = None
        self._tracker_initialized = False  # Add this flag
    
        self.setup_ui()
        self.connect_signals()
        self.apply_dark_theme()
        
        self.add_tracking_controls()
        
        
        self.vision.frame_ready.connect(self.update_frame)
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("👁️ Buster Vision")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        self.status_indicator = QLabel("● Ready")
        self.status_indicator.setStyleSheet("color: #4ec9b0; font-weight: bold;")
        header_layout.addWidget(self.status_indicator)
        
        self.fps_label = QLabel("FPS: 0.0")
        self.fps_label.setStyleSheet("color: #569cd6; font-weight: bold;")
        header_layout.addWidget(self.fps_label)
        layout.addWidget(header_widget)
        
        content_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(content_splitter, 1)
        
        self.image_label = QLabel("Camera not started")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 2px solid #333333;
                border-radius: 8px;
                color: #666666;
            }
        """)
        content_splitter.addWidget(self.image_label)
        
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(8)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ Start")
        self.start_btn.setStyleSheet(self.get_button_style("#4ec9b0"))
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setStyleSheet(self.get_button_style("#f44747"))
        button_layout.addWidget(self.stop_btn)
        
        self.photo_btn = QPushButton("📸 Photo")
        self.photo_btn.setStyleSheet(self.get_button_style("#569cd6"))
        button_layout.addWidget(self.photo_btn)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #333333;")
        button_layout.addWidget(separator)
        
        modes = [
            ("👤 Faces", VisionMode.FACES),
            ("📦 Objects", VisionMode.OBJECTS),
            ("📱 QR", VisionMode.QR),
            ("📝 Text", VisionMode.TEXT),
            ("⚡ Edge", VisionMode.EDGE),
            ("🔄 Normal", VisionMode.NORMAL),
        ]
        
        for label, mode in modes:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    color: #cccccc;
                    border: 2px solid transparent;
                    padding: 6px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                }
                QPushButton:checked {
                    border-color: #4ec9b0;
                    background-color: #2d4a3b;
                }
            """)
            btn.clicked.connect(lambda checked, m=mode: self.set_vision_mode(m))
            button_layout.addWidget(btn)
            setattr(self, f"mode_{mode.value}_btn", btn)
        
        button_layout.addStretch()
        bottom_layout.addLayout(button_layout)
        
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(100)
        self.info_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #d4d4d4;
                border: 1px solid #333333;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                font-size: 9pt;
            }
        """)
        info_layout.addWidget(self.info_text)
        
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setSpacing(2)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stats_labels = {}
        stats_items = [
            ("Faces", "faces", "0"),
            ("Objects", "objects", "0"),
            ("QR Codes", "qr_codes", "0"),
            ("Barcodes", "barcodes", "0"),
        ]
        
        for label, key, default in stats_items:
            item_label = QLabel(f"{label}: {default}")
            item_label.setStyleSheet("color: #888888; font-size: 9pt;")
            stats_layout.addWidget(item_label)
            self.stats_labels[key] = item_label
        
        info_layout.addWidget(stats_widget)
        bottom_layout.addWidget(info_widget)
        
        content_splitter.addWidget(bottom_widget)
        content_splitter.setSizes([500, 200])
        
        status_bar = QStatusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #252525;
                color: #888888;
                border-top: 1px solid #333333;
                padding: 2px 5px;
            }
        """)
        self.status_label = QLabel("Ready")
        status_bar.addWidget(self.status_label)
        status_bar.addPermanentWidget(QLabel("✨ Vision v1.0"))
        layout.addWidget(status_bar)
        
    def connect_signals(self):
        self.start_btn.clicked.connect(self.start_camera)
        self.stop_btn.clicked.connect(self.stop_camera)
        self.photo_btn.clicked.connect(self.take_photo)
        
        self.vision.result_ready.connect(self.update_info)
        self.vision.status_changed.connect(self.update_status)
        
    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Segoe UI', 'Consolas', monospace;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #cccccc;
                border: none;
                padding: 6px 14px;
                border-radius: 4px;
                font-size: 9pt;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #4d4d4d;
            }
            QSplitter::handle {
                background-color: #333333;
            }
            QSplitter::handle:hover {
                background-color: #4ec9b0;
            }
        """)
    
    def get_button_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {color};
                color: #1e1e1e;
                padding: 6px 14px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}cc;
            }}
        """
    
    def closeEvent(self, event):
        if hasattr(self, 'vision') and self.vision:
            self.vision.stop_camera()
            self.vision.running = False
            self.vision.quit()
            self.vision.wait()
        if hasattr(self, 'recording_active') and self.recording_active:
            self.stop_recording()
        if hasattr(self, 'advanced_tracker') and self.advanced_tracker:
            self.advanced_tracker.clear()
        if hasattr(self, 'face_tracker') and self.face_tracker:
            self.face_tracker.clear()
        self.save_settings()
        if hasattr(self, 'recording_timer'):
            self.recording_timer.stop()
        event.accept()
    
    @Slot(QImage)
    def update_frame(self, qimage: QImage):
        """Update the image display - optimized for UI responsiveness"""
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        
        if self.current_result:
            self.fps_label.setText(f"FPS: {self.current_result.fps:.1f}")
            self.update_performance_stats()
    
    @Slot(VisionResult)
    def update_info(self, result: VisionResult):
        self.current_result = result
        info_text = []
        if result.faces:
            info_text.append(f"👤 Faces: {len(result.faces)}")
        if result.objects:
            info_text.append(f"📦 Objects: {len(result.objects)}")
        if result.qr_codes:
            info_text.append(f"📱 QR Codes: {len(result.qr_codes)}")
        if result.barcodes:
            info_text.append(f"📊 Barcodes: {len(result.barcodes)}")
        if result.text_detected:
            info_text.append(f"📝 Text: {len(result.text_detected)}")
        if info_text:
            self.info_text.setText("\n".join(info_text))
        if not self.runtime_core:
            return

        if result.faces:
            safe_faces = [
                [int(x), int(y), int(w), int(h)]
                for x, y, w, h in result.faces
            ]

            self.runtime_core.dispatcher.publish(
                "vision.face.detected",
                {
                    "count": len(safe_faces),
                    "faces": safe_faces,
                    "fps": float(result.fps),
                },
                source="vision_panel",
            )

        if result.qr_codes:
            safe_codes = [str(code) for code in result.qr_codes]

            self.runtime_core.dispatcher.publish(
                "vision.qr.detected",
                {
                    "codes": safe_codes,
                    "count": len(safe_codes),
                },
                source="vision_panel",
            )


        if result.objects:
            safe_objects = []

            for obj in result.objects:

                # Tuple/List format
                if isinstance(obj, (tuple, list)) and len(obj) == 6:
                    label, confidence, x, y, w, h = obj

                    safe_objects.append({
                        "label": str(label),
                        "confidence": float(confidence),
                        "x": int(x),
                        "y": int(y),
                        "w": int(w),
                        "h": int(h),
                    })

                else:
                    # Fallback if it's already a dict or custom object
                    safe_objects.append(str(obj))

            self.runtime_core.dispatcher.publish(
                "vision.objects.detected",
                {
                    "count": len(safe_objects),
                    "objects": safe_objects,
                },
                source="vision_panel",
            )    
    
    @Slot(str)
    def update_status(self, status: str):
        self.status_label.setText(status)
        if "error" in status.lower():
            self.status_indicator.setText("● Error")
            self.status_indicator.setStyleSheet("color: #f44747; font-weight: bold;")
        elif "started" in status.lower() or "running" in status.lower():
            self.status_indicator.setText("● Running")
            self.status_indicator.setStyleSheet("color: #4ec9b0; font-weight: bold;")
        else:
            self.status_indicator.setText("● Ready")
            self.status_indicator.setStyleSheet("color: #4ec9b0; font-weight: bold;")
    
    @Slot()
    def start_camera(self):
        if self.vision is None:
            self.vision = VisionEngine()
            self.vision.frame_ready.connect(self.update_frame)
            self.vision.result_ready.connect(self.update_info)
            self.vision.status_changed.connect(self.update_status)

        self.vision.start_camera(0)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.publish_vision_status(
            "running",
            camera_id=0,
            mode=self.vision.mode.value,
        )

        if self.runtime_core:
            self.runtime_core.dispatcher.publish(
                "vision.camera.started",
                {
                    "camera_id": 0,
                    "mode": self.vision.mode.value,
                },
                source="vision_panel",
            )

        self.publish_face_state(
            "working",
            "Vision camera is active.",
        )
    
    @Slot()
    def stop_camera(self):
        if self.vision is not None:
            self.vision.stop_camera()
            self.vision.quit()
            self.vision.wait(2000)
            self.vision = None

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.image_label.clear()
        self.image_label.setText("Camera stopped")

        self.publish_vision_status("ready")

        if self.runtime_core:
            self.runtime_core.dispatcher.publish(
                "vision.camera.stopped",
                {},
                source="vision_panel",
            )

        self.publish_face_state(
            "idle",
            "Vision camera stopped.",
        )
    
    @Slot()
    def take_photo(self):
        if self.vision.running:
            import os
            screenshots_dir = self._get_screenshots_dir()
            self.vision.mutex.lock()
            if self.vision.camera and self.vision.camera.isOpened():
                ret, frame = self.vision.camera.read()
                if ret:
                    timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")
                    filename = f"vision_photo_{timestamp}.jpg"
                    full_path = os.path.join(screenshots_dir, filename)
                    cv2.imwrite(full_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                    self.status_label.setText(f"Photo saved: {full_path}")
                    self.info_text.append(f"📸 Photo: {full_path}")
            self.vision.mutex.unlock()
            if self.runtime_core:
                self.runtime_core.dispatcher.publish(
                    "vision.photo.saved",
                    {
                        "path": full_path,
                    },
                    source="vision_panel",
                )

                self.runtime_core.dispatcher.notify(
                    "Vision",
                    f"Photo saved: {filename}",
                    "success",
                )
    
    @Slot()
    def set_vision_mode(self, mode: VisionMode):
        self.vision.set_mode(mode)
        for mode_enum in VisionMode:
            btn = getattr(self, f"mode_{mode_enum.value}_btn", None)
            if btn:
                btn.setChecked(mode == mode_enum)
        self.publish_vision_status(
            "running",
            mode=mode.value,
        )

        if self.runtime_core:
            self.runtime_core.dispatcher.publish(
                "vision.mode.changed",
                {
                    "mode": mode.value,
                },
                source="vision_panel",
            )
      
    def add_tracking_controls(self):
        try:
            main_layout = self.layout()
            content_splitter = main_layout.itemAt(1).widget()
            bottom_widget = content_splitter.widget(1)
            bottom_layout = bottom_widget.layout()
            button_layout = bottom_layout.itemAt(0).layout()
            
            insert_index = button_layout.count() - 1
            
            self.track_btn = QPushButton("🎯 Advanced Tracking")
            self.track_btn.setStyleSheet(self.get_button_style("#dcdcaa"))
            self.track_btn.clicked.connect(self.toggle_advanced_tracking)
            button_layout.insertWidget(insert_index, self.track_btn)
            insert_index += 1
            
            self.record_btn = QPushButton("📹 Record")
            self.record_btn.setStyleSheet(self.get_button_style("#f44747"))
            self.record_btn.clicked.connect(self.toggle_recording)
            button_layout.insertWidget(insert_index, self.record_btn)
            insert_index += 1
            
            self.screenshot_btn = QPushButton("🖼️ Screenshot")
            self.screenshot_btn.setStyleSheet(self.get_button_style("#569cd6"))
            self.screenshot_btn.clicked.connect(self.capture_screenshot)
            button_layout.insertWidget(insert_index, self.screenshot_btn)
            
            self.open_recordings_btn = QPushButton("📁 Recordings")
            self.open_recordings_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    color: #4ec9b0;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 9pt;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                }
            """)
            self.open_recordings_btn.clicked.connect(self.open_recordings_folder)
            button_layout.insertWidget(insert_index, self.open_recordings_btn)
            insert_index += 1
        
            self.open_screenshots_btn = QPushButton("📸 Screenshots")
            self.open_screenshots_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    color: #dcdcaa;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 9pt;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                }
            """)
            self.open_screenshots_btn.clicked.connect(self.open_screenshots_folder)
            button_layout.insertWidget(insert_index, self.open_screenshots_btn)
            insert_index += 1
            
            self.tracking_status_label = QLabel("● Idle")
            self.tracking_status_label.setStyleSheet("color: #888888; font-weight: bold;")
            button_layout.addWidget(self.tracking_status_label)
            
            self.info_text.append("🎯 Advanced tracking controls added")
        except Exception as e:
            print(f"Error adding tracking controls: {e}")
    
    # ==================== Tracking Methods ====================
    
    @Slot()
    def start_advanced_tracking(self):
        """Start advanced object tracking"""
        if not self.vision.running:
            self.start_camera()
            QTimer.singleShot(500, self._init_advanced_tracker)
        else:
            self._init_advanced_tracker()
        
        self.tracking_active = True
        if self.vision:
            self.vision.tracking_active = True
            self.vision.face_tracker = self.face_tracker
            self.vision.advanced_tracker = self.advanced_tracker
        
        self.update_status("Advanced tracking started")
        self.info_text.append("🎯 Advanced object tracking activated")
        
        self.publish_vision_status(
            "tracking",
            tracking=True,
        )

        if self.runtime_core:
            self.runtime_core.dispatcher.publish(
                "vision.tracking.started",
                {},
                source="vision_panel",
            )
        
        if hasattr(self, 'tracking_status_label'):
            self.tracking_status_label.setText("● Advanced Tracking")
            self.tracking_status_label.setStyleSheet("color: #4ec9b0; font-weight: bold;")
        if hasattr(self, 'track_btn'):
            self.track_btn.setText("⏹ Stop Tracking")
        
        QTimer.singleShot(200, self._force_face_detection)
    
    def _init_advanced_tracker(self):
        # Prevent multiple initializations
        if self._tracker_initialized:
            return
        try:
            self.vision.mutex.lock()
            if self.vision.camera and self.vision.camera.isOpened():
                ret, frame = self.vision.camera.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.advanced_tracker = AdvancedTracker(tracker_type='auto', max_objects=10)
                    self.face_tracker = FaceTracker(max_faces=10)
                    
                    faces = self.face_tracker.detect_faces(frame_rgb)
                    if faces:
                        for (x, y, w, h, conf) in faces:
                            self.face_tracker.init_tracker(frame_rgb, (x, y, w, h), "Face", conf)
                        self.info_text.append(f"👤 Found {len(faces)} faces")
                    
                    if self.vision:
                        self.vision.face_tracker = self.face_tracker
                        self.vision.advanced_tracker = self.advanced_tracker
                    
                    self._tracker_initialized = True  # Mark as initialized
                    self.info_text.append("✅ Advanced trackers initialized")
            self.vision.mutex.unlock()
        except Exception as e:
            self.info_text.append(f"⚠️ Tracker init error: {str(e)}")
    
    def _force_face_detection(self):
        if hasattr(self, 'face_tracker') and self.face_tracker and self.vision.running:
            self.vision.mutex.lock()
            if self.vision.camera and self.vision.camera.isOpened():
                ret, frame = self.vision.camera.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    faces = self.face_tracker.detect_faces(frame_rgb)
                    for (x, y, w, h, conf) in faces:
                        self.face_tracker.init_tracker(frame_rgb, (x, y, w, h), "Face", conf)
                    if faces:
                        self.info_text.append(f"👤 Found {len(faces)} faces")
            self.vision.mutex.unlock()
    
    @Slot()
    def stop_advanced_tracking(self):
        """Stop advanced tracking"""  
        self.tracking_active = False
        self._tracker_initialized = False  # Reset flag
        
        if self.vision:
            self.vision.tracking_active = False
            self.vision.face_tracker = None
            self.vision.advanced_tracker = None
        if hasattr(self, 'advanced_tracker'):
            self.advanced_tracker.clear()
            self.advanced_tracker = None
        if hasattr(self, 'face_tracker'):
            self.face_tracker.clear()
            self.face_tracker = None
            
        self.publish_vision_status(
            "running",
            tracking=False,
        )

        if self.runtime_core:
            self.runtime_core.dispatcher.publish(
                "vision.tracking.stopped",
                {},
                source="vision_panel",
            )    
        
        self.update_status("Advanced tracking stopped")
        self.info_text.append("⏹ Advanced tracking stopped")
        
        if hasattr(self, 'tracking_status_label'):
            self.tracking_status_label.setText("● Idle")
            self.tracking_status_label.setStyleSheet("color: #888888; font-weight: bold;")
        if hasattr(self, 'track_btn'):
            self.track_btn.setText("🎯 Start Tracking")
    
    @Slot()
    def toggle_advanced_tracking(self):
        if hasattr(self, 'tracking_active') and self.tracking_active:
            self.stop_advanced_tracking()
        else:
            self.start_advanced_tracking()
    
    # ==================== Recording Methods ====================
    
    @Slot()
    def start_recording(self):
        if not self.vision.running:
            self.start_camera()
        import os
        recordings_dir = self._get_recordings_dir()
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")
        filename = f"vision_recording_{timestamp}.avi"
        self.recording_filename = os.path.join(recordings_dir, filename)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.video_writer = cv2.VideoWriter(self.recording_filename, fourcc, 30.0, (640, 480))
        self.recording_active = True
        if hasattr(self, 'record_btn'):
            self.record_btn.setText("⏹ Stop Recording")
        self.update_status(f"Recording: {self.recording_filename}")
        self.info_text.append(f"🎥 Recording started: {self.recording_filename}")
    
    @Slot()
    def stop_recording(self):
        self.recording_active = False
        if hasattr(self, 'video_writer') and self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        if hasattr(self, 'record_btn'):
            self.record_btn.setText("📹 Record")
        self.update_status(f"Recording saved: {self.recording_filename}")
        self.info_text.append(f"💾 Recording saved: {self.recording_filename}")
    
    @Slot()
    def toggle_recording(self):
        if hasattr(self, 'recording_active') and self.recording_active:
            self.stop_recording()
        else:
            self.start_recording()
    
    @Slot()
    def capture_screenshot(self):
        if self.vision.running and self.current_result:
            import os
            screenshots_dir = self._get_screenshots_dir()
            timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")
            filename = f"vision_screenshot_{timestamp}.png"
            full_path = os.path.join(screenshots_dir, filename)
            self.vision.mutex.lock()
            if self.vision.camera and self.vision.camera.isOpened():
                ret, frame = self.vision.camera.read()
                if ret:
                    cv2.imwrite(full_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                    self.update_status(f"Screenshot saved: {full_path}")
                    self.info_text.append(f"📸 Screenshot: {full_path}")
            self.vision.mutex.unlock()
    
    @Slot()
    def open_recordings_folder(self):
        import os
        import subprocess
        folder = self._get_recordings_dir()
        if os.name == 'nt':
            subprocess.Popen(f'explorer "{folder}"')
        else:
            subprocess.Popen(f'open "{folder}"' if os.name == 'darwin' else f'xdg-open "{folder}"', shell=True)
    
    @Slot()
    def open_screenshots_folder(self):
        import os
        import subprocess
        folder = self._get_screenshots_dir()
        if os.name == 'nt':
            subprocess.Popen(f'explorer "{folder}"')
        else:
            subprocess.Popen(f'open "{folder}"' if os.name == 'darwin' else f'xdg-open "{folder}"', shell=True)
    
    # ==================== Helper Methods ====================
    
    def detect_motion(self, frame: np.ndarray) -> bool:
        if not hasattr(self, 'motion_detection_active') or not self.motion_detection_active:
            return False
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        if self.prev_frame is None:
            self.prev_frame = gray
            return False
        diff = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) > self.motion_threshold:
                motion_detected = True
                (x, y, w, h) = cv2.boundingRect(contour)
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(frame, "Motion!", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        self.prev_frame = gray
        return motion_detected
    
    def update_performance_stats(self):
        if hasattr(self.vision, 'fps'):
            fps = self.vision.fps
            self.fps_label.setText(f"FPS: {fps:.1f}")
            if fps > 25:
                self.fps_label.setStyleSheet("color: #4ec9b0; font-weight: bold;")
            elif fps > 15:
                self.fps_label.setStyleSheet("color: #dcdcaa; font-weight: bold;")
            else:
                self.fps_label.setStyleSheet("color: #f44747; font-weight: bold;")
    
    def _detect_new_objects(self, frame):
        detected_objects = []
        if hasattr(self, 'face_tracker') and self.face_tracker:
            faces = self.face_tracker.detect_faces(frame)
            for (x, y, w, h, conf) in faces:
                detected_objects.append({
                    'bbox': (x, y, w, h),
                    'label': 'Face',
                    'confidence': conf,
                    'type': 'face'
                })
        return detected_objects
    
    def _iou(self, bbox1, bbox2):
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        intersection = (x_right - x_left) * (y_bottom - y_top)
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        return intersection / union if union > 0 else 0
    
    def _get_recordings_dir(self):
        import os
        recordings_dir = r"C:\Users\xkali\new_ai\buster-v10\recordings"
        if not os.path.exists(recordings_dir):
            os.makedirs(recordings_dir)
        return recordings_dir
    
    def _get_screenshots_dir(self):
        import os
        screenshots_dir = r"C:\Users\xkali\new_ai\buster-v10\screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        return screenshots_dir
    
    def save_settings(self):
        settings = {
            'motion_threshold': self.motion_threshold if hasattr(self, 'motion_threshold') else 5000,
        }
        try:
            with open("vision_settings.json", 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
            
    def publish_vision_status(self, status: str, **extra):
        if not self.runtime_core:
            return

        self.runtime_core.dispatcher.publish(
            "vision.status",
            {
                "status": status,
                **extra,
            },
            source="vision_panel",
        )


    def publish_face_state(self, state: str, message: str):
        if not self.runtime_core:
            return

        self.runtime_core.dispatcher.face(
            state,
            message,
        )        