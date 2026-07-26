from __future__ import annotations

import uuid
import contextvars
from typing import Optional, Dict, Any

_TRACE_ID: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_TASK_ID: contextvars.ContextVar[str] = contextvars.ContextVar("task_id", default="")
_PARENT_TASK_ID: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("parent_task_id", default=None)
_AGENT_ID: contextvars.ContextVar[str] = contextvars.ContextVar("agent_id", default="main-agent")


class TraceContext:
    """Manages context-local correlation keys (trace_id, task_id, parent_task_id, agent_id)."""

    @staticmethod
    def start_trace(
        task_id: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        agent_id: str = "main-agent",
    ) -> str:
        """Initializes or rotates the active trace and sets context variables."""
        trace_id = f"trc_{uuid.uuid4().hex[:12]}"
        _TRACE_ID.set(trace_id)
        _TASK_ID.set(task_id or f"tsk_{uuid.uuid4().hex[:8]}")
        _PARENT_TASK_ID.set(parent_task_id)
        _AGENT_ID.set(agent_id)
        return trace_id

    @staticmethod
    def get_context() -> Dict[str, Any]:
        """Returns current context metadata dictionary."""
        trace_id = _TRACE_ID.get()
        if not trace_id:
            trace_id = f"trc_{uuid.uuid4().hex[:12]}"
            _TRACE_ID.set(trace_id)

        task_id = _TASK_ID.get()
        if not task_id:
            task_id = f"tsk_{uuid.uuid4().hex[:8]}"
            _TASK_ID.set(task_id)

        return {
            "trace_id": trace_id,
            "task_id": task_id,
            "parent_task_id": _PARENT_TASK_ID.get(),
            "agent_id": _AGENT_ID.get(),
        }