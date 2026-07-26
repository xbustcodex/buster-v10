from __future__ import annotations

import platform
import sys
from typing import Any, Dict, Optional
from buster.world_model import WorldModelEngine


class PerceptionEngine:
    """Perception Engine with Hardware, Kernel & Runtime Awareness."""

    def __init__(self, data_dir: str = "data") -> None:
        self.world = WorldModelEngine(data_dir=data_dir)
        self.hardware_context = {
            "processor": platform.processor() or platform.machine(),
            "platform": platform.platform(),
            "kernel": platform.release(),
            "python_version": sys.version.split()[0],
        }

    def perceive_text(
        self,
        source: str,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
    ) -> Dict[str, Any]:
        ctx = context or {}
        ctx.setdefault("hardware", self.hardware_context)
        obs = self.world.observe(source=source, summary=text, context=ctx, importance=importance)
        understanding = self.world.understand_now()
        return {"observation": obs, "understanding": understanding}

    def perceive_camera_observation(
        self,
        description: str,
        objects: Optional[list] = None,
        scene: Optional[str] = None,
        confidence: float = 0.75,
    ) -> Dict[str, Any]:
        context = {
            "objects": objects or [],
            "scene": scene or "unknown",
            "hardware": self.hardware_context,
        }
        return self.world.observe("camera", description, context=context, importance=0.7, confidence=confidence)

    def perceive_desktop_observation(self, active_app: str, detail: str = "") -> Dict[str, Any]:
        summary = f"Desktop active app: {active_app}. {detail}".strip()
        context = {
            "active_app": active_app,
            "hardware": self.hardware_context,
        }
        return self.world.observe("desktop", summary, context=context, importance=0.6)