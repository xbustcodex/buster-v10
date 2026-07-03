from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Capability:
    name: str
    provider: str
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "provider": self.provider,
            "description": self.description,
            "metadata": self.metadata,
        }


class CapabilityRegistry:
    def __init__(self) -> None:
        self.capabilities: Dict[str, Capability] = {}

    def register(self, name: str, provider: str, description: str = "", **metadata: Any) -> Capability:
        cap = Capability(name=name, provider=provider, description=description, metadata=metadata)
        self.capabilities[name] = cap
        return cap

    def get(self, name: str) -> Capability | None:
        return self.capabilities.get(name)

    def require(self, name: str) -> Capability:
        if name not in self.capabilities:
            raise KeyError(f"Missing capability: {name}")
        return self.capabilities[name]

    def provider_for(self, capability: str) -> str:
        return self.require(capability).provider

    def list(self) -> List[Dict[str, Any]]:
        return [cap.to_dict() for cap in self.capabilities.values()]

    def install_defaults(self) -> None:
        self.register("mission.plan", "planner", "Create mission plan")
        self.register("repo.index", "memory", "Load repository and project context")
        self.register("build.compile", "builder", "Compile or build project")
        self.register("test.run", "tester", "Run tests")
        self.register("fix.repair", "fixer", "Repair detected issue")
        self.register("review.quality", "reviewer", "Review quality and architecture")
        self.register("verify.result", "verifier", "Verify final result")
        self.register("learning.record", "learning", "Record reusable strategy")
        self.register("companion.explain", "conversation", "Explain mission progress")
