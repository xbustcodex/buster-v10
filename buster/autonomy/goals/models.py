from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from buster.utils.datetime_utils import utc_now


@dataclass
class CuriositySignal:
    signal_type: str
    target: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    signal_id: str = field(default_factory=lambda: f"sig_{uuid.uuid4().hex[:8]}")
    created_at: str = field(default_factory=utc_now)


@dataclass
class GoalProposal:
    title: str
    request: str
    target: str
    signal_id: str
    id: str = field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:8]}")
    project_type: str = "general"
    created_at: str = field(default_factory=utc_now)


@dataclass
class GoalEvaluation:
    goal_id: str
    value_score: float
    risk_score: float
    cost_score: float
    confidence: float
    is_approved: bool
    reason: str


@dataclass
class GoalExecutionResult:
    goal_id: str
    success: bool
    output: Dict[str, Any] = field(default_factory=dict)