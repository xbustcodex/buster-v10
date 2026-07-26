from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from buster.rhythm.rhythm import BusterRhythm, LifeState


class RhythmService:
    """Service that polls or triggers rhythm ticks and broadcasts state changes."""

    def __init__(
        self,
        rhythm: BusterRhythm,
        blackboard: Any,
        event_bus: Any,
        poll_interval_seconds: int = 10,
    ) -> None:
        self.rhythm = rhythm
        self.blackboard = blackboard
        self.event_bus = event_bus
        self.poll_interval = poll_interval_seconds
        self._current_state: Optional[LifeState] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def tick_sync(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Synchronous tick helper for direct core runtime invocations."""
        now = now or datetime.now()
        status = self.rhythm.get_blackboard_status(now)
        new_state = LifeState(status["life_state"])

        if hasattr(self.blackboard, "set"):
            self.blackboard.set("rhythm", status)
        elif hasattr(self.blackboard, "update"):
            self.blackboard.update("rhythm", status)

        if self._current_state != new_state:
            self._current_state = new_state
            if hasattr(self.event_bus, "publish"):
                # Handle both async and sync event bus implementations
                res = self.event_bus.publish(
                    "rhythm.state_changed",
                    {"new_state": new_state.value, "status": status},
                    source="rhythm_service",
                )
                if asyncio.iscoroutine(res):
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(res)
                    except RuntimeError:
                        pass
        return status

    async def tick(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Evaluates state, updates blackboard, and fires transition events if changed."""
        now = now or datetime.now()
        status = self.rhythm.get_blackboard_status(now)
        new_state = LifeState(status["life_state"])

        # Write to blackboard
        if hasattr(self.blackboard, "update"):
            self.blackboard.update("rhythm", status)
        elif hasattr(self.blackboard, "set"):
            self.blackboard.set("rhythm", status)

        # Check for state transitions
        if self._current_state != new_state:
            old_state = self._current_state
            self._current_state = new_state

            # Publish generic state change
            await self.event_bus.publish(
                "rhythm.state_changed",
                {
                    "previous_state": old_state.value if old_state else None,
                    "new_state": new_state.value,
                    "status": status,
                },
            )

            # Publish specific state events
            event_topic = f"rhythm.{new_state.value.lower()}_started"
            await self.event_bus.publish(event_topic, status)

            # Specific feature triggers
            await self.event_bus.publish(
                "rhythm.goal_inhibitor_changed",
                {"active": status["goal_inhibitor_active"]},
            )
            await self.event_bus.publish(
                "rhythm.dream_sandbox_changed",
                {"active": status["dream_sandbox_active"]},
            )

            if status["dream_sandbox_active"]:
                await self.event_bus.publish("dream_cycle.requested", status)

        return status

    async def start(self) -> None:
        """Starts the background polling loop."""
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def _loop(self) -> None:
        while self._running:
            await self.tick()
            await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()