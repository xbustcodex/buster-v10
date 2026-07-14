from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .experience import ExperienceRecord
from .patterns import DesignPatternStore
from .strategies import BuildStrategyStore


class LearningEngine:
    """Central learning loop for Buster AI OS.

    Records completed work, extracts reusable patterns, updates strategy scores,
    and recommends better approaches for the next project.
    """

    def __init__(
        self,
        memory_path: str | Path = "data/learning_memory.json",
        strategies_path: str | Path = "data/build_strategies.json",
        patterns_path: str | Path = "data/design_patterns.json",
    ) -> None:
        self.memory_path = Path(memory_path)
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.strategy_store = BuildStrategyStore(strategies_path)
        self.pattern_store = DesignPatternStore(patterns_path)
        self.records: List[ExperienceRecord] = self._load_records()

    def _load_records(self) -> List[ExperienceRecord]:
        if not self.memory_path.exists():
            return []
        try:
            raw = json.loads(self.memory_path.read_text(encoding="utf-8"))
            items = raw if isinstance(raw, list) else raw.get("records", [])
            return [ExperienceRecord.from_dict(item) for item in items]
        except Exception:
            return []

    def save(self) -> None:
        self.memory_path.write_text(
            json.dumps([record.to_dict() for record in self.records], indent=2),
            encoding="utf-8",
        )

    def record_experience(self, record: ExperienceRecord | Dict[str, Any]) -> ExperienceRecord:
        if isinstance(record, dict):
            record = ExperienceRecord.from_dict(record)
        self.records.append(record)
        self.strategy_store.record_result(record.strategy, record.outcome == "success")

        for pattern in record.reusable_patterns:
            self.pattern_store.add_pattern(
                name=pattern[:80],
                description=pattern,
                project_type=record.project,
                tags=record.tags,
                source=record.id,
            )

        self.save()
        return record

    def learn_from_job(
        self,
        task: str,
        project: str,
        success: bool,
        strategy: str,
        what_worked: Optional[List[str]] = None,
        what_failed: Optional[List[str]] = None,
        fixes: Optional[List[str]] = None,
        reusable_patterns: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExperienceRecord:
        record = ExperienceRecord(
            task=task,
            project=project,
            outcome="success" if success else "failure",
            strategy=strategy,
            what_worked=what_worked or [],
            what_failed=what_failed or [],
            fixes=fixes or [],
            reusable_patterns=reusable_patterns or [],
            tags=tags or [],
            score=1.0 if success else 0.0,
            metadata=metadata or {},
        )
        return self.record_experience(record)

    def recommend_strategy(self, project_type: str = "general", request: str = "") -> Dict[str, Any]:
        strategy = self.strategy_store.recommend(project_type, request)
        patterns = self.pattern_store.search(request, project_type=project_type)[:5]
        similar = self.search_experience(request, project=project_type)[:5]
        return {
            "strategy": strategy,
            "patterns": patterns,
            "similar_experiences": [item.to_dict() for item in similar],
        }

    def search_experience(self, query: str = "", project: Optional[str] = None) -> List[ExperienceRecord]:
        query_l = query.lower().strip()
        results: List[ExperienceRecord] = []
        for record in self.records:
            blob = " ".join([
                record.task,
                record.project,
                record.strategy,
                " ".join(record.what_worked),
                " ".join(record.what_failed),
                " ".join(record.fixes),
                " ".join(record.reusable_patterns),
                " ".join(record.tags),
            ]).lower()
            if project and record.project not in (project, "general"):
                continue
            if not query_l or query_l in blob:
                results.append(record)
        return list(reversed(results))

    def summary(self) -> Dict[str, Any]:
        successes = sum(1 for record in self.records if record.outcome == "success")
        failures = sum(1 for record in self.records if record.outcome == "failure")
        return {
            "records": len(self.records),
            "successes": successes,
            "failures": failures,
            "strategies": len(self.strategy_store.strategies),
            "patterns": len(self.pattern_store.patterns),
        }
