from __future__ import annotations

import platform
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class VisualObservation:
    source: str = "camera"
    objects: List[str] = field(default_factory=list)
    scene: str = "unknown"
    confidence: float = 0.0
    importance: float = 0.0
    timestamp: str = ""
    hardware: Dict[str, Any] = field(default_factory=dict)
    runtime: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["objects"] = data["objects"] or []
        if not data["timestamp"]:
            data["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return data


class EyeSystem:
    """Hardware & Kernel Aware Visual Perception Subsystem."""

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
        objects: Optional[List[str]] = None,
        scene: str = "workspace",
        confidence: float = 0.5,
        source: str = "camera",
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        objects = objects or []
        importance = self.score_importance(objects, scene, confidence)

        runtime_data = dict(self.runtime_profile)
        if runtime_context:
            runtime_data.update(runtime_context)

        return VisualObservation(
            source=source,
            objects=objects,
            scene=scene,
            confidence=confidence,
            importance=importance,
            hardware=self.hardware_profile,
            runtime=runtime_data,
        ).to_dict()

    def score_importance(self, objects: List[str], scene: str, confidence: float) -> float:
        important = {"person", "phone", "esp32", "arduino", "laptop", "error", "screen", "terminal", "pixel"}
        score = confidence * 0.4
        score += min(0.4, len(set(o.lower() for o in objects) & important) * 0.15)
        if scene in {"development", "workspace", "hardware", "terminal_execution"}:
            score += 0.1
        return max(0.0, min(1.0, score))