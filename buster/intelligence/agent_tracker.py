"""Agent activity tracking for Buster Desktop AI OS.

This module tracks the current and historical state of Buster agents without
depending on Qt or a specific runtime implementation. Runtime events can be
forwarded directly to ``AgentTracker.handle_event()``.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import RLock
from time import monotonic
from typing import Any, Deque, Mapping


@dataclass(slots=True)
class AgentState:
    """Mutable state for one runtime agent."""

    agent_id: str
    name: str
    status: str = "idle"
    current_task: str = ""
    last_task: str = ""
    last_message: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    updated_at: str | None = None
    duration_seconds: float | None = None
    tasks_started: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable copy of the state."""

        return asdict(self)


@dataclass(frozen=True, slots=True)
class AgentActivity:
    """One normalized agent activity entry."""

    agent_id: str
    agent_name: str
    action: str
    status: str
    timestamp: str
    task: str
    message: str
    duration_seconds: float | None
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation."""

        return asdict(self)


class AgentTracker:
    """Thread-safe tracker for agent lifecycle and task activity."""

    VALID_STATUSES = {
        "unknown",
        "idle",
        "queued",
        "planning",
        "running",
        "waiting",
        "paused",
        "complete",
        "failed",
        "stopped",
    }

    ACTIVE_STATUSES = {"queued", "planning", "running", "waiting", "paused"}

    def __init__(self, max_history: int = 500) -> None:
        if max_history < 1:
            raise ValueError("max_history must be greater than zero")

        self._agents: dict[str, AgentState] = {}
        self._history: Deque[AgentActivity] = deque(maxlen=max_history)
        self._status_counts: Counter[str] = Counter()
        self._task_started_at: dict[str, float] = {}
        self._lock = RLock()
        self._max_history = max_history

    @property
    def max_history(self) -> int:
        return self._max_history

    def register_agent(
        self,
        agent_id: str,
        *,
        name: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> AgentState:
        """Register an agent or update its descriptive information."""

        normalized_id = self._normalize_agent_id(agent_id)
        normalized_name = str(name or normalized_id).strip() or normalized_id

        with self._lock:
            state = self._agents.get(normalized_id)
            if state is None:
                state = AgentState(
                    agent_id=normalized_id,
                    name=normalized_name,
                    updated_at=self._utc_now(),
                    metadata=dict(metadata or {}),
                )
                self._agents[normalized_id] = state
            else:
                state.name = normalized_name
                state.updated_at = self._utc_now()
                if metadata:
                    state.metadata.update(dict(metadata))

            return self._copy_state(state)

    def start_task(
        self,
        agent_id: str,
        task: str,
        *,
        name: str | None = None,
        status: str = "running",
        message: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> AgentState:
        """Mark an agent as starting work on a task."""

        normalized_id = self._normalize_agent_id(agent_id)
        normalized_status = self._normalize_status(status)
        now = self._utc_now()

        with self._lock:
            state = self._get_or_create_locked(normalized_id, name)
            self._replace_status_count_locked(state.status, normalized_status)

            state.status = normalized_status
            state.current_task = str(task or "").strip()
            state.last_message = str(message or "").strip()
            state.started_at = now
            state.completed_at = None
            state.duration_seconds = None
            state.updated_at = now
            state.tasks_started += 1

            if metadata:
                state.metadata.update(dict(metadata))

            self._task_started_at[normalized_id] = monotonic()
            self._append_activity_locked(
                state,
                action="task.started",
                task=state.current_task,
                message=state.last_message,
                duration_seconds=None,
                metadata=metadata,
            )

            return self._copy_state(state)

    def update_status(
        self,
        agent_id: str,
        status: str,
        *,
        task: str | None = None,
        name: str | None = None,
        message: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> AgentState:
        """Update an agent without completing its current task."""

        normalized_id = self._normalize_agent_id(agent_id)
        normalized_status = self._normalize_status(status)

        with self._lock:
            state = self._get_or_create_locked(normalized_id, name)
            self._replace_status_count_locked(state.status, normalized_status)

            state.status = normalized_status
            if task is not None:
                state.current_task = str(task).strip()
            if message:
                state.last_message = str(message).strip()
            if metadata:
                state.metadata.update(dict(metadata))
            state.updated_at = self._utc_now()

            self._append_activity_locked(
                state,
                action="status.updated",
                task=state.current_task,
                message=state.last_message,
                duration_seconds=state.duration_seconds,
                metadata=metadata,
            )

            return self._copy_state(state)

    def complete_task(
        self,
        agent_id: str,
        *,
        message: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> AgentState:
        """Mark the current agent task as complete."""

        return self._finish_task(
            agent_id,
            status="complete",
            action="task.completed",
            message=message,
            metadata=metadata,
        )

    def fail_task(
        self,
        agent_id: str,
        *,
        message: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> AgentState:
        """Mark the current agent task as failed."""

        return self._finish_task(
            agent_id,
            status="failed",
            action="task.failed",
            message=message,
            metadata=metadata,
        )

    def set_idle(self, agent_id: str, *, message: str = "") -> AgentState:
        """Return an agent to idle without changing task counters."""

        normalized_id = self._normalize_agent_id(agent_id)

        with self._lock:
            state = self._get_or_create_locked(normalized_id)
            self._replace_status_count_locked(state.status, "idle")

            state.status = "idle"
            state.current_task = ""
            state.last_message = str(message or "").strip()
            state.updated_at = self._utc_now()
            self._task_started_at.pop(normalized_id, None)

            self._append_activity_locked(
                state,
                action="agent.idle",
                task="",
                message=state.last_message,
                duration_seconds=state.duration_seconds,
                metadata=None,
            )

            return self._copy_state(state)

    def handle_event(self, event: Any) -> AgentState | None:
        """Update agent state from a dispatcher event.

        Common supported event names:

        - ``agent.started``
        - ``agent.running``
        - ``agent.progress``
        - ``agent.completed``
        - ``agent.failed``
        - ``agent.idle``
        """

        event_type = str(
            self._read_field(event, "event_type", "type", "name") or ""
        ).strip().lower()

        if "agent" not in event_type:
            return None

        payload = self._read_field(event, "payload", "data", "details")
        if not isinstance(payload, Mapping):
            payload = {}

        agent_id = (
            self._read_field(event, "agent_id", "agent", "source")
            or payload.get("agent_id")
            or payload.get("agent")
        )
        if not agent_id:
            return None

        name = (
            self._read_field(event, "agent_name", "name")
            or payload.get("agent_name")
            or payload.get("name")
        )
        task = (
            self._read_field(event, "task", "request")
            or payload.get("task")
            or payload.get("request")
            or ""
        )
        message = (
            self._read_field(event, "message", "description", "summary")
            or payload.get("message")
            or ""
        )
        status = (
            self._read_field(event, "status", "state")
            or payload.get("status")
            or ""
        )

        if event_type.endswith((".started", ".running")):
            return self.start_task(
                str(agent_id),
                str(task),
                name=str(name) if name else None,
                status=str(status or "running"),
                message=str(message),
                metadata=payload,
            )

        if event_type.endswith((".completed", ".complete", ".success")):
            return self.complete_task(
                str(agent_id),
                message=str(message),
                metadata=payload,
            )

        if event_type.endswith((".failed", ".error")):
            return self.fail_task(
                str(agent_id),
                message=str(message),
                metadata=payload,
            )

        if event_type.endswith(".idle"):
            return self.set_idle(str(agent_id), message=str(message))

        return self.update_status(
            str(agent_id),
            str(status or "running"),
            task=str(task) if task else None,
            name=str(name) if name else None,
            message=str(message),
            metadata=payload,
        )

    def get(self, agent_id: str) -> AgentState | None:
        """Return one agent state."""

        normalized_id = self._normalize_agent_id(agent_id)
        with self._lock:
            state = self._agents.get(normalized_id)
            return self._copy_state(state) if state else None

    def all_agents(self) -> list[AgentState]:
        """Return all agent states ordered by display name."""

        with self._lock:
            states = [self._copy_state(state) for state in self._agents.values()]

        return sorted(states, key=lambda item: item.name.lower())

    def active_agents(self) -> list[AgentState]:
        """Return agents currently doing or awaiting work."""

        return [
            state
            for state in self.all_agents()
            if state.status in self.ACTIVE_STATUSES
        ]

    def recent_activity(self, limit: int = 50) -> list[AgentActivity]:
        """Return newest activity entries first."""

        if limit < 1:
            return []

        with self._lock:
            return list(reversed(tuple(self._history)))[0:limit]

    def snapshot(self, history_limit: int = 50) -> dict[str, Any]:
        """Return a serializable snapshot for Mission Control."""

        with self._lock:
            states = [self._copy_state(state) for state in self._agents.values()]
            history = list(self._history)
            status_counts = Counter(state.status for state in states)

        return {
            "total_agents": len(states),
            "active_agents": sum(
                1 for state in states if state.status in self.ACTIVE_STATUSES
            ),
            "status_counts": dict(status_counts),
            "agents": [
                state.to_dict()
                for state in sorted(states, key=lambda item: item.name.lower())
            ],
            "recent_activity": [
                item.to_dict()
                for item in history[-max(0, history_limit):]
            ],
        }

    def clear_history(self) -> None:
        """Clear activity history while retaining current agent states."""

        with self._lock:
            self._history.clear()

    def reset(self) -> None:
        """Clear all agent state and history."""

        with self._lock:
            self._agents.clear()
            self._history.clear()
            self._status_counts.clear()
            self._task_started_at.clear()

    def _finish_task(
        self,
        agent_id: str,
        *,
        status: str,
        action: str,
        message: str,
        metadata: Mapping[str, Any] | None,
    ) -> AgentState:
        normalized_id = self._normalize_agent_id(agent_id)
        now = self._utc_now()

        with self._lock:
            state = self._get_or_create_locked(normalized_id)
            duration = self._duration_for_locked(normalized_id)

            self._replace_status_count_locked(state.status, status)
            state.status = status
            state.last_task = state.current_task
            state.current_task = ""
            state.last_message = str(message or "").strip()
            state.completed_at = now
            state.updated_at = now
            state.duration_seconds = duration

            if status == "complete":
                state.tasks_completed += 1
            else:
                state.tasks_failed += 1

            if metadata:
                state.metadata.update(dict(metadata))

            self._append_activity_locked(
                state,
                action=action,
                task=state.last_task,
                message=state.last_message,
                duration_seconds=duration,
                metadata=metadata,
            )

            return self._copy_state(state)

    def _get_or_create_locked(
        self,
        agent_id: str,
        name: str | None = None,
    ) -> AgentState:
        state = self._agents.get(agent_id)
        if state is not None:
            if name:
                state.name = str(name).strip() or state.name
            return state

        state = AgentState(
            agent_id=agent_id,
            name=str(name or agent_id).strip() or agent_id,
            updated_at=self._utc_now(),
        )
        self._agents[agent_id] = state
        self._status_counts[state.status] += 1
        return state

    def _append_activity_locked(
        self,
        state: AgentState,
        *,
        action: str,
        task: str,
        message: str,
        duration_seconds: float | None,
        metadata: Mapping[str, Any] | None,
    ) -> None:
        self._history.append(
            AgentActivity(
                agent_id=state.agent_id,
                agent_name=state.name,
                action=action,
                status=state.status,
                timestamp=self._utc_now(),
                task=task,
                message=message,
                duration_seconds=duration_seconds,
                metadata=dict(metadata or {}),
            )
        )

    def _duration_for_locked(self, agent_id: str) -> float | None:
        started = self._task_started_at.pop(agent_id, None)
        if started is None:
            return None
        return round(max(0.0, monotonic() - started), 3)

    def _replace_status_count_locked(self, old: str, new: str) -> None:
        if old == new:
            return

        if self._status_counts[old] > 0:
            self._status_counts[old] -= 1
        self._status_counts[new] += 1

    @classmethod
    def _normalize_status(cls, status: str) -> str:
        normalized = str(status or "unknown").strip().lower()
        aliases = {
            "completed": "complete",
            "success": "complete",
            "successful": "complete",
            "error": "failed",
            "errored": "failed",
            "active": "running",
            "working": "running",
            "pending": "queued",
        }
        normalized = aliases.get(normalized, normalized)
        return normalized if normalized in cls.VALID_STATUSES else "unknown"

    @staticmethod
    def _normalize_agent_id(agent_id: str) -> str:
        normalized = str(agent_id or "").strip()
        if not normalized:
            raise ValueError("agent_id cannot be empty")
        return normalized

    @staticmethod
    def _copy_state(state: AgentState) -> AgentState:
        return AgentState(
            agent_id=state.agent_id,
            name=state.name,
            status=state.status,
            current_task=state.current_task,
            last_task=state.last_task,
            last_message=state.last_message,
            started_at=state.started_at,
            completed_at=state.completed_at,
            updated_at=state.updated_at,
            duration_seconds=state.duration_seconds,
            tasks_started=state.tasks_started,
            tasks_completed=state.tasks_completed,
            tasks_failed=state.tasks_failed,
            metadata=dict(state.metadata),
        )

    @staticmethod
    def _read_field(event: Any, *names: str) -> Any:
        if isinstance(event, Mapping):
            for name in names:
                if name in event:
                    return event[name]
            return None

        for name in names:
            if hasattr(event, name):
                return getattr(event, name)

        return None

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
