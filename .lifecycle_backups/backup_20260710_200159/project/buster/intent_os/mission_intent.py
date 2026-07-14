from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.sdk import BusterSDK
from buster.agent_os import LivingCompanionRuntime
from buster.workspace_awareness import WorkspaceAwarenessRuntime

from .intent_engine import IntentActivityEngine
from .interrupt_policy import InterruptPolicy


class MissionIntentRuntime:
    def __init__(self, sdk: BusterSDK | None = None, data_dir: str | Path = "data", mode: str = "companion") -> None:
        self.data_dir = Path(data_dir)
        self.sdk = sdk or BusterSDK(data_dir=data_dir)
        self.workspace = WorkspaceAwarenessRuntime(self.sdk, data_dir=data_dir)
        self.intent_engine = IntentActivityEngine(self.sdk, data_dir=data_dir)
        self.companion = LivingCompanionRuntime(self.sdk, data_dir=data_dir)
        self.policy = InterruptPolicy(mode)
        self.running = False

    def start(self) -> Dict[str, Any]:
        self.running = True
        self.workspace.start()
        self.companion.start()
        self.sdk.publish("mission_intent.started", {"running": True}, source="mission_intent")
        return self.status()

    def stop(self) -> Dict[str, Any]:
        self.running = False
        self.workspace.stop()
        self.sdk.publish("mission_intent.stopped", {"running": False}, source="mission_intent")
        return self.status()

    def process_workspace(self, context: Dict[str, Any]) -> Dict[str, Any]:
        workspace_result = self.workspace.scan(context)
        self.intent_engine.add_workspace_events(workspace_result["events"])
        hypothesis = self.intent_engine.infer()

        speech = None
        if self.policy.should_speak(hypothesis):
            speech = self.companion.say(self._speech_for_intent(hypothesis.to_dict()), reason="intent_prediction")

        return {
            "workspace": workspace_result,
            "hypothesis": hypothesis.to_dict(),
            "speech": speech,
            "policy": self.policy.style(),
        }

    def _speech_for_intent(self, hypothesis: Dict[str, Any]) -> str:
        intent = hypothesis["intent"]
        if intent == "android_development":
            return "It looks like you're starting an Android development session. I'll prepare the project context and testing agents."
        if intent == "esp32_development":
            return "It looks like you're continuing ESP32 development. I'll prepare the hardware workflow and serial monitor context."
        if intent == "hardware_android_development":
            return "It looks like you're working across Android and ESP32. I'll prepare both development contexts."
        if intent == "debugging_tests":
            return "It looks like you're debugging tests. I'll prepare the Fixer and Tester agents."
        return hypothesis["summary"]

    def status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "intent": self.intent_engine.status(),
            "policy": self.policy.style(),
            "workspace": self.workspace.status(),
        }
