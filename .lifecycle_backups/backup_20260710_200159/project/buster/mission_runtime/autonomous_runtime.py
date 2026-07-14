from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json

from buster.sdk import BusterSDK
from buster.agent_os import AgentRuntime, LivingCompanionRuntime
from buster.multi_agent import MultiAgentCollaborationRuntime

from .capabilities import CapabilityRegistry
from .executor import MissionExecutor
from .mission import Mission
from .scheduler import MissionScheduler


class AutonomousMissionRuntime:
    def __init__(self, sdk: BusterSDK | None = None, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.sdk = sdk or BusterSDK(data_dir=data_dir)
        self.capabilities = CapabilityRegistry()
        self.capabilities.install_defaults()
        self.scheduler = MissionScheduler()
        self.agent_runtime = AgentRuntime(self.sdk, data_dir=data_dir)
        self.companion = LivingCompanionRuntime(self.sdk, data_dir=data_dir)
        self.collaboration = MultiAgentCollaborationRuntime(self.sdk, data_dir=data_dir)
        self.executor = MissionExecutor(self.sdk, self.capabilities, self.agent_runtime, self.companion, self.collaboration)
        self.running = False
        self.state_file = self.data_dir / "autonomous_mission_runtime_state.json"

    def start(self) -> Dict[str, Any]:
        self.running = True
        self.agent_runtime.start()
        self.companion.start()
        self.sdk.publish("autonomous_mission_runtime.started", {"running": True}, source="autonomous_mission_runtime")
        self._persist()
        return self.status()

    def stop(self) -> Dict[str, Any]:
        self.running = False
        self.sdk.publish("autonomous_mission_runtime.stopped", {"running": False}, source="autonomous_mission_runtime")
        self._persist()
        return self.status()

    def create_development_mission(self, title: str, intent: str = "development") -> Mission:
        mission = Mission(title=title, intent=intent)
        mission.add_step("Plan mission strategy", "mission.plan")
        mission.add_step("Load project context", "repo.index")
        mission.add_step("Compile/build project", "build.compile")
        mission.add_step("Run test suite", "test.run")
        mission.add_step("Repair issues if needed", "fix.repair")
        mission.add_step("Review quality", "review.quality")
        mission.add_step("Verify result", "verify.result")
        mission.add_step("Record reusable strategy", "learning.record")
        return mission

    def submit(self, mission: Mission) -> Dict[str, Any]:
        self.scheduler.submit(mission)
        self.sdk.publish("mission.queued", mission.to_dict(), source="autonomous_mission_runtime")
        self._persist()
        return mission.to_dict()

    def run_next(self) -> Dict[str, Any] | None:
        mission = self.scheduler.next()
        if mission is None:
            return None
        result = self.executor.execute(mission)
        self.scheduler.mark_completed(mission)
        self._persist()
        return result

    def run_development_mission(self, title: str, intent: str = "development") -> Dict[str, Any]:
        if not self.running:
            self.start()
        mission = self.create_development_mission(title, intent)
        self.submit(mission)
        result = self.run_next()
        assert result is not None
        return result

    def status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "capabilities": self.capabilities.list(),
            "scheduler": self.scheduler.status(),
            "agents": self.agent_runtime.status(),
            "companion": self.companion.status(),
        }

    def _persist(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.status(), indent=2), encoding="utf-8")
