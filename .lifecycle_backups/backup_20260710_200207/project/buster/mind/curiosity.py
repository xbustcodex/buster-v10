from __future__ import annotations

from typing import Any, Dict, List

from .storage import load_json, append_record, now_iso

CURIOSITY_LOG = "data/curiosity_log.json"


class CuriosityEngine:
    """Finds useful improvement opportunities from repeated patterns."""

    def __init__(self, log_path: str = CURIOSITY_LOG):
        self.log_path = log_path

    def inspect_patterns(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        suggestions: List[Dict[str, Any]] = []
        for pattern in patterns:
            count = int(pattern.get("count", pattern.get("uses", 0)) or 0)
            name = pattern.get("name") or pattern.get("title") or "Repeated pattern"
            domain = pattern.get("domain", "general")
            if count >= 3:
                suggestions.append({
                    "type": "automation_opportunity",
                    "title": f"Create reusable solution for {name}",
                    "reason": f"Seen {count} times in {domain} work.",
                    "confidence": min(0.99, 0.55 + (count * 0.08)),
                    "timestamp": now_iso(),
                })
        for item in suggestions:
            append_record(self.log_path, item)
        return suggestions

    def suggest_from_memory(self) -> List[Dict[str, Any]]:
        learning = load_json("data/learning_memory.json", [])
        if isinstance(learning, dict):
            candidates = learning.get("patterns", []) or learning.get("records", []) or []
        elif isinstance(learning, list):
            candidates = learning
        else:
            candidates = []
        return self.inspect_patterns(candidates)
