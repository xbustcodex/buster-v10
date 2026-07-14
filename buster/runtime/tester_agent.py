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

        status = "passed" if result.returncode == 0 else "failed"

        output = (result.stdout + "\n" + result.stderr).strip()

        summary = (
            output.splitlines()[-1]
            if output
            else (
                "All tests passed."
                if status == "passed"
                else "Tests failed."
            )
        )

        data = {
            "agent": self.agent_name,

            "status": status,

            "returncode": result.returncode,

            "request": payload.get("request", ""),
  
            "summary": summary,

            "message": summary,

            "output": output,

            "error": output if status == "failed" else "",

            "output_tail": output[-4000:],
        }

        self.publish("tester.completed", data)
        return data
