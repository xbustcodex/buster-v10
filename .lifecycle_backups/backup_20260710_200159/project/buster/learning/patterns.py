from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class DesignPatternStore:
    """Stores reusable project and code design patterns."""

    def __init__(self, path: str | Path = "data/design_patterns.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.patterns: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else data.get("patterns", [])
        except Exception:
            return []

    def save(self) -> None:
        self.path.write_text(json.dumps(self.patterns, indent=2), encoding="utf-8")

    def add_pattern(
        self,
        name: str,
        description: str,
        project_type: str = "general",
        tags: Optional[List[str]] = None,
        source: str = "learning",
    ) -> Dict[str, Any]:
        pattern = {
            "name": name,
            "description": description,
            "project_type": project_type,
            "tags": tags or [],
            "source": source,
            "uses": 0,
        }
        self.patterns.append(pattern)
        self.save()
        return pattern

    def search(self, query: str = "", project_type: Optional[str] = None) -> List[Dict[str, Any]]:
        query_l = query.lower().strip()
        results = []
        for pattern in self.patterns:
            blob = " ".join([
                pattern.get("name", ""),
                pattern.get("description", ""),
                " ".join(pattern.get("tags", [])),
                pattern.get("project_type", ""),
            ]).lower()
            if project_type and pattern.get("project_type") not in (project_type, "general"):
                continue
            if not query_l or query_l in blob:
                results.append(pattern)
        return results
