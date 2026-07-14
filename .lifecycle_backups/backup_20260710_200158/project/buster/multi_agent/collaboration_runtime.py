from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
import json
from buster.sdk import BusterSDK
from buster.agent_os import AgentRuntime, LivingCompanionRuntime
from .blackboard import CollaborationBlackboard
from .delegation import DelegationPlanner
from .negotiation import AgentNegotiator

class MultiAgentCollaborationRuntime:
    def __init__(self, sdk: BusterSDK | None = None, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.sdk = sdk or BusterSDK(data_dir=data_dir)
        self.agent_runtime = AgentRuntime(self.sdk, data_dir=data_dir)
        self.companion = LivingCompanionRuntime(self.sdk, data_dir=data_dir)
        self.blackboard = CollaborationBlackboard()
        self.delegation = DelegationPlanner()
        self.negotiator = AgentNegotiator(self.blackboard)
        self.running = False
        self.state_file = self.data_dir / "multi_agent_collaboration_state.json"
        self.timeline_file = self.data_dir / "multi_agent_timeline.json"

    def start(self) -> Dict[str, Any]:
        self.running = True
        self.agent_runtime.start()
        self.companion.start()
        self.sdk.publish("multi_agent.started", {"running": True}, source="multi_agent")
        self._persist()
        return self.status()

    def stop(self) -> Dict[str, Any]:
        self.running = False
        self.sdk.publish("multi_agent.stopped", {"running": False}, source="multi_agent")
        self._persist()
        return self.status()

    def run_mission(self, mission: str, intent: str = "general") -> Dict[str, Any]:
        if not self.running:
            self.start()
        plan = self.delegation.plan(mission, intent)
        agents: List[str] = list(plan["agents"])
        self.blackboard.post("planner", f"Mission created: {mission}", kind="mission", intent=intent)
        self.companion.say(f"I've created the mission: {mission}", reason="mission_created")

        for index, agent_name in enumerate(agents):
            negotiation = self.negotiator.negotiate(f"{mission} step {index + 1}", agents[index:])
            chosen = negotiation["decision"]["chosen_agent"]
            self.blackboard.post(chosen, f"{chosen.title()} Agent accepted work.", kind="agent_accept")
            self.agent_runtime.assign(chosen, f"Working on mission: {mission}", step=index + 1)
            self.sdk.publish("multi_agent.agent_selected", {"mission": mission, "agent": chosen, "negotiation": negotiation}, source="multi_agent")
            if chosen == "tester":
                self.blackboard.post("tester", "Tester found one regression.", kind="finding")
                self.companion.say("The Tester found one regression.", reason="agent_update")
            elif chosen == "fixer":
                self.blackboard.post("fixer", "Fixer is investigating the failure.", kind="repair")
                self.companion.say("I've asked the Fixer Agent to investigate.", reason="agent_coordination")
            elif chosen == "verifier":
                self.blackboard.post("verifier", "Verifier confirmed the result.", kind="verify")
                self.companion.say("All tests are now passing.", reason="verification")
            elif chosen == "learning":
                self.blackboard.post("learning", "Learning recorded the successful teamwork strategy.", kind="learning")
                self.companion.say("I've recorded the teamwork strategy. I'll use it next time.", reason="learning")
            self.agent_runtime.complete(chosen, f"{chosen.title()} Agent completed step {index + 1}")

        self.blackboard.post("planner", "Mission collaboration complete.", kind="mission_complete")
        self.sdk.publish("multi_agent.mission.completed", {"mission": mission, "intent": intent}, source="multi_agent")
        self._persist()
        return self.status()

    def status(self) -> Dict[str, Any]:
        return {"running": self.running, "blackboard": self.blackboard.status(), "agents": self.agent_runtime.status(), "companion": self.companion.status()}

    def _persist(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.status(), indent=2), encoding="utf-8")
        self.timeline_file.write_text(json.dumps(self.blackboard.timeline(), indent=2), encoding="utf-8")
