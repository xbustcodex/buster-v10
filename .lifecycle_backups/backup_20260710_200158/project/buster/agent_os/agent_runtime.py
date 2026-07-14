from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from buster.sdk import BusterSDK
from .agent_service import AgentService
from .registry import AgentRegistry


DEFAULT_AGENTS = [
    ("planner", "Creates missions and assigns work"),
    ("builder", "Builds code and project assets"),
    ("tester", "Runs tests and finds regressions"),
    ("fixer", "Repairs issues discovered by tests"),
    ("reviewer", "Reviews quality and architecture"),
    ("verifier", "Confirms the final result"),
    ("vision", "Reports visual observations"),
    ("hearing", "Reports audio observations"),
    ("memory", "Retrieves relevant history"),
    ("learning", "Records strategies and patterns"),
    ("conversation", "Explains activity to the user"),
    ("presence", "Manages companion state"),
    ("world_model", "Maintains environment context"),
]


class AgentRuntime:
    def __init__(self, sdk: BusterSDK | None = None, data_dir: str | Path = "data") -> None:
        self.sdk = sdk or BusterSDK(data_dir=data_dir)
        self.registry = AgentRegistry()
        self.running = False
        self.timeline: List[Dict[str, Any]] = []

    def install_default_agents(self) -> Dict[str, Any]:
        for name, role in DEFAULT_AGENTS:
            agent = AgentService(name=name, role=role)
            self.registry.register(agent)
            self.sdk.register_service(f"agent.{name}", agent)
            self.sdk.register_module(f"agent.{name}", agent)
        self.sdk.publish("agent_os.installed", {"agents": list(self.registry.agents)}, source="agent_runtime")
        return self.status()

    def start(self) -> Dict[str, Any]:
        if not self.registry.agents:
            self.install_default_agents()
        self.running = True
        self.sdk.start()
        self.sdk.publish("agent_os.started", {"agents": list(self.registry.agents)}, source="agent_runtime")
        return self.status()

    def stop(self) -> Dict[str, Any]:
        self.running = False
        self.sdk.stop()
        self.sdk.publish("agent_os.stopped", {}, source="agent_runtime")
        return self.status()

    def assign(self, agent_name: str, task: str, **metadata: Any) -> Dict[str, Any]:
        agent = self.registry.require(agent_name)
        status = agent.assign(task, **metadata)
        event = self.sdk.publish(
            "agent.task.assigned",
            {"agent": agent_name, "task": task, "status": status},
            source="agent_runtime",
        )
        item = {"event": event.type, "agent": agent_name, "message": task, "status": status}
        self.timeline.append(item)
        return item

    def complete(self, agent_name: str, message: str) -> Dict[str, Any]:
        agent = self.registry.require(agent_name)
        status = agent.complete(message)
        event = self.sdk.publish(
            "agent.task.completed",
            {"agent": agent_name, "message": message, "status": status},
            source="agent_runtime",
        )
        item = {"event": event.type, "agent": agent_name, "message": message, "status": status}
        self.timeline.append(item)
        return item

    def run_demo_mission(self) -> Dict[str, Any]:
        self.assign("planner", "Create coding session mission")
        self.complete("planner", "Mission created")
        self.assign("builder", "Analyse project dependencies")
        self.complete("builder", "Builder Agent finished compiling")
        self.assign("tester", "Run test suite")
        self.complete("tester", "Tester found one regression")
        self.assign("fixer", "Investigate failing test")
        self.complete("fixer", "Missing import repaired locally")
        self.assign("verifier", "Run verification")
        self.complete("verifier", "All tests are passing")
        self.assign("learning", "Record reusable build strategy")
        self.complete("learning", "Recorded new build strategy")
        return self.status()

    def status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "agents": self.registry.status(),
            "timeline": self.timeline[-20:],
            "sdk": self.sdk.status(),
        }
