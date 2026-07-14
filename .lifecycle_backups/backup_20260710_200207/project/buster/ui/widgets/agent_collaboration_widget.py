
from __future__ import annotations

from typing import Dict, Any, List


class AgentCollaborationWidgetModel:
    def render_model(self, dashboard_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        agents: List[Dict[str, Any]] = dashboard_snapshot.get("active_agents", [])
        return {
            "title": dashboard_snapshot.get("title", "Collaborative Agent System"),
            "face_expression": dashboard_snapshot.get("face_expression", "idle"),
            "active_count": len(agents),
            "agents": agents,
            "activity": dashboard_snapshot.get("latest_activity", []),
            "conversation": dashboard_snapshot.get("agent_conversation", []),
            "voice_queue": dashboard_snapshot.get("pending_voice", []),
        }
