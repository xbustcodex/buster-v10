
from __future__ import annotations

from typing import Dict, Any

from buster.collaboration.engine import CollaborativeAgentEngine


class CollaborationDashboard:
    def __init__(self, engine: CollaborativeAgentEngine | None = None):
        self.engine = engine or CollaborativeAgentEngine()

    def snapshot(self) -> Dict[str, Any]:
        data = self.engine.dashboard()
        return {
            "title": "Collaborative Agent System",
            "face_expression": data["face_expression"],
            "active_agents": data["active_agents"],
            "latest_activity": data["latest_activity"],
            "agent_conversation": data["latest_conversation"],
            "pending_voice": data["pending_voice"],
        }
