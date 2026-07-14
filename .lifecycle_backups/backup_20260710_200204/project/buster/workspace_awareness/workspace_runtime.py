from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json

from buster.sdk import BusterSDK
from buster.agent_os import LivingCompanionRuntime

from .app_detector import AppDetector
from .device_watcher import DeviceWatcher
from .git_watcher import GitWatcher
from .project_context import ProjectContextDetector
from .workspace_events import WorkspaceEvent


class WorkspaceAwarenessRuntime:
    def __init__(self, sdk: BusterSDK | None = None, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.sdk = sdk or BusterSDK(data_dir=data_dir)
        self.companion = LivingCompanionRuntime(self.sdk, data_dir=data_dir)

        self.app_detector = AppDetector()
        self.project_detector = ProjectContextDetector()
        self.git_watcher = GitWatcher()
        self.device_watcher = DeviceWatcher()

        self.events: List[Dict[str, Any]] = []
        self.running = False
        self.state_file = self.data_dir / "workspace_awareness_state.json"
        self.events_file = self.data_dir / "workspace_awareness_events.json"

    def start(self) -> Dict[str, Any]:
        self.running = True
        self.companion.start()
        self.sdk.publish("workspace_awareness.started", {"running": True}, source="workspace_awareness")
        self._persist()
        return self.status()

    def stop(self) -> Dict[str, Any]:
        self.running = False
        self.sdk.publish("workspace_awareness.stopped", {"running": False}, source="workspace_awareness")
        self._persist()
        return self.status()

    def scan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        detected: List[WorkspaceEvent] = []
        detected.extend(self.app_detector.detect(context))
        detected.extend(self.project_detector.detect(context))
        detected.extend(self.git_watcher.detect(context))
        detected.extend(self.device_watcher.detect(context))

        for event in detected:
            self.record_event(event)

        self._react(detected)
        self._persist()
        return {
            "running": self.running,
            "events": [e.to_dict() for e in detected],
            "total_events": len(self.events),
            "companion_messages": self.companion.status()["messages"],
        }

    def record_event(self, event: WorkspaceEvent) -> Dict[str, Any]:
        item = event.to_dict()
        self.events.append(item)
        self.sdk.publish(
            f"workspace.{event.type}",
            item,
            source="workspace_awareness",
            priority="high" if event.importance >= 0.8 else "normal",
        )
        return item

    def _react(self, events: List[WorkspaceEvent]) -> None:
        for event in events:
            app = event.data.get("app")
            if event.type == "app.active" and app:
                self.companion.notice_app(app)

            if event.type == "project.context":
                contexts = ", ".join(event.data.get("contexts", []))
                self.companion.say(
                    f"I detected the project context: {contexts}. I'll prepare the right development tools.",
                    reason="project_context",
                )

            if event.type == "git.changed":
                self.companion.say(
                    event.summary + ". I can index the changes and prepare a checkpoint when tests pass.",
                    reason="git_awareness",
                )

            if event.type.startswith("hardware."):
                self.companion.say(event.summary + ". I'll make the matching plugin context available.", reason="device_awareness")

    def status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "events": self.events[-20:],
            "event_count": len(self.events),
            "companion": self.companion.status(),
        }

    def _persist(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.status(), indent=2), encoding="utf-8")
        self.events_file.write_text(json.dumps(self.events, indent=2), encoding="utf-8")
