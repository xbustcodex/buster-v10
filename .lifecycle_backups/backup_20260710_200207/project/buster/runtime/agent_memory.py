from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from buster.runtime.storage import now


class AgentMemory:
    def __init__(self, sdk, path: str | Path = "data/agent_memory.json"):
        self.sdk = sdk
        self.path = Path(path)
        self.data = self._load()

    def _load(self):
        if not self.path.exists():
            return {"agents": {}, "events": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"agents": {}, "events": []}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def record(self, agent: str, action: str, result: Dict[str, Any]):
        profile = self.data.setdefault("agents", {}).setdefault(agent, {
            "runs": 0,
            "successes": 0,
            "failures": 0,
            "last_action": None,
            "last_result": None,
        })

        profile["runs"] += 1
        profile["last_action"] = action
        profile["last_result"] = result

        status = str(result.get("status", "")).lower()
        if status in {"completed", "passed", "success", "ok", "safe_noop"}:
            profile["successes"] += 1
        elif status in {"failed", "error"}:
            profile["failures"] += 1

        event = {
            "agent": agent,
            "action": action,
            "result_status": result.get("status"),
            "timestamp": now(),
        }

        self.data.setdefault("events", []).append(event)
        self.data["events"] = self.data["events"][-500:]

        self.save()
        self.sdk.publish("agent.memory.recorded", event, source="agent_memory")
        return profile

    def status(self):
        return self.data
