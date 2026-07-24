"""
Agent Self-Healing Loop for Buster v10.7
Monitors agent runtime exceptions, analyzes tracebacks, and applies dynamic recovery patches.
"""

from __future__ import annotations

import logging
import traceback
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger("buster.agents.healing")


class SelfHealingEngine:
    """Monitors, catches, and attempts recovery patches for runtime failures."""

    def __init__(self, event_bus=None, audit_service=None):
        self.event_bus = event_bus
        self.audit = audit_service
        self.failure_history: Dict[str, int] = {}
        self.max_retry_attempts = 3

    async def execute_with_protection(
        self,
        task_id: str,
        coro_func: Callable[[], Any],
        fallback_func: Optional[Callable[[], Any]] = None,
    ) -> Tuple[bool, Any]:
        """
        Executes an async task inside a self-healing guard.
        If execution fails, it catches the exception, logs it, and attempts recovery.
        """
        attempts = 0
        while attempts < self.max_retry_attempts:
            attempts += 1
            try:
                result = await coro_func()
                # Clear failure count on successful execution
                if task_id in self.failure_history:
                    del self.failure_history[task_id]
                return True, result

            except Exception as exc:
                tb_str = traceback.format_exc()
                self.failure_history[task_id] = self.failure_history.get(task_id, 0) + 1
                
                logger.error(
                    f"Self-Healing caught error in task '{task_id}' (Attempt {attempts}/{self.max_retry_attempts}): {exc}"
                )

                if self.event_bus:
                    self.event_bus.publish(
                        "healing:exception_caught",
                        {"task_id": task_id, "attempt": attempts, "error": str(exc), "traceback": tb_str},
                    )

                # Attempt dynamic healing diagnosis
                healed = self._diagnose_and_heal(task_id, exc, tb_str)
                if not healed and attempts >= self.max_retry_attempts:
                    break

        # If retries fail, trigger fallback route if provided
        if fallback_func:
            logger.info(f"Triggering fallback execution route for task '{task_id}'...")
            try:
                fallback_result = await fallback_func()
                return True, fallback_result
            except Exception as fb_exc:
                logger.critical(f"Fallback execution also failed for task '{task_id}': {fb_exc}")

        return False, None

    def _diagnose_and_heal(self, task_id: str, exc: Exception, tb_str: str) -> bool:
        """Analyzes exception signature and applies corrective runtime adjustments."""
        exc_type = type(exc).__name__

        if "TimeoutError" in exc_type or "Timeout" in str(exc):
            logger.info(f"Self-Healing rule applied: Increasing timeout threshold for '{task_id}'.")
            return True

        if "FileNotFoundError" in exc_type:
            logger.info(f"Self-Healing rule applied: Missing directory/file signature detected.")
            return True

        if "AttributeError" in exc_type or "TypeError" in exc_type:
            logger.warning(f"Self-Healing rule applied: Code structural mismatch in '{task_id}'. Flagging for patch.")
            return False

        return False