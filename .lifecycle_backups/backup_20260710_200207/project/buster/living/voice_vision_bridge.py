from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .state import LivingMood


@dataclass
class VoiceVisionBridge:
    """
    Normalizes voice and vision signals for Mission Control.

    It does not own microphone or camera hardware.
    Existing voice/vision modules can pass summaries into this bridge.
    """

    voice_enabled: bool = False
    vision_enabled: bool = False

    def voice_signal(self, text: str = "", listening: bool = True) -> Dict[str, Any]:
        return {
            "channel": "voice",
            "listening": listening,
            "heard": text,
            "mood": LivingMood.LISTENING if listening else LivingMood.STANDBY,
        }

    def vision_signal(self, summary: str = "", watching: bool = True) -> Dict[str, Any]:
        return {
            "channel": "vision",
            "watching": watching,
            "seen": summary,
            "mood": LivingMood.WATCHING if watching else LivingMood.STANDBY,
        }

    def combine(self, voice: Dict[str, Any] | None = None, vision: Dict[str, Any] | None = None) -> Dict[str, Any]:
        voice = voice or {}
        vision = vision or {}
        return {
            "voice": voice,
            "vision": vision,
            "listening": bool(voice.get("listening", False)),
            "watching": bool(vision.get("watching", False)),
            "mood": vision.get("mood") or voice.get("mood") or LivingMood.STANDBY,
        }
