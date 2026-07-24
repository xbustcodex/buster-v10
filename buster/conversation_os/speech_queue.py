from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4


def get_utc_now_str() -> str:
    """Returns ISO formatted UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SpeechQueue:
    def __init__(self, path: str = "data/proactive_speech_queue.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _load(self) -> List[Dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, items: List[Dict[str, Any]]) -> None:
        temp_path = self.path.with_suffix(".tmp")
        try:
            temp_path.write_text(json.dumps(items[-500:], indent=2), encoding="utf-8")
            temp_path.replace(self.path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()

    def add(
        self,
        text: str,
        priority: str = "normal",
        source: str = "buster",
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        item = {
            "id": uuid4().hex[:12],
            "text": text,
            "priority": priority,
            "source": source,
            "reason": reason,
            "metadata": metadata or {},
            "created": get_utc_now_str(),
            "spoken": False,
            "spoken_at": None,
        }
        items = self._load()
        items.append(item)
        self._save(items)
        return item

    def pending(self) -> List[Dict[str, Any]]:
        return [i for i in self._load() if not i.get("spoken")]

    def mark_spoken(self, item_id: str) -> bool:
        items = self._load()
        changed = False
        for item in items:
            if item.get("id") == item_id:
                item["spoken"] = True
                item["spoken_at"] = get_utc_now_str()
                changed = True
                break
        if changed:
            self._save(items)
        return changed

    def clear(self) -> None:
        self._save([])