from __future__ import annotations
from buster.utils.datetime_utils import utc_now, utc_timestamp
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime
from .storage import load_json, save_json

def _now() -> str:
    return utc_timestamp()

class DesignDecisionStore:
    """Stores architecture/design choices and ranks how well they work."""
    def __init__(self, path: str | Path = "data/design_decisions.json") -> None:
        self.path = Path(path)
        data = load_json(self.path, [])
        self.decisions: List[Dict[str, Any]] = data if isinstance(data, list) else []
    def record(self, project_type: str, decision: str, outcome: str, confidence: float = 0.5, notes: str = "") -> Dict[str, Any]:
        item = {"timestamp": _now(), "project_type": project_type or "general", "decision": decision, "outcome": outcome, "confidence": float(confidence), "notes": notes}
        self.decisions.append(item); self.save(); return item
    def recommend(self, project_type: str, limit: int = 5) -> List[Dict[str, Any]]:
        ptype = (project_type or "general").lower()
        candidates = [d for d in self.decisions if d.get("project_type", "").lower() in {ptype, "general"}]
        def score(d: Dict[str, Any]) -> float:
            bonus = 1.0 if str(d.get("outcome", "")).lower() in {"success", "accepted", "passed"} else 0.0
            return float(d.get("confidence", 0.5)) + bonus
        return sorted(candidates, key=score, reverse=True)[:limit]
    def save(self) -> None:
        save_json(self.path, self.decisions)
