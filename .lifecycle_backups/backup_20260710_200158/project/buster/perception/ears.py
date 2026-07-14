from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Any

@dataclass
class AudioObservation:
    source: str = "microphone"
    sound_type: str = "unknown"
    confidence: float = 0.0
    text: str = ""
    speaker: str = "unknown"
    importance: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if not data["timestamp"]:
            data["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return data

class EarSystem:
    def observe(self, sound_type="speech", text="", speaker="unknown", confidence=0.5, importance=None):
        if importance is None:
            importance = self.score_importance(sound_type, text, confidence)
        return AudioObservation(sound_type=sound_type, text=text, speaker=speaker, confidence=confidence, importance=importance).to_dict()

    def score_importance(self, sound_type: str, text: str, confidence: float) -> float:
        score = confidence * 0.5
        lowered = (text or "").lower()
        if "buster" in lowered:
            score += 0.4
        if sound_type in {"alarm", "error", "device_connected"}:
            score += 0.3
        if sound_type == "speech":
            score += 0.1
        return max(0.0, min(1.0, score))
