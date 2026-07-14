from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from buster.sdk import BusterSDK
from .agent_runtime import AgentRuntime


class LivingCompanionRuntime:
    def __init__(self, sdk: BusterSDK | None = None, data_dir: str | Path = "data") -> None:
        self.sdk = sdk or BusterSDK(data_dir=data_dir)
        self.agent_runtime = AgentRuntime(self.sdk, data_dir=data_dir)
        self.mode = "companion"
        self.messages: List[Dict[str, Any]] = []
        self.running = False

    def start(self) -> Dict[str, Any]:
        self.running = True
        self.agent_runtime.start()
        self.say("Good morning Adam.", reason="startup")
        self.sdk.publish("companion.living.started", {"mode": self.mode}, source="living_companion")
        return self.status()

    def stop(self) -> Dict[str, Any]:
        self.running = False
        self.agent_runtime.stop()
        self.sdk.publish("companion.living.stopped", {}, source="living_companion")
        return self.status()

    def say(self, message: str, reason: str = "companion") -> Dict[str, Any]:
        event = self.sdk.speak(message, reason=reason)
        item = {
            "timestamp": event.timestamp,
            "message": message,
            "reason": reason,
        }
        self.messages.append(item)
        return item

    def notice_app(self, app_name: str) -> Dict[str, Any]:
        self.sdk.observe(f"{app_name} is open", source="living_companion", app=app_name)
        if app_name.lower() == "android studio":
            return self.say(
                "I noticed Android Studio is open. Loading the Android development context.",
                reason="workspace_awareness",
            )
        return self.say(f"I noticed {app_name} is open.", reason="workspace_awareness")

    def notice_project(self, project: str, kind: str = "project") -> Dict[str, Any]:
        self.sdk.observe(f"{project} is available", source="living_companion", project=project, kind=kind)
        if "esp32" in project.lower():
            return self.say(
                "The ESP32 project you worked on yesterday is available. I've indexed the source tree.",
                reason="project_memory",
            )
        return self.say(f"{project} is available. I've loaded its context.", reason="project_memory")

    def run_coding_demo(self) -> Dict[str, Any]:
        self.notice_app("Android Studio")
        self.notice_project("ESP32 alarm project", kind="hardware")
        self.agent_runtime.run_demo_mission()
        self.say("The Builder Agent finished compiling.", reason="agent_update")
        self.say("The Tester found one regression.", reason="agent_update")
        self.say("I've asked the Fixer Agent to investigate.", reason="agent_coordination")
        self.say("The issue was a missing import. It's repaired locally.", reason="repair_complete")
        self.say("All tests are now passing.", reason="verification")
        self.say("I've recorded a new build strategy. I'll use it next time.", reason="learning")
        return self.status()

    def status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "mode": self.mode,
            "messages": self.messages[-20:],
            "agents": self.agent_runtime.status(),
        }
