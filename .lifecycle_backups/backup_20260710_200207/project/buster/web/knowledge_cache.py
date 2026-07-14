import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List


class KnowledgeCache:
    """
    Long-term useful web knowledge cache.

    This is separate from the short TTL WebCache. Use this for facts, docs,
    and findings Buster chooses to remember.
    """

    def __init__(self, path: str = "data/web_knowledge_cache.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict:
        if not self.path.exists():
            return {"items": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"items": []}

    def _save(self):
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def remember(self, topic: str, summary: str, sources: List[dict] | None = None):
        self.data.setdefault("items", []).append({
            "topic": topic,
            "summary": summary,
            "sources": sources or [],
            "saved_at": datetime.now(timezone.utc).isoformat(),
        })
        self._save()

    def find(self, topic: str) -> List[dict]:
        needle = topic.lower()
        return [
            item for item in self.data.get("items", [])
            if needle in item.get("topic", "").lower() or needle in item.get("summary", "").lower()
        ]
