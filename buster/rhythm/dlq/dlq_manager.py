from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from buster.rhythm.dlq.models import DeadLetterItem, DLQStatus, RecoveryStrategy
from buster.rhythm.rhythm import BusterRhythm, LifeState


class RhythmDLQManager:
    """Manages Dead Letter Queue items and evaluates recovery execution against current Rhythm states."""

    def __init__(
        self,
        rhythm: BusterRhythm,
        storage_path: Optional[Path] = None,
        event_bus: Optional[Any] = None,
    ) -> None:
        self.rhythm = rhythm
        self.storage_path = storage_path
        self.event_bus = event_bus
        self.items: Dict[str, DeadLetterItem] = {}
        if storage_path and storage_path.exists():
            self._load_from_disk()

    def enqueue(
        self,
        task_id: str,
        task_name: str,
        payload: Dict[str, Any],
        error: Exception | str,
        recovery_strategy: Optional[RecoveryStrategy] = None,
        max_attempts: int = 3,
    ) -> DeadLetterItem:
        """Adds a failed task to the DLQ and determines its initial recovery strategy."""
        err_msg = str(error)
        err_type = type(error).__name__ if isinstance(error, Exception) else "UnknownError"

        # Determine strategy if not explicitly supplied
        if not recovery_strategy:
            if payload.get("execution_class") == "foreground" or payload.get("priority") == "high":
                recovery_strategy = RecoveryStrategy.IMMEDIATE
            elif payload.get("experimental") or payload.get("self_improvement"):
                recovery_strategy = RecoveryStrategy.DREAM_SANDBOX
            else:
                recovery_strategy = RecoveryStrategy.NEXT_WORK_CYCLE

        item = DeadLetterItem(
            task_id=task_id,
            task_name=task_name,
            payload=payload,
            error_message=err_msg,
            error_type=err_type,
            max_attempts=max_attempts,
            recovery_strategy=recovery_strategy,
        )

        self.items[item.item_id] = item
        self._save_to_disk()

        if self.event_bus and hasattr(self.event_bus, "publish"):
            self.event_bus.publish(
                "dlq.item_enqueued",
                item.to_dict(),
                source="rhythm_dlq_manager",
            )

        return item

    def list_items(self) -> List[DeadLetterItem]:
        """Returns all managed Dead Letter Queue items."""
        return list(self.items.values())

    def get_ready_items(self, now: Optional[datetime] = None) -> List[DeadLetterItem]:
        """Returns items in the DLQ that are eligible for recovery right now given the current Rhythm state."""
        rhythm_status = self.rhythm.get_blackboard_status(now)
        current_state = LifeState(rhythm_status["life_state"])
        ready: List[DeadLetterItem] = []

        for item in self.items.values():
            if item.status not in (DLQStatus.PENDING, DLQStatus.SCHEDULED):
                continue

            if item.attempts >= item.max_attempts:
                item.status = DLQStatus.EXHAUSTED
                continue

            # Check strategy eligibility
            if item.recovery_strategy == RecoveryStrategy.IMMEDIATE:
                ready.append(item)

            elif item.recovery_strategy == RecoveryStrategy.NEXT_WORK_CYCLE:
                if current_state == LifeState.WORK:
                    ready.append(item)

            elif item.recovery_strategy == RecoveryStrategy.DREAM_SANDBOX:
                if current_state == LifeState.SLEEP and rhythm_status.get("dream_sandbox_active"):
                    ready.append(item)

        return ready

    def mark_resolved(self, item_id: str) -> None:
        if item_id in self.items:
            self.items[item_id].status = DLQStatus.RESOLVED
            self._save_to_disk()

    def mark_failed(self, item_id: str, new_error: str) -> None:
        if item_id in self.items:
            item = self.items[item_id]
            item.attempts += 1
            item.error_message = new_error
            if item.attempts >= item.max_attempts:
                item.status = DLQStatus.EXHAUSTED
            else:
                item.status = DLQStatus.PENDING
            self._save_to_disk()

    def status(self) -> Dict[str, Any]:
        """Return the current DLQ status summary."""
        items = self.list_items()
        return {
            "total_items": len(items),
            "pending_items": len([i for i in items if i.status in (DLQStatus.PENDING, DLQStatus.SCHEDULED)]),
            "resolved_items": len([i for i in items if i.status == DLQStatus.RESOLVED]),
            "exhausted_items": len([i for i in items if i.status == DLQStatus.EXHAUSTED]),
            "storage_path": str(self.storage_path) if self.storage_path else None,
        }

    def _save_to_disk(self) -> None:
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = [item.to_dict() for item in self.items.values()]
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_from_disk(self) -> None:
        if not self.storage_path or not self.storage_path.exists():
            return
        try:
            raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
            for entry in raw:
                item = DeadLetterItem(
                    item_id=entry["item_id"],
                    task_id=entry["task_id"],
                    task_name=entry["task_name"],
                    payload=entry["payload"],
                    error_message=entry["error_message"],
                    error_type=entry["error_type"],
                    failed_at=entry["failed_at"],
                    attempts=entry["attempts"],
                    max_attempts=entry["max_attempts"],
                    status=DLQStatus(entry["status"]),
                    recovery_strategy=RecoveryStrategy(entry["recovery_strategy"]),
                    scheduled_for=entry.get("scheduled_for"),
                )
                self.items[item.item_id] = item
        except Exception:
            pass