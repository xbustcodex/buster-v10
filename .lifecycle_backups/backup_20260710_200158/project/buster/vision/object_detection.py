from pathlib import Path
from buster.vision.types import Detection

class ObjectDetector:
    def __init__(self, settings=None):
        self.settings = settings
        self.ready = False
        self.backend = "motion_fallback"
        self.model = None
        self.names = {}
        self.background = None
        self.frame_count = 0
        self.last_detections = []
        self.confidence = getattr(settings, "yolo_confidence", 0.35) if settings else 0.35
        self.device = getattr(settings, "yolo_device", "cpu") if settings else "cpu"
        self.every_n = max(1, int(getattr(settings, "yolo_every_n_frames", 6) if settings else 6))
        if settings and getattr(settings, "enable_yolo", True):
            self._load_yolo()

    def _load_yolo(self):
        try:
            from ultralytics import YOLO
            model_path = Path(getattr(self.settings, "yolo_model_path", "models/yolov8n.pt"))
            model_path.parent.mkdir(parents=True, exist_ok=True)
            source = str(model_path) if model_path.exists() else "yolov8n.pt"
            self.model = YOLO(source)
            self.names = self.model.names
            self.ready = True
            self.backend = "yolo"
        except Exception as exc:
            self.ready = False
            self.backend = f"motion_fallback ({exc})"

    def process(self, frame):
        if frame is None:
            return []
        self.frame_count += 1
        if self.ready and self.model:
            if self.frame_count % self.every_n == 0 or not self.last_detections:
                self.last_detections = self._process_yolo(frame)
            return self.last_detections
        return self._process_motion(frame)

    def _process_yolo(self, frame):
        try:
            results = self.model.predict(source=frame, conf=self.confidence, device=self.device, verbose=False)
            if not results:
                return []
            detections = []
            boxes = results[0].boxes
            if boxes is None:
                return []
            for box in boxes:
                xyxy = box.xyxy[0].tolist()
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                x1, y1, x2, y2 = [int(v) for v in xyxy]
                label = self.names.get(cls_id, str(cls_id)) if isinstance(self.names, dict) else str(cls_id)
                detections.append(Detection("object", label, (x1, y1, max(0, x2-x1), max(0, y2-y1)), conf))
            return detections[:20]
        except Exception:
            return []

    def _process_motion(self, frame):
        try:
            import cv2
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            if self.background is None:
                self.background = gray
                return []
            diff = cv2.absdiff(self.background, gray)
            thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            detections = []
            for c in contours:
                area = cv2.contourArea(c)
                if area < 2500:
                    continue
                x, y, w, h = cv2.boundingRect(c)
                detections.append(Detection("object", "Motion/Object", (int(x), int(y), int(w), int(h)), min(1.0, area/20000.0)))
            return detections[:8]
        except Exception:
            return []

    def status(self):
        return f"YOLO ready ({self.device}, conf {self.confidence})" if self.ready else f"YOLO unavailable, using {self.backend}"
