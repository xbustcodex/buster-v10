from __future__ import annotations
from buster.utils.datetime_utils import utc_now, utc_timestamp
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, List
import uuid

def _now() -> str:
    return utc_timestamp()

@dataclass
class ExperienceRecord:
    """A durable record of an engineering outcome."""
    id: str
    timestamp: str
    project: str
    project_type: str
    task: str
    strategy: str
    outcome: str
    confidence: float = 0.5
    risk: str = "medium"
    tools: List[str] = field(default_factory=list)
    agents: List[str] = field(default_factory=list)
    plugins: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    fixes: List[str] = field(default_factory=list)
    design_choices: List[str] = field(default_factory=list)
    user_feedback: str = ""
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.outcome.lower() in {"success", "passed", "fixed", "accepted", "completed"}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperienceRecord":
        return cls(
            id=data.get("id") or str(uuid.uuid4()),
            timestamp=data.get("timestamp") or _now(),
            project=data.get("project", "default"),
            project_type=data.get("project_type", "general"),
            task=data.get("task", "unknown"),
            strategy=data.get("strategy", "default"),
            outcome=data.get("outcome", "unknown"),
            confidence=float(data.get("confidence", 0.5)),
            risk=data.get("risk", "medium"),
            tools=list(data.get("tools", [])),
            agents=list(data.get("agents", [])),
            plugins=list(data.get("plugins", [])),
            errors=list(data.get("errors", [])),
            fixes=list(data.get("fixes", [])),
            design_choices=list(data.get("design_choices", [])),
            user_feedback=data.get("user_feedback", ""),
            notes=data.get("notes", ""),
            metadata=dict(data.get("metadata", {})),
        )

def make_experience_record(project: str, project_type: str, task: str, strategy: str, outcome: str, **kwargs: Any) -> ExperienceRecord:
    return ExperienceRecord(id=str(uuid.uuid4()), timestamp=_now(), project=project, project_type=project_type, task=task, strategy=strategy, outcome=outcome, **kwargs)
