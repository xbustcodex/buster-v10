from __future__ import annotations
from typing import Any, Dict, List
from .messages import AgentMessage, CollaborationDecision

class CollaborationBlackboard:
    def __init__(self) -> None:
        self.messages: List[AgentMessage] = []
        self.decisions: List[CollaborationDecision] = []
        self.shared_state: Dict[str, Any] = {}

    def post(self, agent: str, message: str, kind: str = "status", **data: Any) -> AgentMessage:
        msg = AgentMessage(agent=agent, message=message, kind=kind, data=data)
        self.messages.append(msg)
        return msg

    def decide(self, mission: str, chosen_agent: str, reason: str, confidence: float, next_agents: List[str] | None = None) -> CollaborationDecision:
        decision = CollaborationDecision(mission=mission, chosen_agent=chosen_agent, reason=reason, confidence=confidence, next_agents=next_agents or [])
        self.decisions.append(decision)
        return decision

    def set(self, key: str, value: Any) -> None:
        self.shared_state[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.shared_state.get(key, default)

    def timeline(self, limit: int = 50) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for msg in self.messages:
            item = msg.to_dict(); item["type"] = "message"; items.append(item)
        for dec in self.decisions:
            item = dec.to_dict(); item["type"] = "decision"; items.append(item)
        return sorted(items, key=lambda x: x["timestamp"])[-limit:]

    def status(self) -> Dict[str, Any]:
        return {"messages": [m.to_dict() for m in self.messages[-20:]], "decisions": [d.to_dict() for d in self.decisions[-20:]], "shared_state": self.shared_state, "timeline": self.timeline()}
