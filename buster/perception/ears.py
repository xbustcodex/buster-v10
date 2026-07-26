from __future__ import annotations

import platform
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class AudioObservation:
    source: str = "microphone"
    sound_type: str = "unknown"
    confidence: float = 0.0
    text: str = ""
    speaker: str = "unknown"
    importance: float = 0.0
    timestamp: str = ""
    hardware: Dict[str, Any] = field(default_factory=dict)
    runtime: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if not data["timestamp"]:
            data["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return data


class EarSystem:
    """Hardware & Kernel Aware Audio Perception Subsystem."""

    def __init__(self) -> None:
        self.hardware_profile = {
            "processor": platform.processor() or platform.machine(),
            "platform": platform.platform(),
            "kernel": platform.release(),
            "system": platform.system(),
        }
        self.runtime_profile = {
            "python_version": sys.version.split()[0],
            "executable": sys.executable,
        }

    def observe(
        self,
        sound_type: str = "speech",
        text: str = "",
        speaker: str = "unknown",
        confidence: float = 0.5,
        importance: Optional[float] = None,
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if importance is None:
            importance = self.score_importance(sound_type, text, confidence)

        runtime_data = dict(self.runtime_profile)
        if runtime_context:
            runtime_data.update(runtime_context)

        return AudioObservation(
            sound_type=sound_type,
            text=text,
            speaker=speaker,
            confidence=confidence,
            importance=importance,
            hardware=self.hardware_profile,
            runtime=runtime_data,
        ).to_dict()

    def score_importance(self, sound_type: str, text: str, confidence: float) -> float:
        score = confidence * 0.5
        lowered = (text or "").lower()

        if "buster" in lowered:
            score += 0.4
        if sound_type in {"alarm", "error", "device_connected", "hardware_interrupt"}:
            score += 0.3
        if sound_type == "speech":
            score += 0.1
        if any(k in lowered for k in ["kernel", "panic", "crash", "traceback", "cpu"]):
            score += 0.2

        return max(0.0, min(1.0, score))