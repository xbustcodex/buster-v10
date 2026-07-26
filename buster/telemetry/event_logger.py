from __future__ import annotations

import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from buster.telemetry.trace_context import TraceContext


class EventLogger:
    """Appends structured JSON events to execution and failure .jsonl files."""

    def __init__(
        self,
        log_dir: str = "data",
        events_filename: str = "execution_events.jsonl",
        failures_filename: str = "failure_events.jsonl",
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.log_dir / events_filename
        self.failures_path = self.log_dir / failures_filename

    def log_event(
        self,
        event_type: str,
        component: str,
        status: str = "info",
        duration_ms: float = 0.0,
        attempt: int = 1,
        failure_category: Optional[str] = None,
        retryable: Optional[bool] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Constructs and persists a structured telemetry event."""
        ctx = TraceContext.get_context()
        now_str = datetime.now(timezone.utc).isoformat()

        event_payload = {
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "timestamp": now_str,
            "trace_id": ctx["trace_id"],
            "task_id": ctx["task_id"],
            "parent_task_id": ctx["parent_task_id"],
            "agent_id": ctx["agent_id"],
            "component": component,
            "event_type": event_type,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "attempt": attempt,
            "failure_category": failure_category,
            "retryable": retryable,
        }

        if extra:
            event_payload["extra"] = extra

        self._append_jsonl(self.events_path, event_payload)

        # Mirror failure-related events to failure_events.jsonl for fast debugging queries
        if status in {"failed", "error"} or failure_category is not None:
            self._append_jsonl(self.failures_path, event_payload)

        return event_payload

    def _append_jsonl(self, path: Path, payload: Dict[str, Any]) -> None:
        """Appends a single JSON record safely as a new line."""
        line = json.dumps(payload) + "\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)