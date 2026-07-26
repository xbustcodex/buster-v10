from __future__ import annotations
from typing import Any, Callable
from buster.mission_control.presenter import MissionControlPresenter
from buster.mission_control.snapshot import MissionControlSnapshot


class MissionControlEventListener:
    """Subscribes to runtime events and pushes freshly generated snapshots to the UI."""

    def __init__(
        self,
        presenter: MissionControlPresenter,
        event_bus: Any,
        on_snapshot_updated: Callable[[MissionControlSnapshot], None],
    ):
        self.presenter = presenter
        self.event_bus = event_bus
        self.on_snapshot_updated = on_snapshot_updated
        self._subscribe_to_events()

    def _subscribe_to_events(self) -> None:
        monitored_events = [
            "mission_control.snapshot_updated",
            "runtime.health_changed",
            "worker.lease_acquired",
            "worker.lease_released",
            "worker.lease_expired",
            "circuit.opened",
            "circuit.half_opened",
            "circuit.closed",
            "task.delegated",
            "task.dead_lettered",
            "telemetry.metrics_updated",
        ]

        if hasattr(self.event_bus, "subscribe"):
            for event_name in monitored_events:
                self.event_bus.subscribe(event_name, self._handle_event)

    def _handle_event(self, event_data: Any = None) -> None:
        snapshot = self.presenter.create_snapshot()
        self.on_snapshot_updated(snapshot)