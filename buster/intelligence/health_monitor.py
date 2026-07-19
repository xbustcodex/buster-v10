"""Runtime health evaluation for Buster Desktop AI OS.

Consumes either a RuntimeSnapshot dictionary or a live BusterRuntimeCore and
produces a normalized health report for Mission Control. This module is
independent of Qt and does not modify runtime state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


HEALTHY_STATES = {"healthy", "ok", "ready", "running", "connected", "available"}
WARNING_STATES = {"warning", "degraded", "idle", "partial", "unknown", "stopped"}
ERROR_STATES = {"error", "failed", "critical", "offline", "unavailable", "disconnected"}


@dataclass(frozen=True, slots=True)
class HealthCheck:
    name: str
    status: str
    score: int
    message: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class HealthReport:
    overall: str
    score: int
    checked_at: str
    checks: tuple[HealthCheck, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "score": self.score,
            "checked_at": self.checked_at,
            "checks": [check.to_dict() for check in self.checks],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


class HealthMonitor:
    """Evaluate runtime, dispatcher, agent, job, memory and service health."""

    def __init__(
        self,
        runtime_core: Any | None = None,
        *,
        warning_threshold: int = 75,
        critical_threshold: int = 50,
    ) -> None:
        self.runtime_core = runtime_core
        self.warning_threshold = max(0, min(100, int(warning_threshold)))
        self.critical_threshold = max(0, min(100, int(critical_threshold)))
        self._last_report: HealthReport | None = None

    def evaluate(self, snapshot: Mapping[str, Any] | None = None) -> dict[str, Any]:
        source = self._resolve_snapshot(snapshot)

        checks = (
            self._check_runtime(source),
            self._check_dispatcher(source),
            self._check_agents(source),
            self._check_jobs(source),
            self._check_memory(source),
            self._check_services(source),
            self._check_registry(source),
            self._check_events(source),
            self._check_plugins(source),
            self._check_ai_provider(source),
            self._check_git(source),
        )

        applicable = [check for check in checks if check.status != "not_available"]
        score = (
            round(sum(check.score for check in applicable) / len(applicable))
            if applicable
            else 0
        )

        warnings = tuple(
            check.message for check in applicable if check.status == "warning"
        )
        errors = tuple(
            check.message
            for check in applicable
            if check.status in {"error", "critical"}
        )

        if errors or score < self.critical_threshold:
            overall = "critical"
        elif warnings or score < self.warning_threshold:
            overall = "warning"
        else:
            overall = "healthy"

        report = HealthReport(
            overall=overall,
            score=score,
            checked_at=self._utc_now(),
            checks=checks,
            warnings=warnings,
            errors=errors,
        )
        self._last_report = report
        return report.to_dict()

    def compact(self, snapshot: Mapping[str, Any] | None = None) -> dict[str, Any]:
        report = self.evaluate(snapshot)
        return {
            "overall": report["overall"],
            "score": report["score"],
            "checked_at": report["checked_at"],
            "warning_count": len(report["warnings"]),
            "error_count": len(report["errors"]),
            "checks": {
                check["name"]: check["status"]
                for check in report["checks"]
                if check["status"] != "not_available"
            },
        }

    def last_report(self) -> dict[str, Any] | None:
        return self._last_report.to_dict() if self._last_report else None

    def _resolve_snapshot(
        self,
        snapshot: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        if isinstance(snapshot, Mapping):
            return dict(snapshot)

        if self.runtime_core is None:
            return {}

        runtime_snapshot = getattr(self.runtime_core, "runtime_snapshot", None)
        capture = getattr(runtime_snapshot, "capture", None)
        if callable(capture):
            try:
                result = capture(event_limit=50, activity_limit=50)
                if isinstance(result, Mapping):
                    return dict(result)
            except Exception:
                pass

        status = getattr(self.runtime_core, "status", None)
        if callable(status):
            try:
                result = status()
                if isinstance(result, Mapping):
                    return dict(result)
            except Exception:
                pass

        return {}

    def _check_runtime(self, source: Mapping[str, Any]) -> HealthCheck:
        runtime = self._mapping(source.get("runtime"))
        started = bool(source.get("started", runtime.get("started", False)))
        status = self._normalise_status(runtime.get("status"))

        if started or status in HEALTHY_STATES:
            return self._check("runtime", "healthy", 100, "Runtime is running.", runtime)
        if status in ERROR_STATES:
            return self._check(
                "runtime", "critical", 0, f"Runtime state is {status}.", runtime
            )
        return self._check(
            "runtime", "warning", 60, "Runtime is not started.", runtime
        )

    def _check_dispatcher(self, source: Mapping[str, Any]) -> HealthCheck:
        dispatcher = self._mapping(source.get("dispatcher"))
        status = self._mapping(dispatcher.get("status"))
        subscribers = dispatcher.get("subscriber_count")
        if subscribers is None:
            subscribers = self._subscriber_count(
                status.get("subscribers", dispatcher.get("subscribers", {}))
            )
        subscribers = self._to_int(subscribers)

        if not dispatcher:
            return self._check(
                "dispatcher",
                "not_available",
                0,
                "Dispatcher health is unavailable.",
                {},
            )
        if subscribers <= 0:
            return self._check(
                "dispatcher",
                "warning",
                70,
                "Dispatcher is active but has no subscribers.",
                {"subscribers": subscribers, **dispatcher},
            )
        return self._check(
            "dispatcher",
            "healthy",
            100,
            f"Dispatcher is healthy with {subscribers} subscriber(s).",
            {"subscribers": subscribers, **dispatcher},
        )

    def _check_agents(self, source: Mapping[str, Any]) -> HealthCheck:
        agents = self._mapping(source.get("agents"))
        tracker = self._mapping(agents.get("tracker"))
        counts = self._mapping(tracker.get("status_counts"))
        failed = self._sum_keys(counts, {"failed", "error", "critical"})
        active = self._to_int(agents.get("active_count", tracker.get("active_agents", 0)))
        total = self._to_int(agents.get("count", tracker.get("total_agents", 0)))

        if failed:
            return self._check(
                "agents",
                "error",
                max(0, 100 - failed * 20),
                f"{failed} agent task(s) failed.",
                {"total": total, "active": active, "failed": failed},
            )
        if total == 0:
            return self._check(
                "agents",
                "warning",
                70,
                "No agents are registered in the tracker.",
                {"total": total, "active": active},
            )
        return self._check(
            "agents",
            "healthy",
            100,
            f"{total} agent(s) registered; {active} active.",
            {"total": total, "active": active},
        )

    def _check_jobs(self, source: Mapping[str, Any]) -> HealthCheck:
        jobs = self._mapping(source.get("jobs"))
        counts = self._mapping(jobs.get("counts"))
        failed = self._sum_keys(counts, {"failed", "error"})
        running = self._to_int(counts.get("running", jobs.get("active_count", 0)))
        total = self._to_int(jobs.get("count", 0))

        if failed:
            return self._check(
                "jobs",
                "error",
                max(0, 100 - failed * 20),
                f"{failed} job(s) failed.",
                {"total": total, "running": running, "failed": failed},
            )
        return self._check(
            "jobs",
            "healthy",
            100,
            f"{total} job(s) known; {running} running.",
            {"total": total, "running": running, "failed": failed},
        )

    def _check_memory(self, source: Mapping[str, Any]) -> HealthCheck:
        memory = self._mapping(source.get("memory"))
        status = self._mapping(memory.get("status", memory))
        event_count = self._to_int(memory.get("event_count", 0))

        if not status:
            return self._check(
                "memory",
                "not_available",
                0,
                "Agent memory health is unavailable.",
                {},
            )
        return self._check(
            "memory",
            "healthy",
            100,
            f"Agent memory is available with {event_count} event(s).",
            {"event_count": event_count},
        )

    def _check_services(self, source: Mapping[str, Any]) -> HealthCheck:
        services = self._mapping(source.get("services"))
        count = self._to_int(services.get("count", 0))
        sdk = self._mapping(services.get("sdk", services))

        if not services:
            return self._check(
                "services", "not_available", 0, "Service status is unavailable.", {}
            )
        if count <= 0 and not sdk:
            return self._check(
                "services", "warning", 65, "No runtime services were detected.", services
            )
        return self._check(
            "services",
            "healthy",
            100,
            f"{count} runtime service(s) available.",
            {"count": count},
        )

    def _check_registry(self, source: Mapping[str, Any]) -> HealthCheck:
        registry = self._mapping(source.get("registry"))
        count = self._to_int(registry.get("count", 0))
        if not registry:
            return self._check(
                "registry", "not_available", 0, "Registry health is unavailable.", {}
            )
        return self._check(
            "registry",
            "healthy",
            100,
            f"Registry is available with {count} item(s).",
            {"count": count},
        )

    def _check_events(self, source: Mapping[str, Any]) -> HealthCheck:
        events = self._mapping(source.get("events"))
        count = self._to_int(events.get("count", 0))
        monitor = self._mapping(events.get("monitor"))
        error_count = self._to_int(
            monitor.get("error_count", monitor.get("errors", 0))
        )

        if error_count:
            return self._check(
                "events",
                "warning",
                max(40, 100 - error_count * 10),
                f"Runtime event stream contains {error_count} error event(s).",
                {"count": count, "errors": error_count},
            )
        return self._check(
            "events",
            "healthy",
            100,
            f"Runtime event stream contains {count} event(s).",
            {"count": count, "errors": error_count},
        )

    def _check_plugins(self, source: Mapping[str, Any]) -> HealthCheck:
        plugins = self._find_section(source, "plugins")
        if not plugins:
            return self._check(
                "plugins", "not_available", 0, "Plugin health is unavailable.", {}
            )
        failed = self._count_statuses(plugins, ERROR_STATES)
        if failed:
            return self._check(
                "plugins",
                "error",
                max(0, 100 - failed * 20),
                f"{failed} plugin(s) are unhealthy.",
                {"failed": failed},
            )
        return self._check(
            "plugins", "healthy", 100, "Plugin system is healthy.", plugins
        )

    def _check_ai_provider(self, source: Mapping[str, Any]) -> HealthCheck:
        provider = (
            self._find_section(source, "ai_provider")
            or self._find_section(source, "ai")
            or self._find_section(source, "llm")
        )
        if not provider:
            return self._check(
                "ai_provider",
                "not_available",
                0,
                "AI provider health is unavailable.",
                {},
            )
        status = self._normalise_status(provider.get("status", provider.get("state")))
        if status in ERROR_STATES:
            return self._check(
                "ai_provider", "error", 20, f"AI provider state is {status}.", provider
            )
        if status in WARNING_STATES:
            return self._check(
                "ai_provider", "warning", 70, f"AI provider state is {status}.", provider
            )
        return self._check(
            "ai_provider", "healthy", 100, "AI provider is available.", provider
        )

    def _check_git(self, source: Mapping[str, Any]) -> HealthCheck:
        git = self._find_section(source, "git")
        if not git:
            return self._check(
                "git", "not_available", 0, "Git health is unavailable.", {}
            )
        status = self._normalise_status(git.get("status", git.get("state")))
        if status in ERROR_STATES:
            return self._check(
                "git", "warning", 60, f"Git state is {status}.", git
            )
        return self._check(
            "git", "healthy", 100, "Git repository information is available.", git
        )

    @staticmethod
    def _check(
        name: str,
        status: str,
        score: int,
        message: str,
        details: Mapping[str, Any],
    ) -> HealthCheck:
        return HealthCheck(
            name=name,
            status=status,
            score=max(0, min(100, int(score))),
            message=message,
            details=dict(details),
        )

    @staticmethod
    def _find_section(source: Mapping[str, Any], name: str) -> dict[str, Any]:
        direct = source.get(name)
        if isinstance(direct, Mapping):
            return dict(direct)

        state = source.get("state")
        if isinstance(state, Mapping):
            nested = state.get(name)
            if isinstance(nested, Mapping):
                return dict(nested)

        runtime = source.get("runtime")
        if isinstance(runtime, Mapping):
            details = runtime.get("details")
            if isinstance(details, Mapping):
                nested = details.get(name)
                if isinstance(nested, Mapping):
                    return dict(nested)

        return {}

    @staticmethod
    def _mapping(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, Mapping) else {}

    @staticmethod
    def _normalise_status(value: Any) -> str:
        return str(value or "unknown").strip().lower()

    @staticmethod
    def _to_int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _subscriber_count(value: Any) -> int:
        if not isinstance(value, Mapping):
            return 0
        total = 0
        for count in value.values():
            try:
                total += int(count)
            except (TypeError, ValueError):
                continue
        return total

    @staticmethod
    def _sum_keys(mapping: Mapping[str, Any], keys: set[str]) -> int:
        total = 0
        for key in keys:
            try:
                total += int(mapping.get(key, 0) or 0)
            except (TypeError, ValueError):
                continue
        return total

    @staticmethod
    def _count_statuses(value: Any, statuses: set[str]) -> int:
        count = 0
        if isinstance(value, Mapping):
            current = str(value.get("status", value.get("state", ""))).lower()
            if current in statuses:
                count += 1
            for child in value.values():
                count += HealthMonitor._count_statuses(child, statuses)
        elif isinstance(value, (list, tuple, set)):
            for child in value:
                count += HealthMonitor._count_statuses(child, statuses)
        return count

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
