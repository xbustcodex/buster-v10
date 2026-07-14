from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .workspace_events import WorkspaceEvent


class DeviceWatcher:
    KEYWORDS = {
        "esp32": ("ESP32 device detected", "hardware.esp32"),
        "arduino": ("Arduino device detected", "hardware.arduino"),
        "pixel": ("Pixel phone detected", "hardware.android"),
        "android": ("Android device detected", "hardware.android"),
        "adb": ("ADB device detected", "hardware.android"),
    }

    def detect_from_names(self, device_names: Iterable[str]) -> List[WorkspaceEvent]:
        events: List[WorkspaceEvent] = []
        seen = set()

        for raw in device_names:
            text = str(raw)
            lower = text.lower()
            for key, (summary, event_type) in self.KEYWORDS.items():
                if key in lower and event_type not in seen:
                    seen.add(event_type)
                    events.append(
                        WorkspaceEvent(
                            type=event_type,
                            summary=summary,
                            confidence=0.85,
                            importance=0.85,
                            data={"device": text},
                        )
                    )
        return events

    def detect(self, context: Dict[str, Any]) -> List[WorkspaceEvent]:
        devices = context.get("devices") or context.get("usb") or []
        return self.detect_from_names(devices)
