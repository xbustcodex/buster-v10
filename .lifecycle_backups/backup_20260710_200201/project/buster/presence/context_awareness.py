from __future__ import annotations
from typing import Dict, Any

class ContextAwareness:
    def describe_context(self, active_window: str = "", device_hint: str = "", idle_minutes: int = 0) -> Dict[str, Any]:
        window = (active_window or "").lower(); device = (device_hint or "").lower(); suggestions = []
        if "android studio" in window: suggestions.append("I can monitor Logcat while you work in Android Studio.")
        if "visual studio code" in window or "vscode" in window: suggestions.append("I can watch your project files and suggest a re-index when they change.")
        if "esp32" in device or "cp210" in device or "ch340" in device: suggestions.append("ESP32-style device detected. Arduino and ESP32 plugins may help.")
        if idle_minutes >= 20: suggestions.append(f"Your workspace has been idle for about {idle_minutes} minutes.")
        return {"active_window": active_window, "device_hint": device_hint, "idle_minutes": idle_minutes, "suggestions": suggestions}
