from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .workspace_events import WorkspaceEvent


class ProjectContextDetector:
    MARKERS = {
        "settings.gradle": "Android/Gradle project",
        "build.gradle": "Gradle project",
        "pyproject.toml": "Python project",
        "requirements.txt": "Python project",
        "platformio.ini": "PlatformIO/ESP32 project",
        "arduino.json": "Arduino project",
        "package.json": "Node/JavaScript project",
    }

    def detect_path(self, path: str | Path) -> List[WorkspaceEvent]:
        root = Path(path)
        events: List[WorkspaceEvent] = []
        if not root.exists():
            return events

        detected = []
        for marker, label in self.MARKERS.items():
            if (root / marker).exists():
                detected.append(label)

        if detected:
            summary = f"Project context detected: {', '.join(sorted(set(detected)))}"
            events.append(
                WorkspaceEvent(
                    type="project.context",
                    summary=summary,
                    confidence=0.9,
                    importance=0.8,
                    data={"path": str(root), "contexts": sorted(set(detected))},
                )
            )
        return events

    def detect(self, context: Dict[str, Any]) -> List[WorkspaceEvent]:
        path = context.get("project_path") or context.get("cwd")
        if not path:
            return []
        return self.detect_path(path)
