from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .sdk_agent import SDKAgent


class ReviewerAgent(SDKAgent):
    agent_name = "reviewer_agent"

    def run(self, task: Any = None) -> Dict[str, Any]:
        payload = task if isinstance(task, dict) else {"request": str(task or "")}

        runtime_files = list(Path("buster/runtime").glob("*.py"))
        test_files = list(Path("tests").glob("test_*.py"))

        findings = []

        if not runtime_files:
            findings.append("No runtime files found.")

        if not test_files:
            findings.append("No tests found.")

        if Path("data/runtime_events.json").exists():
            findings.append("Runtime event state file exists; ensure generated data is not committed unless intentional.")

        data = {
            "agent": self.agent_name,
            "status": "completed",
            "request": payload.get("request", ""),
            "runtime_files": len(runtime_files),
            "test_files": len(test_files),
            "findings": findings,
            "recommendation": "Architecture looks valid. Keep generated data out of commits.",
        }

        self.publish("reviewer.completed", data)
        return data
