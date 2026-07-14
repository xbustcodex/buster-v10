from __future__ import annotations

import subprocess
import sys
from typing import Any, Dict

from .sdk_agent import SDKAgent


class TesterAgent(SDKAgent):
    agent_name = "tester_agent"

    def run(self, task: Any = None) -> Dict[str, Any]:
        payload = task if isinstance(task, dict) else {"request": str(task or "")}

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        output = (result.stdout + "\\n" + result.stderr).strip()

        data = {
            "agent": self.agent_name,
            "status": "passed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "request": payload.get("request", ""),
            "output_tail": output[-4000:],
        }

        self.publish("tester.completed", data)
        return data
