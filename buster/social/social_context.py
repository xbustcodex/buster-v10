# buster/social/social_context.py
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SocialState:
    timestamp: str
    user_mood: str  # "focused", "casual", "frustrated", "idle"
    environment_noise_level: str  # "quiet", "active", "high_activity"
    active_engagement_mode: str  # "companion", "work", "dnd"
    relational_notes: List[str] = field(default_factory=list)


class SocialContextEngine:
    """Models user sentiment, environmental mood, and relational dynamics."""

    def __init__(self, storage_path: str | Path = "data/social_context.json") -> None:
        self.storage_path = Path(storage_path)
        self.state = SocialState(
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            user_mood="focused",
            environment_noise_level="quiet",
            active_engagement_mode="companion",
        )
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            self._save()
            return
        try:
            raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
            self.state = SocialState(**raw)
        except Exception as e:
            logger.error(f"Failed to load social context: {e}")

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(asdict(self.state), indent=2), encoding="utf-8")

    def update_context(
        self,
        user_mood: Optional[str] = None,
        noise_level: Optional[str] = None,
        engagement_mode: Optional[str] = None,
        note: Optional[str] = None,
    ) -> SocialState:
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.state.timestamp = now_iso

        if user_mood:
            self.state.user_mood = user_mood
        if noise_level:
            self.state.environment_noise_level = noise_level
        if engagement_mode:
            self.state.active_engagement_mode = engagement_mode
        if note:
            self.state.relational_notes.append(f"[{now_iso}] {note}")
            if len(self.state.relational_notes) > 50:
                self.state.relational_notes.pop(0)

        self._save()
        return self.state