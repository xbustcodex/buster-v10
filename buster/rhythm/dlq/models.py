from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class DLQStatus(str, Enum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    RECOVERING = "RECOVERING"
    RESOLVED = "RESOLVED"
    EXHAUSTED = "EXHAUSTED"


class RecoveryStrategy(str, Enum):
    IMMEDIATE = "IMMEDIATE"            # High-priority user tasks
    NEXT_WORK_CYCLE = "NEXT_WORK_CYCLE"# Heavy code repairs
    DREAM_SANDBOX = "DREAM_SANDBOX"    # Experimental/self-improvement fixes
    DEFERRED = "DEFERRED"              # Wait for manual intervention or specific state


@dataclass
class DeadLetterItem:
    task_id: str
    task_name: str
    payload: Dict[str, Any]
    error_message: str
    error_type: str
    failed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    attempts: int = 1
    max_attempts: int = 3
    status: DLQStatus = DLQStatus.PENDING
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.NEXT_WORK_CYCLE
    scheduled_for: Optional[str] = None
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "payload": self.payload,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "failed_at": self.failed_at,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "status": self.status.value,
            "recovery_strategy": self.recovery_strategy.value,
            "scheduled_for": self.scheduled_for,
        }