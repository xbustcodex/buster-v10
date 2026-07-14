from __future__ import annotations
from buster.utils.datetime_utils import utc_now, utc_timestamp

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class MissionControl:
    def __init__(self, state_path: str | Path = "data/mission_control_state.json") -> None:
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_path.exists():
            self.save(self.default_state())

    def default_state(self) -> Dict[str, Any]:
        return {
            "status": "ready",
            "confidence": 0.0,
            "active_agents": [],
            "running_jobs": [],
            "plugins_loaded": [],
            "learning_entries": 0,
            "last_decision": None,
            "last_strategy": None,
            "updated_at": utc_now().replace(tzinfo=None).isoformat() + "Z",
        }

    def load(self) -> Dict[str, Any]:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return self.default_state()

    def save(self, data: Dict[str, Any]) -> None:
        data["updated_at"] = utc_now().replace(tzinfo=None).isoformat() + "Z"
        self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def update_from_reasoning(self, reasoning_result: Dict[str, Any]) -> Dict[str, Any]:
        state = self.load()
        state["confidence"] = reasoning_result.get("confidence", {}).get("score", 0.0)
        state["last_decision"] = reasoning_result.get("decision")
        state["last_strategy"] = reasoning_result.get("strategy", {}).get("name")
        self.save(state)
        return state

    def summary(self) -> str:
        state = self.load()
        return (
            "MISSION CONTROL\n"
            f"Status: {state.get('status')}\n"
            f"Confidence: {state.get('confidence')}\n"
            f"Decision: {state.get('last_decision')}\n"
            f"Strategy: {state.get('last_strategy', 'none')}\n"
            f"Plugins Loaded: {len(state.get('plugins_loaded', []))}\n"
            f"Running Jobs: {len(state.get('running_jobs', []))}\n"
        )
