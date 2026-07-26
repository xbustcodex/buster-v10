# buster/learning/preference_memory.py
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class InterestItem:
    topic: str
    category: str  # e.g., "code_pattern", "api", "concept", "hobby"
    affinity_score: float  # 0.0 (dislike/bored) to 1.0 (fascinated)
    notes: List[str] = field(default_factory=list)
    last_explored: Optional[str] = None


class PersonalPreferenceMemory:
    """Manages Buster's autonomous likes, dislikes, and explored rabbit holes."""

    def __init__(self, storage_path: str | Path = "data/interests.json") -> None:
        self.storage_path = Path(storage_path)
        self.interests: Dict[str, InterestItem] = {}
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            self._save()
            return
        try:
            raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
            for key, val in raw.get("interests", {}).items():
                self.interests[key] = InterestItem(**val)
        except Exception as e:
            logger.error(f"Failed to load preference memory: {e}")

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "interests": {k: asdict(v) for k, v in self.interests.items()}
        }
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def record_exploration(self, topic: str, category: str, affinity_score: float, note: str) -> None:
        """Records an interest exploration or updates affinity."""
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()

        if topic in self.interests:
            item = self.interests[topic]
            item.affinity_score = round((item.affinity_score + affinity_score) / 2.0, 2)
            item.notes.append(note)
            item.last_explored = now_iso
        else:
            self.interests[topic] = InterestItem(
                topic=topic,
                category=category,
                affinity_score=affinity_score,
                notes=[note],
                last_explored=now_iso,
            )
        self._save()

    def get_top_interests(self, limit: int = 5) -> List[InterestItem]:
        sorted_items = sorted(self.interests.values(), key=lambda x: x.affinity_score, reverse=True)
        return sorted_items[:limit]