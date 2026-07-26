from __future__ import annotations

import json
import os
import traceback
from datetime import datetime
from typing import Dict, Any, Optional


class HurdleEngine:
    """Technician Mindset: Captures runtime errors and missing capabilities,

    converting them into self-upgrade plans in the Growth Ledger.
    """

    def __init__(self, ledger_path: Optional[str] = None) -> None:
        if ledger_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.ledger_path = os.path.join(base_dir, "growth_ledger.json")
        else:
            self.ledger_path = ledger_path
        self._ensure_ledger_exists()

    def _ensure_ledger_exists(self) -> None:
        """Ensures the growth ledger JSON file and directory structure exist."""
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        if not os.path.exists(self.ledger_path):
            initial_data = {
                "hurdles": [],
                "toolbelt": [],
                "ambition_backlog": [
                    {
                        "id": "amb-001",
                        "title": "Establish Autonomous Self-Patching Protocol",
                        "status": "In Progress",
                        "priority": "High"
                    }
                ]
            }
            with open(self.ledger_path, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2)

    def handle_hurdle(self, task_name: str, exception: Exception) -> Dict[str, Any]:
        """Triggered whenever Buster hits a roadblock during execution.

        Formulates an upgrade plan instead of raising a blind failure.
        """
        error_type = type(exception).__name__
        error_msg = str(exception)
        tb_str = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))

        print(f"🚧 [Hurdle Engine] Roadblock detected in [{task_name}]: {error_type} - {error_msg}")

        # 1. Formulate a self-upgrade plan based on technician heuristics
        upgrade_plan = self.formulate_upgrade_plan(error_type, error_msg)

        # 2. Build the Hurdle Entry
        hurdle_entry = {
            "id": f"hrd-{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "task": task_name,
            "error_type": error_type,
            "error_message": error_msg,
            "traceback": tb_str,
            "status": "Queued for Sandbox Testing",
            "proposed_self_upgrade": upgrade_plan
        }

        # 3. Commit entry to Growth Ledger
        self._log_to_ledger("hurdles", hurdle_entry)

        return hurdle_entry

    def formulate_upgrade_plan(self, error_type: str, error_msg: str) -> Dict[str, str]:
        """Analyzes error signatures and proposes concrete technical solutions."""
        if "FileNotFoundError" in error_type or "No such file" in error_msg:
            return {
                "action": "CREATE_UTILITY",
                "summary": "Build automated path verification and workspace directory fallback in brain/tools/."
            }
        elif "TimeoutError" in error_type or "timed out" in error_msg.lower():
            return {
                "action": "REFACTOR_ASYNC",
                "summary": "Refactor execution worker to stream chunked output and increase buffer timeout."
            }
        elif "ImportError" in error_type or "ModuleNotFoundError" in error_type:
            return {
                "action": "DEPENDENCY_PATCH",
                "summary": "Auto-detect missing dependency and log sandbox environment install task."
            }
        else:
            return {
                "action": "CODE_REFACTOR",
                "summary": "Generate sandbox refactoring patch to isolate execution context."
            }

    def register_tool(self, tool_name: str, description: str, path: str) -> None:
        """Registers a newly self-built tool to Buster's toolbelt."""
        tool_entry = {
            "name": tool_name,
            "description": description,
            "path": path,
            "registered_at": datetime.now().isoformat()
        }
        self._log_to_ledger("toolbelt", tool_entry)

    def _log_to_ledger(self, key: str, data: Dict[str, Any]) -> None:
        """Helper to append structured data into the growth ledger JSON."""
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            ledger = {"hurdles": [], "toolbelt": [], "ambition_backlog": []}

        if key not in ledger:
            ledger[key] = []

        ledger[key].append(data)

        with open(self.ledger_path, "w", encoding="utf-8") as f:
            json.dump(ledger, f, indent=2)


if __name__ == "__main__":
    engine = HurdleEngine()
    try:
        open("non_existent_config.json", "r")
    except Exception as e:
        result = engine.handle_hurdle("Load Config File", e)
        print("Logged Hurdle Successfully:")
        print(json.dumps(result, indent=2))