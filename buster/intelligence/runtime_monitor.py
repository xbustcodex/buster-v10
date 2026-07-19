"""Runtime event monitoring for Buster Desktop AI OS.

This module records runtime events, maintains lightweight statistics, and
provides immutable snapshots for Mission Control and other UI consumers.

It deliberately does not depend on Qt or on a specific dispatcher
implementation. The runtime can forward events to ``RuntimeMonitor.record()``
or ``RuntimeMonitor.handle_event()``.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import RLock
from time import monotonic
from typing import Any, Callable, Deque, Mapping
from uuid import uuid4


EventListener = Callable[["RuntimeEventRecord"], None]


@dataclass(frozen=True, slots=True)
class RuntimeEventRecord:
    """Normalized runtime event stored by :class:`RuntimeMonitor`."""

    event_id: str
    event_type: str
    timestamp: str
    source: str
    severity: str
    message: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation of the event."""

        return asdict(self)


class RuntimeMonitor:
    """Thread-safe runtime event monitor."""

    VALID_SEVERITIES = {"debug", "info", "success", "warning", "error", "critical"}

    def __init__(self, max_events: int = 1_000) -> None:
        if max_events < 1:
            raise ValueError("max_events must be greater than zero")

        self._max_events = max_events
        self._events: Deque[RuntimeEventRecord] = deque(maxlen=max_events)
        self._event_counts: Counter[str] = Counter()
        self._severity_counts: Counter[str] = Counter()
        self._listeners: list[EventListener] = []
        self._lock = RLock()

        self._started_at_monotonic: float | None = None
        self._started_at_utc: str | None = None
        self._stopped_at_utc: str | None = None
        self._running = False
        self._total_recorded = 0
        self._last_error: RuntimeEventRecord | None = None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def max_events(self) -> int:
        return self._max_events

    def start(self) -> None:
        """Mark monitoring as active."""

        with self._lock:
            if self._running:
                return

            self._running = True
            self._started_at_monotonic = monotonic()
            self._started_at_utc = self._utc_now()
            self._stopped_at_utc = None

    def stop(self) -> None:
        """Mark monitoring as inactive."""

        with self._lock:
            if not self._running:
                return

            self._running = False
            self._stopped_at_utc = self._utc_now()

    def record(
        self,
        event_type: str,
        *,
        source: str = "runtime",
        severity: str = "info",
        message: str = "",
        payload: Mapping[str, Any] | None = None,
        timestamp: str | datetime | None = None,
        event_id: str | None = None,
    ) -> RuntimeEventRecord:
        """Normalize and store one runtime event."""

        normalized_type = str(event_type or "runtime.unknown").strip()
        normalized_source = str(source or "runtime").strip()
        normalized_severity = str(severity or "info").strip().lower()

        if normalized_severity not in self.VALID_SEVERITIES:
            normalized_severity = "info"

        record = RuntimeEventRecord(
            event_id=event_id or uuid4().hex,
            event_type=normalized_type,
            timestamp=self._normalize_timestamp(timestamp),
            source=normalized_source,
            severity=normalized_severity,
            message=str(message or "").strip(),
            payload=dict(payload or {}),
        )

        with self._lock:
            self._events.append(record)
            self._event_counts[record.event_type] += 1
            self._severity_counts[record.severity] += 1
            self._total_recorded += 1

            if record.severity in {"error", "critical"}:
                self._last_error = record

            listeners = tuple(self._listeners)

        for listener in listeners:
            try:
                listener(record)
            except Exception:
                continue

        return record

    def handle_event(self, event: Any) -> RuntimeEventRecord:
        """Record a dispatcher event represented by a mapping or object."""

        event_type = self._read_field(event, "event_type", "type", "name")
        source = self._read_field(event, "source", "service", "producer")
        severity = self._read_field(event, "severity", "level", "status")
        message = self._read_field(event, "message", "description", "summary")
        payload = self._read_field(event, "payload", "data", "details")
        timestamp = self._read_field(event, "timestamp", "created_at", "time")
        event_id = self._read_field(event, "event_id", "id")

        if not isinstance(payload, Mapping):
            payload = {"value": payload} if payload is not None else {}

        return self.record(
            str(event_type or "runtime.unknown"),
            source=str(source or "runtime"),
            severity=str(severity or "info"),
            message=str(message or ""),
            payload=payload,
            timestamp=timestamp,
            event_id=str(event_id) if event_id else None,
        )

    def subscribe(self, listener: EventListener) -> None:
        """Register a callback for newly recorded events."""

        if not callable(listener):
            raise TypeError("listener must be callable")

        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def unsubscribe(self, listener: EventListener) -> None:
        """Remove a previously registered callback."""

        with self._lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass

    def recent(
        self,
        limit: int = 100,
        *,
        event_type: str | None = None,
        severity: str | None = None,
        source: str | None = None,
    ) -> list[RuntimeEventRecord]:
        """Return newest events first, optionally filtered."""

        if limit < 1:
            return []

        severity_filter = severity.lower() if severity else None

        with self._lock:
            events = tuple(self._events)

        selected: list[RuntimeEventRecord] = []
        for record in reversed(events):
            if event_type and record.event_type != event_type:
                continue
            if severity_filter and record.severity != severity_filter:
                continue
            if source and record.source != source:
                continue

            selected.append(record)
            if len(selected) >= limit:
                break

        return selected

    def latest(self) -> RuntimeEventRecord | None:
        """Return the most recently recorded event."""

        with self._lock:
            return self._events[-1] if self._events else None

    def clear(self, *, reset_totals: bool = False) -> None:
        """Clear retained event history and counters."""

        with self._lock:
            self._events.clear()
            self._event_counts.clear()
            self._severity_counts.clear()
            self._last_error = None

            if reset_totals:
                self._total_recorded = 0

    def snapshot(self, event_limit: int = 50) -> dict[str, Any]:
        """Return a serializable runtime monitoring snapshot."""

        with self._lock:
            retained_events = list(self._events)
            uptime_seconds = self._calculate_uptime_locked()

            return {
                "running": self._running,
                "started_at": self._started_at_utc,
                "stopped_at": self._stopped_at_utc,
                "uptime_seconds": round(uptime_seconds, 3),
                "total_recorded": self._total_recorded,
                "retained_events": len(retained_events),
                "max_events": self._max_events,
                "event_counts": dict(self._event_counts),
                "severity_counts": dict(self._severity_counts),
                "last_error": (
                    self._last_error.to_dict() if self._last_error else None
                ),
                "events": [
                    item.to_dict()
                    for item in retained_events[-max(0, event_limit):]
                ],
            }

    def _calculate_uptime_locked(self) -> float:
        if self._started_at_monotonic is None:
            return 0.0

        if self._running:
            return max(0.0, monotonic() - self._started_at_monotonic)

        return 0.0

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

    @classmethod
    def _normalize_timestamp(cls, value: str | datetime | None) -> str:
        if value is None:
            return cls._utc_now()

        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).isoformat()

        text = str(value).strip()
        return text or cls._utc_now()
