from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("buster.kernel.circadian")


class HeartbeatDaemon:
    def __init__(self, runtime_core, idle_threshold_seconds: float = 300.0):
        self.core = runtime_core
        self.dispatcher = runtime_core.dispatcher
        self.state = "ACTIVE"  # ACTIVE | CURIOUS | REST
        
        self.idle_threshold = idle_threshold_seconds
        self.seconds_idle = 0.0
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._run_loop())
        except RuntimeError:
            pass  # Fallback if no event loop running at boot time
        logger.info("HeartbeatDaemon started.")

    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("HeartbeatDaemon stopped.")

    def notify_activity(self) -> None:
        """Reset idle timer back to ACTIVE state upon user or task execution."""
        self.seconds_idle = 0.0
        if self.state != "ACTIVE":
            self._transition_to("ACTIVE")

    def _transition_to(self, new_state: str) -> None:
        old_state = self.state
        self.state = new_state
        self.dispatcher.publish(
            "system.circadian.state_changed",
            {"from": old_state, "to": new_state},
            source="heartbeat_daemon",
        )

    def _evaluate_state_transition(self, elapsed: float) -> None:
        self.seconds_idle += elapsed

        if self.seconds_idle < 60.0:
            target_state = "ACTIVE"
        elif 60.0 <= self.seconds_idle < self.idle_threshold:
            target_state = "CURIOUS"
        else:
            target_state = "REST"

        if target_state != self.state:
            self._transition_to(target_state)

    def _get_tick_interval(self) -> float:
        if self.state == "ACTIVE":
            return 1.0
        elif self.state == "CURIOUS":
            return 5.0
        else:  # REST
            return 15.0

    async def _run_loop(self) -> None:
        while self._running:
            try:
                interval = self._get_tick_interval()
                await asyncio.sleep(interval)

                self._evaluate_state_transition(interval)

                tick_payload = {
                    "state": self.state,
                    "idle_seconds": self.seconds_idle,
                    "interval": interval,
                }

                self.dispatcher.publish(
                    "system.tick",
                    tick_payload,
                    source="heartbeat_daemon",
                )

                if self.state == "CURIOUS":
                    self._on_curious_tick()
                elif self.state == "REST":
                    self._on_rest_tick()

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in HeartbeatDaemon loop: {exc}")

    def _on_curious_tick(self) -> None:
        curiosity = getattr(self.core, "curiosity_engine", None)
        if curiosity:
            idea = curiosity.pop_next_downtime_idea()
            if idea:
                self.dispatcher.publish(
                    "curiosity.explore_idea",
                    idea,
                    source="heartbeat_daemon",
                )

    def _on_rest_tick(self) -> None:
        self.dispatcher.publish(
            "system.maintenance.prune",
            {"target": "event_logs"},
            source="heartbeat_daemon",
        )

    def status(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "seconds_idle": round(self.seconds_idle, 1),
            "running": self._running,
        }