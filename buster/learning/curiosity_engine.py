from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class CuriosityScore:
    novelty: float = 0.0
    importance: float = 0.0
    user_relevance: float = 0.0
    technical_value: float = 0.0
    future_usefulness: float = 0.0

    @property
    def total(self) -> float:
        # Multidimensional curiosity weighting
        weights = {
            "novelty": 0.25,
            "importance": 0.25,
            "user_relevance": 0.20,
            "technical_value": 0.15,
            "future_usefulness": 0.15,
        }
        return round(
            (self.novelty * weights["novelty"])
            + (self.importance * weights["importance"])
            + (self.user_relevance * weights["user_relevance"])
            + (self.technical_value * weights["technical_value"])
            + (self.future_usefulness * weights["future_usefulness"]),
            3,
        )


class CuriosityEngine:
    def __init__(self, data_dir: str | Path = "./data"):
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.downtime_queue_path = self.data_dir / "downtime_ideas.json"
        self.long_term_path = self.data_dir / "long_term_knowledge.json"

        self._ensure_storage()

    def _ensure_storage(self) -> None:
        if not self.downtime_queue_path.exists():
            self.downtime_queue_path.write_text("[]", encoding="utf-8")
        if not self.long_term_path.exists():
            self.long_term_path.write_text("[]", encoding="utf-8")

    def evaluate_and_route(
        self,
        topic: str,
        content: str,
        score: CuriosityScore,
        source: str = "runtime",
    ) -> Dict[str, Any]:
        entry = {
            "topic": topic,
            "content": content,
            "score_details": asdict(score),
            "curiosity_score": score.total,
            "source": source,
        }

        total_score = score.total

        if total_score < 0.4:
            action = "discard"
        elif 0.4 <= total_score < 0.8:
            action = "downtime_queue"
            self._append_json(self.downtime_queue_path, entry)
        else:
            action = "long_term_memory"
            self._append_json(self.long_term_path, entry)

        entry["action_taken"] = action
        return entry

    def _append_json(self, path: Path, entry: Dict[str, Any]) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = []
        data.append(entry)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def pop_next_downtime_idea(self) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(self.downtime_queue_path.read_text(encoding="utf-8"))
            if not data:
                return None
            next_idea = data.pop(0)
            self.downtime_queue_path.write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
            return next_idea
        except Exception:
            return None

    def status(self) -> Dict[str, Any]:
        try:
            downtime_count = len(json.loads(self.downtime_queue_path.read_text(encoding="utf-8")))
        except Exception:
            downtime_count = 0

        try:
            long_term_count = len(json.loads(self.long_term_path.read_text(encoding="utf-8")))
        except Exception:
            long_term_count = 0

        return {
            "downtime_ideas_count": downtime_count,
            "long_term_knowledge_count": long_term_count,
        }