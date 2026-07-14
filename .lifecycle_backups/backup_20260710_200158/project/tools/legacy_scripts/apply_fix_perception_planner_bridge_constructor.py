from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "buster" / "brain" / "planner" / "perception_planner_bridge.py"

CODE = '''from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, Optional
import json


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class PerceptionPlannerBridge:
    def __init__(self, data_dir: str | Path = "data", auto_persist: bool = True) -> None:
        self.data_dir = Path(data_dir)
        self.auto_persist = auto_persist
        self.state_file = self.data_dir / "perception_planner_bridge_state.json"
        self.state: Dict[str, Any] = {
            "created": _now(),
            "updated": _now(),
            "plans": 0,
            "last_plan": None,
        }
        self._persist()

    def create_plan_from_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        importance = float(observation.get("importance", 0.5))
        confidence = float(observation.get("confidence", 0.5))
        summary = observation.get("summary", "")
        source = observation.get("source", "unknown")

        action = "record_observation"
        priority = "normal"

        if importance >= 0.8:
            priority = "high"
            action = "update_world_model_and_notify_companion"
        elif confidence < 0.4:
            priority = "low"
            action = "request_more_context"

        plan = {
            "timestamp": _now(),
            "source": source,
            "summary": summary,
            "priority": priority,
            "action": action,
            "confidence": confidence,
            "importance": importance,
            "steps": [
                "record perception event",
                "update world model",
                "refresh working memory",
            ],
        }

        if priority == "high":
            plan["steps"].append("consider companion speech")

        self.state["plans"] = int(self.state.get("plans", 0)) + 1
        self.state["last_plan"] = plan
        self.state["updated"] = _now()
        self._persist()
        return plan

    def plan_from_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        return self.create_plan_from_observation(observation)

    def advise(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        return self.create_plan_from_observation(observation)

    def status(self) -> Dict[str, Any]:
        return dict(self.state)

    def _persist(self) -> None:
        if not self.auto_persist:
            return
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
'''

def main() -> None:
    print("=== Applying PerceptionPlannerBridge Constructor Repair ===")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(CODE, encoding="utf-8")
    print(f"[WRITE] {TARGET.relative_to(ROOT)}")
    print("\\nSUCCESS: PerceptionPlannerBridge now accepts data_dir and supports observation planning.")
    print("Next: python -m pytest")

if __name__ == "__main__":
    main()
