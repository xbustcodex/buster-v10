from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .workspace_events import WorkspaceEvent


class AppDetector:
    KNOWN_APPS = {
        "android studio": "Android Studio",
        "code": "VS Code",
        "visual studio code": "VS Code",
        "cmd": "Terminal",
        "powershell": "Terminal",
        "windows terminal": "Terminal",
        "arduino": "Arduino IDE",
        "chrome": "Browser",
        "edge": "Browser",
    }

    def detect_from_names(self, process_or_window_names: Iterable[str]) -> List[WorkspaceEvent]:
        events: List[WorkspaceEvent] = []
        seen = set()

        for raw in process_or_window_names:
            name = str(raw)
            lower = name.lower()
            for key, label in self.KNOWN_APPS.items():
                if key in lower and label not in seen:
                    seen.add(label)
                    events.append(
                        WorkspaceEvent(
                            type="app.active",
                            summary=f"{label} is active",
                            confidence=0.85,
                            importance=0.75 if label in {"Android Studio", "VS Code", "Arduino IDE"} else 0.5,
                            data={"app": label, "raw": name},
                        )
                    )
        return events

    def detect(self, context: Dict[str, Any]) -> List[WorkspaceEvent]:
        names = context.get("apps") or context.get("windows") or context.get("processes") or []
        return self.detect_from_names(names)
