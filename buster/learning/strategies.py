from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class BuildStrategyStore:
    """Tracks build strategies and recommends the best one for a request."""

    def __init__(self, path: str | Path = "data/build_strategies.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.strategies: List[Dict[str, Any]] = self._load()
        if not self.strategies:
            self._seed_defaults()

    def _load(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else data.get("strategies", [])
        except Exception:
            return []

    def save(self) -> None:
        self.path.write_text(json.dumps(self.strategies, indent=2), encoding="utf-8")

    def _seed_defaults(self) -> None:
        self.strategies = [
            {
                "name": "plan_build_test_fix_verify",
                "description": "Plan first, build files, run tests, fix errors, verify result.",
                "project_types": ["python", "desktop", "general"],
                "successes": 0,
                "failures": 0,
                "score": 0.75,
            },
            {
                "name": "small_incremental_patch",
                "description": "Apply a small safe patch, then test immediately.",
                "project_types": ["existing_project", "bugfix", "general"],
                "successes": 0,
                "failures": 0,
                "score": 0.70,
            },
            {
                "name": "modular_plugin_expansion",
                "description": "Add new capability as a module or plugin instead of growing main.py.",
                "project_types": ["buster", "plugin", "ai_os"],
                "successes": 0,
                "failures": 0,
                "score": 0.85,
            },
        ]
        self.save()

    def record_result(self, name: str, success: bool) -> None:
        strategy = self.get(name)
        if strategy is None:
            strategy = {
                "name": name,
                "description": "Learned strategy",
                "project_types": ["general"],
                "successes": 0,
                "failures": 0,
                "score": 0.50,
            }
            self.strategies.append(strategy)

        if success:
            strategy["successes"] = strategy.get("successes", 0) + 1
        else:
            strategy["failures"] = strategy.get("failures", 0) + 1

        total = strategy.get("successes", 0) + strategy.get("failures", 0)
        if total:
            strategy["score"] = round(strategy.get("successes", 0) / total, 3)
        self.save()

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        for strategy in self.strategies:
            if strategy.get("name") == name:
                return strategy
        return None

    def recommend(self, project_type: str = "general", query: str = "") -> Dict[str, Any]:
        query_l = query.lower()
        candidates = []
        for strategy in self.strategies:
            types = strategy.get("project_types", [])
            blob = (strategy.get("name", "") + " " + strategy.get("description", "")).lower()
            type_match = project_type in types or "general" in types
            text_bonus = 0.1 if query_l and query_l in blob else 0.0
            if type_match or text_bonus:
                score = float(strategy.get("score", 0.0)) + text_bonus
                candidates.append((score, strategy))
        if not candidates:
            return self.strategies[0]
        return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]
