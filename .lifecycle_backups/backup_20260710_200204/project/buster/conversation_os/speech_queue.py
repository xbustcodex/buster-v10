from __future__ import annotations
from buster.utils.datetime_utils import utc_now, utc_timestamp

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import uuid4


def utc_now() -> str:
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
        self.path.write_text(json.dumps(items[-500:], indent=2), encoding="utf-8")

    def add(self, text: str, priority: str = "normal", source: str = "buster", reason: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        item = {
            "id": uuid4().hex[:12],
            "text": text,
            "priority": priority,
            "source": source,
            "reason": reason,
            "metadata": metadata or {},
            "created": utc_now(),
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
                item["spoken_at"] = utc_now()
                changed = True
                break
        self._save(items)
        return changed

    def clear(self) -> None:
        self._save([])
