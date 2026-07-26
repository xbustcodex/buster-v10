# buster/autonomy/mission_state.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class AutonomyPolicy:
    level: int  # 0 to 4
    allow_file_writes: bool
    allow_shell_commands: bool
    allow_network_access: bool
    allow_process_control: bool
    allow_self_patch: bool
    require_approval_for_merge: bool
    maximum_runtime_minutes: int
    maximum_child_tasks: int


@dataclass
class Mission:
    mission_id: str
    objective: str
    status: str  # CREATED, CONTEXTUALIZING, PLANNING, EXECUTING, VERIFYING, RECOVERING, WAITING, PAUSED, BLOCKED, COMPLETED, FAILED, CANCELLED
    priority: int
    created_at: str

    current_stage: str
    root_task_id: Optional[str] = None
    active_task_ids: List[str] = field(default_factory=list)
    completed_task_ids: List[str] = field(default_factory=list)
    failed_task_ids: List[str] = field(default_factory=list)

    success_criteria: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    approved_capabilities: List[str] = field(default_factory=list)

    checkpoint_id: Optional[str] = None
    trace_id: Optional[str] = None
    intervention_required: bool = False
    autonomy_policy: Optional[AutonomyPolicy] = None