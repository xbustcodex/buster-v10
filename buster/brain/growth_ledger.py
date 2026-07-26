from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional


class GrowthLedgerManager:
    """Thread-safe manager tracking Buster's learning insights, hurdles, and toolbelt."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.storage_path = storage_path if storage_path else os.path.join(base_dir, "growth_ledger_state.json")
        self._lock = threading.RLock()
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        with self._lock:
            if not os.path.exists(self.storage_path):
                initial_state = {
                    "cognitive_rhythm": "Active Development Mode",
                    "hurdles": [],
                    "toolbelt": [],
                    "ambition_backlog": []
                }
                self._write_state(initial_state)

    def _read_state(self) -> Dict[str, Any]:
        with self._lock:
            if not os.path.exists(self.storage_path):
                return {"cognitive_rhythm": "Idle", "hurdles": [], "toolbelt": [], "ambition_backlog": []}
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {"cognitive_rhythm": "Idle", "hurdles": [], "toolbelt": [], "ambition_backlog": []}

    def _write_state(self, state: Dict[str, Any]) -> None:
        with self._lock:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return self._read_state()


if __name__ == "__main__":
    ledger = GrowthLedgerManager()
    snapshot = ledger.get_snapshot()
    print("✅ Growth Ledger loaded successfully:")
    print(f"  • Hurdles Patched: {len(snapshot.get('hurdles', []))}")
    print(f"  • Tools Registered: {len(snapshot.get('toolbelt', []))}")