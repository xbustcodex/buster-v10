#!/usr/bin/env python3
"""
vision_panel.py - Buster Vision Panel with PySide6
A comprehensive vision processing panel with camera control, face detection, QR scanning, and more.
"""

import sys
import cv2
import numpy as np
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum

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

class VisionMode(Enum):
    """Vision processing modes"""
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
        
        # Performance tracking
        self.frame_count = 0
        self.fps_timer = QElapsedTimer()
        self.fps = 0.0
        
        # Initialize detectors
        self._init_detectors()
        
    def _init_detectors(self):
        """Initialize computer vision detectors"""
        try:
            # Face detection
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(face_cascade_path)
            
            # QR code detector
            self.qr_detector = cv2.QRCodeDetector()
            
            # Initialize object detector (using pre-trained MobileNet SSD)
            self.object_detector = None  # Would load model here
            self.status_changed.emit("Vision engine initialized")
            
        except Exception as e:
            self.status_changed.emit(f"Error initializing detectors: {str(e)}")
    
    def start_camera(self, camera_id: int = 0):
        """Start the camera"""
        self.mutex.lock()
        try:
            if self.camera is not None:
                self.camera.release()
            
            self.camera = cv2.VideoCapture(camera_id)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            self.running = True
            self.fps_timer.start()
            self.frame_count = 0
            
            if not self.isRunning():
                self.start()
                
            self.status_changed.emit(f"Camera {camera_id} started")
            
        except Exception as e:
            self.status_changed.emit(f"Error starting camera: {str(e)}")
        finally:
            self.mutex.unlock()
    
    def stop_camera(self):
        """Stop the camera"""
        self.mutex.lock()
        self.running = False
        if self.camera:
            self.camera.release()
            self.camera = None
        self.mutex.unlock()
        self.status_changed.emit("Camera stopped")
    
    def set_mode(self, mode: VisionMode):
        """Set vision processing mode"""
        self.mode = mode
        self.status_changed.emit(f"Mode: {mode.value}")
    
    def run(self):
        """Main processing loop"""
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
            qimage = QImage(processed_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            
            # Emit signals
            self.frame_ready.emit(qimage)
            self.result_ready.emit(result)
            
            self.msleep(10)  # Control frame rate
    
    def _process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, VisionResult]:
        """Process a single frame based on current mode"""
        result = VisionResult()
        processed = frame.copy()
        
        # Convert to RGB for display
        processed = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
        
        # Apply different processing modes
        if self.mode == VisionMode.FACES:
            processed, result.faces = self._detect_faces(processed)
        elif self.mode == VisionMode.QR:
            processed, result.qr_codes = self._scan_qr(processed)
        elif self.mode == VisionMode.EDGE:
            processed = self._detect_edges(processed)
        elif self.mode == VisionMode.TEXT:
            processed, result.text_detected = self._detect_text(processed)
        elif self.mode == VisionMode.NORMAL:
            # Just pass through
            pass
        
        return processed, result
    
    def _detect_faces(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Tuple[int, int, int, int]]]:
        """Detect faces in the frame"""
        if self.face_cascade is None:
            return frame, []
        
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"Face", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame, [(x, y, w, h) for (x, y, w, h) in faces]
    
    def _scan_qr(self, frame: np.ndarray) -> Tuple[np.ndarray, List[str]]:
        """Scan for QR codes and barcodes"""
        qr_codes = []
        try:
            # QR Code detection
            data, bbox, _ = self.qr_detector.detectAndDecode(frame)
            if data:
                qr_codes.append(data)
                if bbox is not None:
                    bbox = bbox.astype(int)
                    cv2.polylines(frame, [bbox], True, (0, 255, 0), 2)
                    cv2.putText(frame, f"QR: {data}", (bbox[0][0][0], bbox[0][0][1]-10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Barcode detection (using pyzbar if available)
            try:
                from pyzbar.pyzbar import decode
                decoded = decode(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY))
                for obj in decoded:
                    barcode_data = obj.data.decode('utf-8')
                    qr_codes.append(f"Barcode: {barcode_data}")
                    points = obj.polygon
                    if len(points) == 4:
                        pts = [(p.x, p.y) for p in points]
                        cv2.polylines(frame, [np.array(pts, dtype=int)], True, (0, 255, 0), 2)
            except ImportError:
                pass  # pyzbar not installed
                
        except Exception as e:
            pass
        
        return frame, qr_codes
    
    def _detect_edges(self, frame: np.ndarray) -> np.ndarray:
        """Detect edges using Canny"""
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
    
    def _detect_text(self, frame: np.ndarray) -> Tuple[np.ndarray, List[str]]:
        """Detect text in the frame (placeholder)"""
        # This would use Tesseract or similar
        return frame, ["Text detection placeholder"]

# ==================== Vision Panel Widget ====================

class VisionPanel(QWidget):
    """Main vision panel widget"""
    
    def __init__(self, live=None, parent=None):
        super().__init__(parent)
        self.live = live

        self.vision = VisionEngine()
        self.current_result = VisionResult()

        self.setup_ui()
        self.connect_signals()
        self.apply_dark_theme()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ===== Header =====
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("👁️ Buster Vision")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Status indicator
        self.status_indicator = QLabel("● Ready")
        self.status_indicator.setStyleSheet("color: #4ec9b0; font-weight: bold;")
        header_layout.addWidget(self.status_indicator)
        
        # FPS display
        self.fps_label = QLabel("FPS: 0.0")
        self.fps_label.setStyleSheet("color: #569cd6; font-weight: bold;")
        header_layout.addWidget(self.fps_label)
        
        layout.addWidget(header_widget)
        
        # ===== Main Content =====
        content_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(content_splitter, 1)
        
        # Image display
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
        
        # Bottom section with controls and info
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setSpacing(8)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        # Camera controls
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
        
        # Mode buttons
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
        
        # Info display
        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        # Info text
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
        
        # Stats panel
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
        
        # Status bar
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
        """Connect signals to slots"""
        self.start_btn.clicked.connect(self.start_camera)
        self.stop_btn.clicked.connect(self.stop_camera)
        self.photo_btn.clicked.connect(self.take_photo)
        
        self.vision.frame_ready.connect(self.update_frame)
        self.vision.result_ready.connect(self.update_info)
        self.vision.status_changed.connect(self.update_status)
        
    def apply_dark_theme(self):
        """Apply dark theme to the widget"""
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
        """Get style for colored buttons"""
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
    
    @Slot(QImage)
    def update_frame(self, qimage: QImage):
        """Update the image display"""
        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        
        # Update FPS
        if self.current_result:
            self.fps_label.setText(f"FPS: {self.current_result.fps:.1f}")
    
    @Slot(VisionResult)
    def update_info(self, result: VisionResult):
        """Update the info display"""
        self.current_result = result
        
        # Update text info
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
        
        # Update stats
        self.stats_labels["faces"].setText(f"Faces: {len(result.faces)}")
        self.stats_labels["objects"].setText(f"Objects: {len(result.objects)}")
        self.stats_labels["qr_codes"].setText(f"QR Codes: {len(result.qr_codes)}")
        self.stats_labels["barcodes"].setText(f"Barcodes: {len(result.barcodes)}")
    
    @Slot(str)
    def update_status(self, status: str):
        """Update status display"""
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
        """Start the camera"""
        self.vision.start_camera(0)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    @Slot()
    def stop_camera(self):
        """Stop the camera"""
        self.vision.stop_camera()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.image_label.setText("Camera stopped")
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 2px solid #333333;
                border-radius: 8px;
                color: #666666;
            }
        """)
    
    @Slot()
    def take_photo(self):
        """Take a photo"""
        if self.vision.running:
            # Get current frame and save it
            self.vision.mutex.lock()
            if self.vision.camera and self.vision.camera.isOpened():
                ret, frame = self.vision.camera.read()
                if ret:
                    timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd_hh-mm-ss")
                    filename = f"vision_{timestamp}.jpg"
                    cv2.imwrite(filename, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                    self.status_label.setText(f"Photo saved: {filename}")
            self.vision.mutex.unlock()
    
    @Slot()
    def set_vision_mode(self, mode: VisionMode):
        """Set the vision processing mode"""
        self.vision.set_mode(mode)
        
        # Update button states
        for mode_enum in VisionMode:
            btn = getattr(self, f"mode_{mode_enum.value}_btn", None)
            if btn:
                btn.setChecked(mode == mode_enum)


