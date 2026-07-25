from __future__ import annotations

import time
from typing import Dict, Any


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted on an open circuit breaker."""
    pass


class CircuitBreaker:
    """Monitors failures for a target resource and trips to block execution when failure thresholds are exceeded."""

    def __init__(self, max_failures: int = 3, reset_timeout: float = 60.0):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failure_counts: Dict[str, int] = {}
        self.last_failure_times: Dict[str, float] = {}
        self.states: Dict[str, str] = {}  # "CLOSED", "OPEN", "HALF_OPEN"

    def get_state(self, target_id: str) -> str:
        """Returns the current state for a target resource."""
        state = self.states.get(target_id, "CLOSED")
        if state == "OPEN":
            last_fail = self.last_failure_times.get(target_id, 0.0)
            if time.time() - last_fail >= self.reset_timeout:
                self.states[target_id] = "HALF_OPEN"
                return "HALF_OPEN"
        return state

    def check_allow_execution(self, target_id: str) -> bool:
        """Checks if execution should be permitted for target_id."""
        state = self.get_state(target_id)
        if state == "OPEN":
            raise CircuitBreakerOpenException(
                f"Circuit breaker is OPEN for target '{target_id}'. Execution blocked."
            )
        return True

    def record_success(self, target_id: str) -> None:
        """Resets failure history on successful execution."""
        self.failure_counts[target_id] = 0
        self.states[target_id] = "CLOSED"

    def record_failure(self, target_id: str) -> None:
        """Increments failure count and trips circuit breaker if threshold is met."""
        self.failure_counts[target_id] = self.failure_counts.get(target_id, 0) + 1
        self.last_failure_times[target_id] = time.time()

        if self.failure_counts[target_id] >= self.max_failures:
            self.states[target_id] = "OPEN"