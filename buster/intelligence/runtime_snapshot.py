"""Aggregated runtime snapshots for Buster Desktop AI OS.

This module combines the existing runtime core, dispatcher, runtime monitor,
agent tracker, agent memory, jobs, services, registry, blackboard, and state
store into one Mission Control-friendly snapshot.

It does not own runtime state. It only reads and normalizes state from the
objects already managed by Buster.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class RuntimeHealthSummary:
    """Compact health information for Mission Control."""

    overall: str
    runtime: str
    dispatcher: str
    agents: str
    jobs: str
    memory: str
    services: str
    warnings: tuple[str, ...]
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RuntimeSnapshot:
    """Build serializable snapshots from the current Buster runtime."""

    def __init__(
        self,
        runtime_core: Any,
        *,
        runtime_monitor: Any | None = None,
        agent_tracker: Any | None = None,
    ) -> None:
        if runtime_core is None:
            raise ValueError("runtime_core is required")

        self.runtime_core = runtime_core
        self.runtime_monitor = runtime_monitor
        self.agent_tracker = agent_tracker

    def capture(
        self,
        *,
        event_limit: int = 50,
        activity_limit: int = 50,
    ) -> dict[str, Any]:
        """Capture a complete Mission Control snapshot."""

        core_status = self._safe_call(
            self.runtime_core,
            "status",
            default={},
        )

        runtime_state = self._runtime_section(core_status)
        dispatcher_state = self._dispatcher_section(core_status)
        agents_state = self._agents_section(core_status, activity_limit)
        jobs_state = self._jobs_section(core_status)
        memory_state = self._memory_section(core_status)
        blackboard_state = self._blackboard_section(core_status)
        services_state = self._services_section(core_status)
        registry_state = self._registry_section(core_status)
        event_state = self._events_section(core_status, event_limit)
        state_store = self._state_store_section(core_status)

        health = self._build_health_summary(
            runtime=runtime_state,
            dispatcher=dispatcher_state,
            agents=agents_state,
            jobs=jobs_state,
            memory=memory_state,
            services=services_state,
        )

        return {
            "captured_at": self._utc_now(),
            "root": str(
                getattr(self.runtime_core, "root", core_status.get("root", "."))
            ),
            "started": bool(
                getattr(
                    self.runtime_core,
                    "started",
                    core_status.get("started", False),
                )
            ),
            "health": health.to_dict(),
            "runtime": runtime_state,
            "dispatcher": dispatcher_state,
            "agents": agents_state,
            "jobs": jobs_state,
            "memory": memory_state,
            "blackboard": blackboard_state,
            "services": services_state,
            "registry": registry_state,
            "events": event_state,
            "state": state_store,
            "summary": self._build_summary(
                runtime=runtime_state,
                dispatcher=dispatcher_state,
                agents=agents_state,
                jobs=jobs_state,
                events=event_state,
                health=health,
            ),
        }

    def compact(self) -> dict[str, Any]:
        """Return a small snapshot suitable for a status sidebar."""

        full = self.capture(event_limit=5, activity_limit=5)

        return {
            "captured_at": full["captured_at"],
            "started": full["started"],
            "health": full["health"],
            "summary": full["summary"],
            "latest_events": full["events"].get("recent", []),
            "active_agents": full["agents"].get("active", []),
            "active_jobs": full["jobs"].get("active", []),
        }

    def _runtime_section(self, core_status: Mapping[str, Any]) -> dict[str, Any]:
        runtime = self._as_dict(core_status.get("runtime"))
        started = bool(
            getattr(
                self.runtime_core,
                "started",
                core_status.get("started", False),
            )
        )

        return {
            "started": started,
            "status": runtime.get(
                "status",
                "running" if started else "stopped",
            ),
            "details": runtime,
        }

    def _dispatcher_section(
        self,
        core_status: Mapping[str, Any],
    ) -> dict[str, Any]:
        dispatcher = getattr(self.runtime_core, "dispatcher", None)
        status = self._as_dict(core_status.get("dispatcher"))

        if dispatcher is not None:
            live_status = self._safe_call(dispatcher, "status", default={})
            if isinstance(live_status, Mapping):
                status.update(dict(live_status))

            statistics = self._safe_call(
                dispatcher,
                "statistics",
                default={},
            )
            history = self._safe_call(
                dispatcher,
                "history",
                default=[],
            )
        else:
            statistics = {}
            history = []

        return {
            "status": status,
            "statistics": self._as_dict(statistics),
            "history_count": len(history) if isinstance(history, list) else 0,
            "subscriber_count": self._count_subscribers(status),
        }

    def _agents_section(
        self,
        core_status: Mapping[str, Any],
        activity_limit: int,
    ) -> dict[str, Any]:
        base = self._as_dict(core_status.get("agents"))

        tracker_snapshot: dict[str, Any] = {}
        if self.agent_tracker is not None:
            snapshot = self._safe_call(
                self.agent_tracker,
                "snapshot",
                activity_limit,
                default={},
            )
            tracker_snapshot = self._as_dict(snapshot)

        agents = tracker_snapshot.get("agents", [])
        active = [
            item
            for item in agents
            if isinstance(item, Mapping)
            and item.get("status")
            in {"queued", "planning", "running", "waiting", "paused"}
        ]

        return {
            "runtime": base,
            "tracker": tracker_snapshot,
            "count": tracker_snapshot.get(
                "total_agents",
                self._infer_count(base),
            ),
            "active_count": tracker_snapshot.get(
                "active_agents",
                len(active),
            ),
            "active": active,
            "recent_activity": tracker_snapshot.get(
                "recent_activity",
                [],
            ),
        }

    def _jobs_section(self, core_status: Mapping[str, Any]) -> dict[str, Any]:
        jobs = self._as_dict(core_status.get("jobs"))

        items = jobs.get("jobs", [])
        if not isinstance(items, list):
            items = []

        active = []
        for item in items:
            if not isinstance(item, Mapping):
                continue

            status = str(item.get("status", "")).lower()
            if status in {"queued", "pending", "running", "active"}:
                active.append(dict(item))

        counts = jobs.get("counts", {})
        if not isinstance(counts, Mapping):
            counts = {}

        return {
            "status": jobs,
            "count": jobs.get("count", len(items)),
            "counts": dict(counts),
            "active": active,
            "active_count": len(active),
        }

    def _memory_section(self, core_status: Mapping[str, Any]) -> dict[str, Any]:
        memory = self._as_dict(core_status.get("agent_memory"))

        if not memory:
            memory = self._as_dict(core_status.get("memory"))

        agent_profiles = memory.get("agents", {})
        memory_events = memory.get("events", [])

        return {
            "status": memory,
            "agent_profiles": (
                dict(agent_profiles)
                if isinstance(agent_profiles, Mapping)
                else {}
            ),
            "event_count": (
                len(memory_events)
                if isinstance(memory_events, list)
                else 0
            ),
            "recent_events": (
                memory_events[-20:]
                if isinstance(memory_events, list)
                else []
            ),
        }

    def _blackboard_section(
        self,
        core_status: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self._as_dict(core_status.get("blackboard"))

    def _services_section(
        self,
        core_status: Mapping[str, Any],
    ) -> dict[str, Any]:
        sdk_status = self._as_dict(core_status.get("sdk"))

        if not sdk_status:
            sdk = getattr(self.runtime_core, "sdk", None)
            sdk_status = self._as_dict(
                self._safe_call(sdk, "status", default={})
            )

        return {
            "sdk": sdk_status,
            "count": self._infer_count(sdk_status),
        }

    def _registry_section(
        self,
        core_status: Mapping[str, Any],
    ) -> dict[str, Any]:
        summary = self._as_dict(core_status.get("registry_summary"))

        registry = getattr(self.runtime_core, "registry", None)
        full_status = self._as_dict(
            self._safe_call(registry, "status", default={})
        )

        return {
            "summary": summary,
            "status": full_status,
            "count": self._infer_count(full_status or summary),
        }

    def _events_section(
        self,
        core_status: Mapping[str, Any],
        event_limit: int,
    ) -> dict[str, Any]:
        recent = core_status.get("recent_events", [])
        if not isinstance(recent, list):
            recent = []

        monitor_snapshot: dict[str, Any] = {}
        if self.runtime_monitor is not None:
            snapshot = self._safe_call(
                self.runtime_monitor,
                "snapshot",
                event_limit,
                default={},
            )
            monitor_snapshot = self._as_dict(snapshot)

        dispatcher = getattr(self.runtime_core, "dispatcher", None)
        dispatcher_history = self._safe_call(
            dispatcher,
            "history",
            default=[],
        )

        if not isinstance(dispatcher_history, list):
            dispatcher_history = []

        combined = self._merge_events(
            monitor_snapshot.get("events", []),
            dispatcher_history,
            recent,
            limit=event_limit,
        )

        return {
            "monitor": monitor_snapshot,
            "count": monitor_snapshot.get(
                "total_recorded",
                len(dispatcher_history),
            ),
            "recent": combined,
        }

    def _state_store_section(
        self,
        core_status: Mapping[str, Any],
    ) -> dict[str, Any]:
        state = self._as_dict(core_status.get("state"))

        if not state:
            state_store = getattr(self.runtime_core, "state", None)
            state = self._as_dict(
                self._safe_call(state_store, "snapshot", default={})
            )

        return state

    def _build_health_summary(
        self,
        *,
        runtime: Mapping[str, Any],
        dispatcher: Mapping[str, Any],
        agents: Mapping[str, Any],
        jobs: Mapping[str, Any],
        memory: Mapping[str, Any],
        services: Mapping[str, Any],
    ) -> RuntimeHealthSummary:
        warnings: list[str] = []
        errors: list[str] = []

        runtime_state = (
            "healthy"
            if runtime.get("started")
            else "stopped"
        )

        dispatcher_state = (
            "healthy"
            if dispatcher.get("status") is not None
            else "unknown"
        )

        failed_agents = self._count_agent_status(
            agents,
            {"failed"},
        )
        agents_state = "degraded" if failed_agents else "healthy"

        failed_jobs = self._count_job_status(
            jobs,
            {"failed", "error"},
        )
        jobs_state = "degraded" if failed_jobs else "healthy"

        memory_state = (
            "healthy"
            if isinstance(memory.get("status"), Mapping)
            else "unknown"
        )

        services_state = (
            "healthy"
            if services.get("sdk")
            else "unknown"
        )

        if not runtime.get("started"):
            warnings.append("Runtime is not currently started.")

        if failed_agents:
            errors.append(f"{failed_agents} agent task(s) failed.")

        if failed_jobs:
            errors.append(f"{failed_jobs} job(s) failed.")

        if services_state == "unknown":
            warnings.append("Service status is unavailable.")

        if memory_state == "unknown":
            warnings.append("Agent memory status is unavailable.")

        if errors:
            overall = "degraded"
        elif warnings:
            overall = "warning"
        else:
            overall = "healthy"

        return RuntimeHealthSummary(
            overall=overall,
            runtime=runtime_state,
            dispatcher=dispatcher_state,
            agents=agents_state,
            jobs=jobs_state,
            memory=memory_state,
            services=services_state,
            warnings=tuple(warnings),
            errors=tuple(errors),
        )

    @staticmethod
    def _build_summary(
        *,
        runtime: Mapping[str, Any],
        dispatcher: Mapping[str, Any],
        agents: Mapping[str, Any],
        jobs: Mapping[str, Any],
        events: Mapping[str, Any],
        health: RuntimeHealthSummary,
    ) -> dict[str, Any]:
        return {
            "runtime_status": runtime.get("status", "unknown"),
            "health": health.overall,
            "events": events.get("count", 0),
            "dispatcher_subscribers": dispatcher.get(
                "subscriber_count",
                0,
            ),
            "agents": agents.get("count", 0),
            "active_agents": agents.get("active_count", 0),
            "jobs": jobs.get("count", 0),
            "active_jobs": jobs.get("active_count", 0),
        }

    @staticmethod
    def _count_subscribers(status: Mapping[str, Any]) -> int:
        subscribers = status.get("subscribers", {})
        if not isinstance(subscribers, Mapping):
            return 0

        total = 0
        for value in subscribers.values():
            try:
                total += int(value)
            except (TypeError, ValueError):
                continue

        return total

    @staticmethod
    def _count_agent_status(
        agents: Mapping[str, Any],
        statuses: set[str],
    ) -> int:
        tracker = agents.get("tracker", {})
        if not isinstance(tracker, Mapping):
            return 0

        counts = tracker.get("status_counts", {})
        if not isinstance(counts, Mapping):
            return 0

        return sum(
            int(counts.get(status, 0) or 0)
            for status in statuses
        )

    @staticmethod
    def _count_job_status(
        jobs: Mapping[str, Any],
        statuses: set[str],
    ) -> int:
        counts = jobs.get("counts", {})
        if not isinstance(counts, Mapping):
            return 0

        return sum(
            int(counts.get(status, 0) or 0)
            for status in statuses
        )

    @staticmethod
    def _infer_count(value: Mapping[str, Any]) -> int:
        for key in (
            "count",
            "total",
            "service_count",
            "agent_count",
            "job_count",
        ):
            try:
                if key in value:
                    return int(value[key])
            except (TypeError, ValueError):
                pass

        for key in (
            "items",
            "services",
            "agents",
            "jobs",
            "registered",
        ):
            item = value.get(key)
            if isinstance(item, (list, tuple, set, dict)):
                return len(item)

        return 0

    @staticmethod
    def _merge_events(
        *event_groups: Any,
        limit: int,
    ) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()

        for group in event_groups:
            if not isinstance(group, list):
                continue

            for event in group:
                normalized = RuntimeSnapshot._as_dict(event)
                if not normalized:
                    continue

                event_id = str(
                    normalized.get("event_id")
                    or normalized.get("id")
                    or (
                        str(normalized.get("type", ""))
                        + str(normalized.get("created_at", ""))
                        + str(normalized.get("timestamp", ""))
                    )
                )

                if event_id in seen:
                    continue

                seen.add(event_id)
                merged.append(normalized)

        merged.sort(
            key=lambda item: str(
                item.get("timestamp")
                or item.get("created_at")
                or ""
            )
        )

        return merged[-max(0, limit):]

    @staticmethod
    def _safe_call(
        obj: Any,
        method_name: str,
        *args: Any,
        default: Any,
    ) -> Any:
        if obj is None:
            return default

        method = getattr(obj, method_name, None)
        if not callable(method):
            return default

        try:
            return method(*args)
        except Exception:
            return default

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)

        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            try:
                converted = to_dict()
                if isinstance(converted, Mapping):
                    return dict(converted)
            except Exception:
                return {}

        object_dict = getattr(value, "__dict__", None)
        if isinstance(object_dict, Mapping):
            return dict(object_dict)

        return {}

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
