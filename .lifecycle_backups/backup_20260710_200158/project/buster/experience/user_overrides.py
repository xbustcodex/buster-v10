from __future__ import annotations
from buster.utils.datetime_utils import utc_now, utc_timestamp
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime
from .storage import load_json, save_json

def _now() -> str:
    return utc_timestamp()

class UserOverrideStore:
    """Remembers when the user chooses a different path than Buster recommended."""
    def __init__(self, path: str | Path = "data/user_overrides.json") -> None:
        self.path = Path(path)
        data = load_json(self.path, [])
        self.overrides: List[Dict[str, Any]] = data if isinstance(data, list) else []
    def record(self, context: str, recommended: str, chosen: str, reason: str = "") -> Dict[str, Any]:
        item = {"timestamp": _now(), "context": context, "recommended": recommended, "chosen": chosen, "reason": reason}
        self.overrides.append(item); self.save(); return item
    def recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        return list(reversed(self.overrides[-limit:]))
    def save(self) -> None:
        save_json(self.path, self.overrides)
