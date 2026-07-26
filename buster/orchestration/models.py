# buster/orchestration/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, FrozenSet


@dataclass(frozen=True)
class TaskDependency:
    task_id: str


@dataclass
class MissionTask:
    task_id: str
    capability_id: str
    action: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    required_permissions: FrozenSet[str] = field(default_factory=frozenset)
    risk_level: str = "low"
    max_retries: int = 2


@dataclass
class MissionPlan:
    mission_id: str
    goal: str
    tasks: List[MissionTask] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: 0.0)

    def add_task(self, task: MissionTask) -> None:
        self.tasks.append(task)

    def get_task(self, task_id: str) -> Optional[MissionTask]:
        for t in self.tasks:
            if t.task_id == task_id:
                return t
        return None