from __future__ import annotations

from typing import Any, Dict

from buster.sdk import BusterSDK
from buster.agent_os import AgentRuntime, LivingCompanionRuntime
from buster.multi_agent import MultiAgentCollaborationRuntime

from .capabilities import CapabilityRegistry
from .mission import Mission, StepStatus


class MissionExecutor:
    def __init__(
        self,
        sdk: BusterSDK,
        capabilities: CapabilityRegistry,
        agent_runtime: AgentRuntime,
        companion: LivingCompanionRuntime,
        collaboration: MultiAgentCollaborationRuntime,
    ) -> None:
        self.sdk = sdk
        self.capabilities = capabilities
        self.agent_runtime = agent_runtime
        self.companion = companion
        self.collaboration = collaboration

    def execute(self, mission: Mission) -> Dict[str, Any]:
        mission.start()
        self.sdk.publish("mission.started", mission.to_dict(), source="mission_executor", priority="high")
        self.companion.say(f"I've started the mission: {mission.title}", reason="mission_started")

        for step in mission.steps:
            try:
                capability = self.capabilities.require(step.capability)
                agent = capability.provider
                step.start(agent)
                self.sdk.publish("mission.step.started", step.to_dict(), source="mission_executor")
                self.agent_runtime.assign(agent, step.title, mission=mission.title, capability=step.capability)

                result = self._simulate_capability(agent, step.capability, step.title)
                step.complete(result)
                self.agent_runtime.complete(agent, result["message"])
                self.sdk.publish("mission.step.completed", step.to_dict(), source="mission_executor")

                if result.get("speak"):
                    self.companion.say(result["message"], reason="mission_step")

            except Exception as exc:
                step.fail(str(exc))
                mission.fail()
                self.sdk.publish("mission.failed", mission.to_dict(), source="mission_executor", priority="high")
                self.companion.say(f"The mission failed at step: {step.title}. {exc}", reason="mission_failed")
                return mission.to_dict()

        if all(step.status == StepStatus.COMPLETED for step in mission.steps):
            mission.complete()
            self.sdk.publish("mission.completed", mission.to_dict(), source="mission_executor", priority="high")
            self.companion.say("Mission complete. I've recorded the useful strategy for next time.", reason="mission_completed")

        return mission.to_dict()

    def _simulate_capability(self, agent: str, capability: str, title: str) -> Dict[str, Any]:
        if capability == "build.compile":
            return {"ok": True, "message": "The Builder Agent finished compiling.", "speak": True}
        if capability == "test.run":
            return {"ok": True, "message": "The Tester Agent completed the test run.", "speak": True}
        if capability == "fix.repair":
            return {"ok": True, "message": "The Fixer Agent repaired the issue locally.", "speak": True}
        if capability == "verify.result":
            return {"ok": True, "message": "The Verifier Agent confirmed the result.", "speak": True}
        if capability == "learning.record":
            return {"ok": True, "message": "I've recorded a new build strategy. I'll use it next time.", "speak": True}
        return {"ok": True, "message": f"{agent.title()} Agent completed: {title}", "speak": False}
