from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from buster.sdk import BusterSDK
from buster.agent_os import LivingCompanionRuntime
from buster.mission_runtime import AutonomousMissionRuntime
from buster.intent_os import MissionIntentRuntime
from buster.skills import SkillGrowthEngine

from .voice_runtime import VoiceRuntime
from .daily_rhythm import DailyRhythm


class LivingAICompanionRuntime:
    def __init__(self, sdk: BusterSDK | None = None, data_dir: str | Path = "data", mode: str = "companion") -> None:
        self.sdk = sdk or BusterSDK(data_dir=data_dir)
        self.data_dir = Path(data_dir)
        self.mode = mode
        self.voice = VoiceRuntime(self.sdk, data_dir=data_dir, mode=mode)
        self.rhythm = DailyRhythm()
        self.base_companion = LivingCompanionRuntime(self.sdk, data_dir=data_dir)
        self.mission_runtime = AutonomousMissionRuntime(self.sdk, data_dir=data_dir)
        self.intent_runtime = MissionIntentRuntime(self.sdk, data_dir=data_dir, mode=mode)
        self.skills = SkillGrowthEngine(data_dir=data_dir)
        self.running = False

    def start_day(self, name: str = "Adam") -> Dict[str, Any]:
        self.running = True
        self.base_companion.start()
        self.mission_runtime.start()
        greeting = self.rhythm.greeting(name)
        self.voice.enqueue(greeting, reason="daily_greeting", priority="high")
        self.voice.enqueue("Buster is online. Mission runtime, agents, and workspace awareness are ready.", reason="startup")
        self.voice.drain()
        return self.status()

    def handle_workspace_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        result = self.intent_runtime.process_workspace(context)
        hypothesis = result["hypothesis"]
        if result.get("speech"):
            self.voice.enqueue(result["speech"]["message"], reason="intent_prediction")
        self.skills.record_event({"type": hypothesis["intent"], "summary": hypothesis["summary"]}, success=True)
        self.voice.drain()
        return {"intent": hypothesis, "voice": self.voice.status(), "skills": self.skills.status()}

    def run_development_mission(self, title: str, intent: str = "development") -> Dict[str, Any]:
        result = self.mission_runtime.run_development_mission(title, intent=intent)
        for step in result["steps"]:
            self.skills.record_event(step, success=step["status"] == "completed")
        self.voice.enqueue("The autonomous development mission is complete.", reason="mission_complete", priority="high")
        self.voice.drain()
        return {"mission": result, "voice": self.voice.status(), "skills": self.skills.status()}

    def status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "mode": self.mode,
            "voice": self.voice.status(),
            "skills": self.skills.status(),
            "mission_runtime": self.mission_runtime.status(),
        }
