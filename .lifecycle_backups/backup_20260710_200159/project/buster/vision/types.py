from dataclasses import dataclass
from typing import Tuple

@dataclass
class Detection:
    kind: str
    label: str
    box: Tuple[int, int, int, int]
    confidence: float = 1.0

@dataclass
class VisionResult:
    faces: list
    objects: list
    qr_codes: list
    text: str
    fps: float
    frame_width: int
    frame_height: int
