from __future__ import annotations

import json
from typing import Any, Mapping, Optional

from PySide6.QtCore import QObject, Signal, Slot

from buster.runtime.repair_event_stream import RepairEventStream


class MissionControlRepairBinding(QObject):
    """
    Event-driven repair projection for Mission Control.

    This binding intentionally owns no timer. It updates Mission Control only
    when the runtime dispatcher publishes repair.* events.
    """

    repair_state_changed = Signal(object)
    repair_event_received = Signal(object)

    def __init__(
        self,
        runtime_core: Any,
        mission_control: Any,
        *,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self.runtime_core = runtime_core
        self.mission_control = mission_control

        self.stream = RepairEventStream(
            runtime_core=runtime_core,
            parent=self,
        )
        self.stream.state_changed.connect(
            self._on_state_changed
        )
        self.stream.repair_event.connect(
            self._on_event_received
        )

        self._render_initial_runtime_state()

    @Slot(object)
    def _on_state_changed(
        self,
        state: Any,
    ) -> None:
        data = (
            dict(state)
            if isinstance(state, Mapping)
            else {}
        )

        self._render_state(data)
        self.repair_state_changed.emit(data)

    @Slot(object)
    def _on_event_received(
        self,
        event: Any,
    ) -> None:
        data = (
            dict(event)
            if isinstance(event, Mapping)
            else {}
        )

        self._append_event(data)
        self.repair_event_received.emit(data)

    def _render_initial_runtime_state(self) -> None:
        status_method = getattr(
            self.runtime_core,
            "repair_workflow_status",
            None,
        )

        if callable(status_method):
            try:
                status = status_method()
            except Exception:
                status = {}
        else:
            status = {}

        latest = (
            status.get("latest_session")
            if isinstance(status, Mapping)
            else None
        )

        if not isinstance(latest, Mapping):
            self._render_state(
                {
                    "state": "idle",
                    "title": "No active repair",
                    "message": "Repair workflow is idle.",
                    "progress_percent": 0,
                    "active_repairs": int(
                        status.get("active_sessions", 0)
                        if isinstance(status, Mapping)
                        else 0
                    ),
                    "completed_repairs": 0,
                    "failed_repairs": 0,
                }
            )
            return

        self._render_state(
            {
                "active_session_id": latest.get(
                    "session_id",
                    "",
                ),
                "state": latest.get(
                    "status",
                    "idle",
                ),
                "title": str(
                    latest.get("status", "idle")
                ).replace("_", " ").title(),
                "message": latest.get("error") or "",
                "progress_percent": latest.get(
                    "progress_percent",
                    0,
                ),
                "active_repairs": int(
                    status.get("active_sessions", 0)
                ),
                "completed_repairs": 0,
                "failed_repairs": 0,
            }
        )

    def _render_state(
        self,
        state: Mapping[str, Any],
    ) -> None:
        dashboard = self.mission_control

        self._set_metric(
            dashboard,
            (
                "repair_status_card",
                "repair_card",
            ),
            state.get("state", "idle"),
        )
        self._set_metric(
            dashboard,
            (
                "repair_progress_card",
                "repair_progress",
            ),
            f"{int(state.get('progress_percent', 0) or 0)}%",
        )
        self._set_metric(
            dashboard,
            (
                "active_repairs_card",
                "repairs_card",
            ),
            state.get("active_repairs", 0),
        )

        status_label = self._first_attribute(
            dashboard,
            (
                "repair_status_label",
                "repair_label",
            ),
        )

        if status_label is not None:
            setter = getattr(status_label, "setText", None)

            if callable(setter):
                title = str(
                    state.get("title")
                    or state.get("state")
                    or "Repair"
                )
                message = str(
                    state.get("message") or ""
                )
                setter(
                    title
                    if not message
                    else f"{title}: {message}"
                )

        progress_bar = self._first_attribute(
            dashboard,
            (
                "repair_progress_bar",
                "repair_progress_widget",
            ),
        )

        if progress_bar is not None:
            setter = getattr(
                progress_bar,
                "setValue",
                None,
            )

            if callable(setter):
                setter(
                    int(
                        state.get(
                            "progress_percent",
                            0,
                        )
                        or 0
                    )
                )

        callback = getattr(
            dashboard,
            "update_repair_state",
            None,
        )

        if callable(callback):
            callback(dict(state))

    def _append_event(
        self,
        event: Mapping[str, Any],
    ) -> None:
        dashboard = self.mission_control

        callback = getattr(
            dashboard,
            "add_repair_event",
            None,
        )

        if callable(callback):
            callback(dict(event))
            return

        box = self._first_attribute(
            dashboard,
            (
                "repair_events_box",
                "events_box",
            ),
        )

        if box is None:
            return

        title = str(
            event.get("title")
            or event.get("type")
            or "Repair Event"
        )
        message = str(
            event.get("message") or ""
        )
        created_at = str(
            event.get("created_at") or ""
        )

        line = " · ".join(
            part
            for part in (
                created_at,
                title,
                message,
            )
            if part
        )

        append = getattr(box, "append", None)

        if callable(append):
            append(line)
            return

        append_plain = getattr(
            box,
            "appendPlainText",
            None,
        )

        if callable(append_plain):
            append_plain(line)
            return

        set_plain = getattr(
            box,
            "setPlainText",
            None,
        )
        to_plain = getattr(
            box,
            "toPlainText",
            None,
        )

        if callable(set_plain):
            existing = (
                to_plain()
                if callable(to_plain)
                else ""
            )
            set_plain(
                "\n".join(
                    item
                    for item in (
                        existing,
                        line,
                    )
                    if item
                )
            )

    @staticmethod
    def _set_metric(
        dashboard: Any,
        names: tuple[str, ...],
        value: Any,
    ) -> None:
        card = MissionControlRepairBinding._first_attribute(
            dashboard,
            names,
        )

        if card is None:
            return

        setter = getattr(card, "set_value", None)

        if callable(setter):
            setter(value)
            return

        setter = getattr(card, "setText", None)

        if callable(setter):
            setter(str(value))

    @staticmethod
    def _first_attribute(
        target: Any,
        names: tuple[str, ...],
    ) -> Any:
        for name in names:
            value = getattr(target, name, None)

            if value is not None:
                return value

        return None

    def snapshot(self) -> dict[str, Any]:
        return self.stream.snapshot()

    def close(self) -> None:
        self.stream.close()
        self.deleteLater()


def attach_mission_control_repair_stream(
    mission_control: Any,
    runtime_core: Any,
) -> MissionControlRepairBinding:
    """
    Attach once and return the binding.

    Call after Mission Control has built its widgets.
    """
    existing = getattr(
        mission_control,
        "_repair_binding",
        None,
    )

    if isinstance(
        existing,
        MissionControlRepairBinding,
    ):
        return existing

    binding = MissionControlRepairBinding(
        runtime_core=runtime_core,
        mission_control=mission_control,
        parent=mission_control,
    )
    mission_control._repair_binding = binding
    return binding


def detach_mission_control_repair_stream(
    mission_control: Any,
) -> None:
    binding = getattr(
        mission_control,
        "_repair_binding",
        None,
    )

    if isinstance(
        binding,
        MissionControlRepairBinding,
    ):
        binding.close()

    mission_control._repair_binding = None


__all__ = [
    "MissionControlRepairBinding",
    "attach_mission_control_repair_stream",
    "detach_mission_control_repair_stream",
]
