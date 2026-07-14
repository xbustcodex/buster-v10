from dataclasses import dataclass
from pathlib import Path

@dataclass
class VisionSettings:
    camera_index: int = 0
    width: int = 640
    height: int = 480
    fps_limit: int = 20
    snapshots_dir: Path = Path("screenshots/vision")
    enable_faces: bool = True
    enable_objects: bool = True
    enable_qr: bool = True
    enable_ocr: bool = False
    enable_yolo: bool = True
    yolo_model_path: Path = Path("models/yolov8n.pt")
    yolo_confidence: float = 0.35
    yolo_device: str = "cpu"
    yolo_every_n_frames: int = 6
