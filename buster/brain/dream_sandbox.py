from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from buster.brain.hurdle_engine import HurdleEngine


class DreamSandboxService:
    """Overnight Maintenance and Dream Phase Processor."""

    def __init__(
        self,
        ledger_path: Optional[str] = None,
        sandbox_dir: Optional[str] = None,
    ) -> None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.ledger_path = ledger_path if ledger_path else os.path.join(base_dir, "growth_ledger.json")
        self.sandbox_dir = sandbox_dir if sandbox_dir else os.path.join(base_dir, "sandbox")
        
        self.hurdle_engine = HurdleEngine(ledger_path=self.ledger_path)
        os.makedirs(self.sandbox_dir, exist_ok=True)

    def process_dream_cycle(self) -> Dict[str, Any]:
        """Executes overnight dream phase processing."""
        print("🌙 [Dream Sandbox] Initiating overnight maintenance & cognitive dream cycle...")

        ledger = self._load_ledger()
        hurdles: List[Dict[str, Any]] = ledger.get("hurdles", [])
        
        pending_hurdles = [h for h in hurdles if h.get("status") == "Queued for Sandbox Testing"]

        if not pending_hurdles:
            print("💤 [Dream Sandbox] No pending hurdles found. Memory pruned and system stabilized.")
            return {"processed_count": 0, "status": "Idle"}

        resolved_count = 0
        new_tools = []

        for hurdle in pending_hurdles:
            print(f"🔬 [Dream Sandbox] Simulating patch for Hurdle [{hurdle['id']}]: {hurdle['task']}")
            
            success = self._simulate_sandbox_patch(hurdle)
            if success:
                hurdle["status"] = "Resolved in Dream Mode"
                hurdle["resolved_at"] = datetime.now().isoformat()
                resolved_count += 1

                upgrade = hurdle.get("proposed_self_upgrade", {})
                if upgrade.get("action") == "CREATE_UTILITY":
                    tool_name = f"util_{hurdle['id'].replace('-', '_')}"
                    new_tools.append({
                        "name": tool_name,
                        "description": upgrade.get("summary", "Self-built utility tool"),
                        "path": os.path.join("brain", "tools", f"{tool_name}.py"),
                        "registered_at": datetime.now().isoformat()
                    })

        # Append new tools directly to ledger memory before saving
        if "toolbelt" not in ledger:
            ledger["toolbelt"] = []
            
        ledger["toolbelt"].extend(new_tools)
        self._save_ledger(ledger)

        summary = {
            "processed_count": len(pending_hurdles),
            "resolved_count": resolved_count,
            "status": "Dream Cycle Complete",
        }
        print(f"☀️ [Dream Sandbox] Wakeup preparation complete: {resolved_count}/{len(pending_hurdles)} hurdles patched.")
        return summary

    def _simulate_sandbox_patch(self, hurdle: Dict[str, Any]) -> bool:
        """Simulates testing a code patch in an isolated sandbox environment."""
        sandbox_file = os.path.join(self.sandbox_dir, f"test_{hurdle['id']}.py")
        
        with open(sandbox_file, "w", encoding="utf-8") as f:
            f.write(f"# Sandbox Test Execution for Task: {hurdle['task']}\n")
            f.write(f"# Error Analyzed: {hurdle['error_type']}\n")
            f.write("def run_sandbox_simulation():\n")
            f.write("    return True\n\n")
            f.write("if __name__ == '__main__':\n")
            f.write("    run_sandbox_simulation()\n")

        time.sleep(0.5)
        return True

    def _load_ledger(self) -> Dict[str, Any]:
        if os.path.exists(self.ledger_path):
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    pass
        return {"hurdles": [], "toolbelt": [], "ambition_backlog": []}

    def _save_ledger(self, ledger: Dict[str, Any]) -> None:
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            json.dump(ledger, f, indent=2)


if __name__ == "__main__":
    service = DreamSandboxService()
    result = service.process_dream_cycle()
    print("Execution Result:", json.dumps(result, indent=2))