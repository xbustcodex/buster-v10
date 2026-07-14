
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List

from .agent_state import AgentState, AgentStatus
from .activity_feed import AgentActivityFeed
from .conversation import AgentConversation
from .proactive_voice import ProactiveVoicePresence


DEFAULT_AGENTS = {
    "Planner": "creates missions and chooses strategies",
    "Builder": "builds files and project structure",
    "Tester": "runs tests and finds failures",
    "Fixer": "repairs errors and failed tests",
    "Reviewer": "checks quality and design",
    "Verifier": "confirms the mission is complete",
    "Learning": "records reusable lessons",
    "Experience": "updates skills and project knowledge",
}


class CollaborativeAgentEngine:
    def __init__(self, state_path: str | Path = "data/collaborative_agents_state.json"):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.feed = AgentActivityFeed()
        self.conversation = AgentConversation()
        self.voice = ProactiveVoicePresence()
        self.agents: Dict[str, AgentState] = {}
        self._load_or_init()

    def _load_or_init(self) -> None:
        if self.state_path.exists():
            try:
                raw = json.loads(self.state_path.read_text(encoding="utf-8"))
                for name, info in raw.get("agents", {}).items():
                    self.agents[name] = AgentState(**info)
                if self.agents:
                    return
            except Exception:
                pass
        self.agents = {name: AgentState(name=name, role=role) for name, role in DEFAULT_AGENTS.items()}
        self.save()

    def save(self) -> None:
        data = {
            "agents": {name: state.to_dict() for name, state in self.agents.items()},
            "active_count": len([a for a in self.agents.values() if a.status != AgentStatus.IDLE]),
        }
        self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def set_agent_state(self, agent: str, status: str, message: str = "", confidence: float = 0.0, risk: str = "unknown", mission_id: str = "default", talk: bool = False) -> Dict[str, Any]:
        if agent not in self.agents:
            self.agents[agent] = AgentState(name=agent, role="custom agent")
        self.agents[agent].update(status=status, message=message, confidence=confidence, risk=risk)
        self.save()
        event = self.feed.record(agent, status, message, confidence, risk, mission_id)
        self.conversation.say(agent, message or f"{agent} is {status}.", reason=f"Agent state changed to {status}.", confidence=confidence, mission_id=mission_id)
        if talk:
            self.voice.speak(text=message or f"{agent} is {status}.", reason=f"{agent} changed state to {status}.", priority="normal", confidence=confidence)
        return event

    def mission_story_demo(self, mission_id: str = "demo") -> List[Dict[str, Any]]:
        events = []
        events.append(self.set_agent_state("Planner", AgentStatus.PLANNING, "Mission created.", 0.92, "low", mission_id, True))
        events.append(self.set_agent_state("Builder", AgentStatus.BUILDING, "Generating project structure.", 0.88, "medium", mission_id))
        events.append(self.set_agent_state("Tester", AgentStatus.TESTING, "Running tests.", 0.84, "medium", mission_id))
        events.append(self.set_agent_state("Fixer", AgentStatus.FIXING, "Applying previous solution from Experience Engine.", 0.91, "low", mission_id, True))
        events.append(self.set_agent_state("Verifier", AgentStatus.VERIFYING, "Mission verified successfully.", 0.97, "low", mission_id, True))
        events.append(self.set_agent_state("Learning", AgentStatus.LEARNING, "Recorded a reusable success pattern.", 0.95, "low", mission_id))
        events.append(self.set_agent_state("Experience", AgentStatus.LEARNING, "Updated skill profile for this project type.", 0.93, "low", mission_id))
        return events

    def dashboard(self) -> Dict[str, Any]:
        active = [a.to_dict() for a in self.agents.values() if a.status != AgentStatus.IDLE]
        face = "thinking" if any(a["status"] in ("thinking", "planning") for a in active) else "working" if active else "idle"
        return {
            "agents": {name: state.to_dict() for name, state in self.agents.items()},
            "active_agents": active,
            "latest_activity": self.feed.latest(15),
            "latest_conversation": self.conversation.latest(15, user_visible_only=True),
            "pending_voice": self.voice.pending(5),
            "face_expression": face,
        }
