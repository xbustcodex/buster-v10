from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Any, List

@dataclass
class VisualObservation:
    source: str = "camera"
    objects: List[str] = None
    scene: str = "unknown"
    confidence: float = 0.0
    importance: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["objects"] = data["objects"] or []
        if not data["timestamp"]:
            data["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return data

class EyeSystem:
    def observe(self, objects=None, scene="workspace", confidence=0.5, source="camera"):
        objects = objects or []
        importance = self.score_importance(objects, scene, confidence)
        return VisualObservation(source=source, objects=objects, scene=scene, confidence=confidence, importance=importance).to_dict()

    def score_importance(self, objects, scene, confidence):
        important = {"person", "phone", "esp32", "arduino", "laptop", "error", "screen"}
        score = confidence * 0.4
        score += min(0.4, len(set(o.lower() for o in objects) & important) * 0.15)
        if scene in {"development", "workspace", "hardware"}:
            score += 0.1
        return max(0.0, min(1.0, score))
