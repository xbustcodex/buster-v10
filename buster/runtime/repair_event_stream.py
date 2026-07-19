from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Mapping, Optional

from PySide6.QtCore import QObject, Signal, Slot


REPAIR_EVENT_PREFIX = "repair."

REPAIR_EVENT_TITLES = {
    "repair.service.registered": "Repair Service Online",
    "repair.service.stopped": "Repair Service Stopped",
    "repair.started": "Repair Started",
    "repair.review.started": "Review Started",
    "repair.review.completed": "Review Complete",
    "repair.plan.started": "Repair Planning Started",
    "repair.plan.completed": "Repair Plan Generated",
    "repair.preview.started": "Preview Generation Started",
    "repair.preview.ready": "Preview Ready",
    "repair.preview.approved": "Repair Approved",
    "repair.preview.rejected": "Repair Rejected",
    "repair.apply.started": "Applying Changes",
    "repair.apply.completed": "Changes Applied",
    "repair.verification.started": "Verification Started",
    "repair.verification.passed": "Verification Passed",
    "repair.verification.failed": "Verification Failed",
    "repair.rollback.started": "Rollback Started",
    "repair.rollback.completed": "Rollback Complete",
    "repair.session.completed": "Repair Complete",
    "repair.finished": "Repair Complete",
    "repair.session.failed": "Repair Failed",
    "repair.failed": "Repair Failed",
    "repair.session.cancelled": "Repair Cancelled",
    "repair.recovery.action_required": "Repair Recovery Required",
}

REPAIR_EVENT_STATES = {
    "repair.service.registered": "ready",
    "repair.service.stopped": "offline",
    "repair.started": "created",
    "repair.review.started": "reviewing",
    "repair.review.completed": "reviewed",
    "repair.plan.started": "planning",
    "repair.plan.completed": "planned",
    "repair.preview.started": "previewing",
    "repair.preview.ready": "preview_ready",
    "repair.preview.approved": "approved",
    "repair.preview.rejected": "rejected",
    "repair.apply.started": "applying",
    "repair.apply.completed": "applied",
    "repair.verification.started": "verifying",
    "repair.verification.passed": "verified",
    "repair.verification.failed": "verification_failed",
    "repair.rollback.started": "rolling_back",
    "repair.rollback.completed": "rolled_back",
    "repair.session.completed": "completed",
    "repair.finished": "completed",
    "repair.session.failed": "failed",
    "repair.failed": "failed",
    "repair.session.cancelled": "cancelled",
    "repair.recovery.action_required": "recovery_required",
}

TERMINAL_STATES = {
    "completed",
    "failed",
    "cancelled",
    "rejected",
    "rolled_back",
}


@dataclass(slots=True)
class RepairEvent:
    event_type: str
    session_id: str = ""
    state: str = ""
    title: str = ""
    message: str = ""
    source: str = "self_improvement"
    created_at: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    @property
    def failed(self) -> bool:
        return self.state in {
            "failed",
            "verification_failed",
            "recovery_required",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.event_type,
            "event_type": self.event_type,
            "session_id": self.session_id,
            "state": self.state,
            "status": self.state,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "created_at": self.created_at,
            "payload": dict(self.payload),
            "category": "repair",
            "icon": "🛠",
        }


@dataclass(slots=True)
class RepairMissionState:
    active_session_id: str = ""
    state: str = "idle"
    title: str = "No active repair"
    message: str = "Repair workflow is idle."
    progress_percent: int = 0
    active_repairs: int = 0
    completed_repairs: int = 0
    failed_repairs: int = 0
    last_updated: str = ""
    latest_event: Optional[RepairEvent] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_session_id": self.active_session_id,
            "state": self.state,
            "title": self.title,
            "message": self.message,
            "progress_percent": self.progress_percent,
            "active_repairs": self.active_repairs,
            "completed_repairs": self.completed_repairs,
            "failed_repairs": self.failed_repairs,
            "last_updated": self.last_updated,
            "latest_event": (
                self.latest_event.to_dict()
                if self.latest_event is not None
                else None
            ),
        }


class RepairEventProjector:
    """Convert dispatcher events into timeline and Mission Control state."""

    PROGRESS_BY_STATE = {
        "idle": 0,
        "ready": 0,
        "created": 5,
        "reviewing": 15,
        "reviewed": 30,
        "planning": 40,
        "planned": 55,
        "previewing": 65,
        "preview_ready": 75,
        "approved": 80,
        "applying": 88,
        "applied": 92,
        "verifying": 96,
        "verified": 100,
        "completed": 100,
        "failed": 100,
        "verification_failed": 100,
        "cancelled": 100,
        "rejected": 100,
        "rolling_back": 95,
        "rolled_back": 100,
        "recovery_required": 0,
        "offline": 0,
    }

    def __init__(self) -> None:
        self.state = RepairMissionState()
        self._session_states: dict[str, str] = {}

    @staticmethod
    def is_repair_event(event: Any) -> bool:
        event_type = RepairEventProjector._event_type(event)
        return event_type.startswith(REPAIR_EVENT_PREFIX)

    def project(self, event: Any) -> Optional[RepairEvent]:
        if not self.is_repair_event(event):
            return None

        event_type = self._event_type(event)
        envelope = self._as_mapping(event)
        payload = self._payload(envelope)

        session_id = str(
            payload.get("session_id")
            or envelope.get("session_id")
            or ""
        )
        state = str(
            payload.get("state")
            or payload.get("status")
            or REPAIR_EVENT_STATES.get(event_type, "")
        )
        title = str(
            payload.get("title")
            or REPAIR_EVENT_TITLES.get(
                event_type,
                event_type.replace(".", " ").title(),
            )
        )
        message = self._message(
            event_type,
            payload,
            title,
        )
        created_at = str(
            envelope.get("created_at")
            or payload.get("created_at")
            or datetime.now(timezone.utc).isoformat()
        )
        source = str(
            envelope.get("source")
            or payload.get("source")
            or "self_improvement"
        )

        repair_event = RepairEvent(
            event_type=event_type,
            session_id=session_id,
            state=state,
            title=title,
            message=message,
            source=source,
            created_at=created_at,
            payload=dict(payload),
        )

        self._update_state(repair_event)
        return repair_event

    def _update_state(self, event: RepairEvent) -> None:
        previous = (
            self._session_states.get(event.session_id)
            if event.session_id
            else None
        )

        if event.session_id:
            self._session_states[event.session_id] = event.state

        active_states = {
            "created",
            "reviewing",
            "reviewed",
            "planning",
            "planned",
            "previewing",
            "preview_ready",
            "approved",
            "applying",
            "applied",
            "verifying",
            "rolling_back",
            "recovery_required",
        }

        self.state.active_repairs = sum(
            1
            for state in self._session_states.values()
            if state in active_states
        )

        if event.state == "completed" and previous != "completed":
            self.state.completed_repairs += 1

        if (
            event.state in {"failed", "verification_failed"}
            and previous not in {"failed", "verification_failed"}
        ):
            self.state.failed_repairs += 1

        self.state.active_session_id = event.session_id
        self.state.state = event.state or self.state.state
        self.state.title = event.title
        self.state.message = event.message
        self.state.progress_percent = self.PROGRESS_BY_STATE.get(
            event.state,
            self.state.progress_percent,
        )
        self.state.last_updated = event.created_at
        self.state.latest_event = event

    @staticmethod
    def _event_type(event: Any) -> str:
        if isinstance(event, Mapping):
            return str(
                event.get("type")
                or event.get("event_type")
                or ""
            )

        return str(
            getattr(event, "type", "")
            or getattr(event, "event_type", "")
        )

    @staticmethod
    def _as_mapping(event: Any) -> dict[str, Any]:
        if isinstance(event, Mapping):
            return dict(event)

        method = getattr(event, "to_dict", None)

        if callable(method):
            try:
                value = method()
                if isinstance(value, Mapping):
                    return dict(value)
            except Exception:
                pass

        values = getattr(event, "__dict__", None)
        return dict(values) if isinstance(values, Mapping) else {}

    @staticmethod
    def _payload(envelope: Mapping[str, Any]) -> dict[str, Any]:
        value = envelope.get("payload", {})

        if isinstance(value, Mapping):
            return dict(value)

        return {"value": value}

    @staticmethod
    def _message(
        event_type: str,
        payload: Mapping[str, Any],
        title: str,
    ) -> str:
        explicit = (
            payload.get("message")
            or payload.get("summary")
            or payload.get("error")
        )

        if explicit:
            return str(explicit)

        finding = payload.get("finding")

        if isinstance(finding, Mapping):
            finding_title = (
                finding.get("title")
                or finding.get("category")
                or finding.get("file")
            )
            if finding_title:
                return f"{title}: {finding_title}"

        session_id = str(payload.get("session_id") or "")

        if session_id:
            return f"{title} · Session {session_id[:8]}"

        return title


class RepairEventStream(QObject):
    """
    One dispatcher subscription shared by a Qt consumer.

    Dispatcher callbacks may run on worker threads. The signal safely queues
    delivery onto the Qt object's thread.
    """

    repair_event = Signal(object)
    state_changed = Signal(object)

    def __init__(
        self,
        runtime_core: Any = None,
        *,
        history_limit: int = 100,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self.runtime_core = runtime_core
        self.projector = RepairEventProjector()
        self.history: Deque[RepairEvent] = deque(
            maxlen=max(1, int(history_limit))
        )
        self._connected = False

        self._dispatcher_event.connect(
            self._process_dispatcher_event
        )

        self.connect_runtime()

    _dispatcher_event = Signal(object)

    def connect_runtime(self) -> None:
        if self._connected or self.runtime_core is None:
            return

        dispatcher = getattr(
            self.runtime_core,
            "dispatcher",
            None,
        )
        subscribe = getattr(dispatcher, "subscribe", None)

        if not callable(subscribe):
            return

        subscribe(
            "repair.*",
            self._receive_dispatcher_event,
        )
        self._connected = True

    def disconnect_runtime(self) -> None:
        if not self._connected or self.runtime_core is None:
            return

        dispatcher = getattr(
            self.runtime_core,
            "dispatcher",
            None,
        )
        unsubscribe = getattr(
            dispatcher,
            "unsubscribe",
            None,
        )

        if callable(unsubscribe):
            try:
                unsubscribe(
                    "repair.*",
                    self._receive_dispatcher_event,
                )
            except Exception:
                pass

        self._connected = False

    def set_runtime_core(
        self,
        runtime_core: Any,
    ) -> None:
        self.disconnect_runtime()
        self.runtime_core = runtime_core
        self.projector = RepairEventProjector()
        self.history.clear()
        self.connect_runtime()

    def snapshot(self) -> dict[str, Any]:
        return {
            "repair": self.projector.state.to_dict(),
            "events": [
                item.to_dict()
                for item in self.history
            ],
        }

    def _receive_dispatcher_event(
        self,
        event: Any,
    ) -> None:
        self._dispatcher_event.emit(event)

    @Slot(object)
    def _process_dispatcher_event(
        self,
        event: Any,
    ) -> None:
        repair_event = self.projector.project(event)

        if repair_event is None:
            return

        self.history.appendleft(repair_event)
        self.repair_event.emit(
            repair_event.to_dict()
        )
        self.state_changed.emit(
            self.projector.state.to_dict()
        )

    def close(self) -> None:
        self.disconnect_runtime()
        self.deleteLater()


def timeline_event_from_repair(
    event: Any,
) -> Optional[dict[str, Any]]:
    """
    Convert one repair event into RuntimeTimelinePanel's existing event shape.

    RuntimeTimelinePanel already subscribes to "*" and normally needs no
    separate subscription. Use this helper in event_model/event_card to ensure
    repair events receive a dedicated category, title and icon.
    """
    projector = RepairEventProjector()
    projected = projector.project(event)
    return projected.to_dict() if projected is not None else None


__all__ = [
    "REPAIR_EVENT_PREFIX",
    "REPAIR_EVENT_STATES",
    "REPAIR_EVENT_TITLES",
    "RepairEvent",
    "RepairEventProjector",
    "RepairEventStream",
    "RepairMissionState",
    "timeline_event_from_repair",
]
