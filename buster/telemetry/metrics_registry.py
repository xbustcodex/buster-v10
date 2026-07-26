from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict


class MetricsRegistry:
    """Thread-safe collector for runtime counters, latency timers, and status gauges."""

    def __init__(self, metrics_file: str = "data/runtime_metrics.json"):
        self._lock = threading.RLock()
        self.metrics_path = Path(metrics_file)
        self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
        self._counters: Dict[str, int] = {}
        self._timers: Dict[str, float] = {}

    def increment(self, metric: str, value: int = 1) -> None:
        """Increments a counter metric thread-safely."""
        with self._lock:
            self._counters[metric] = self._counters.get(metric, 0) + value

    def observe_duration(self, metric: str, duration_ms: float) -> None:
        """Updates cumulative duration for a timer metric."""
        with self._lock:
            self._timers[metric] = self._timers.get(metric, 0.0) + duration_ms

    def snapshot(self) -> Dict[str, Any]:
        """Returns a copy of all active metrics."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "cumulative_durations_ms": dict(self._timers),
            }

    def save(self) -> None:
        """Persists current snapshot to disk."""
        with self._lock:
            data = self.snapshot()
            with open(self.metrics_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)