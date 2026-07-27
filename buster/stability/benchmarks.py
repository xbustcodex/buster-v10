# buster/stability/benchmarks.py
from __future__ import annotations

import time
import psutil
import os
from typing import Dict, Any


class PerformanceBenchmark:
    """Measures and records Buster v11.0 runtime performance metrics."""

    def __init__(self) -> None:
        self.process = psutil.Process(os.getpid())

    def measure_startup(self, init_callable) -> float:
        """Measures system startup or component load time."""
        start = time.perf_counter()
        init_callable()
        duration = time.perf_counter() - start
        return duration

    def measure_context_retrieval(self, retrieval_callable) -> float:
        """Measures context retrieval latency."""
        start = time.perf_counter()
        retrieval_callable()
        duration = time.perf_counter() - start
        return duration

    def get_resource_usage(self) -> Dict[str, float]:
        """Captures current memory and CPU utilization."""
        memory_info = self.process.memory_info()
        return {
            "memory_mb": memory_info.rss / (1024 * 1024),
            "cpu_percent": self.process.cpu_percent(interval=0.1),
        }

    def run_suite(self, init_callable, retrieval_callable) -> Dict[str, Any]:
        """Executes a full benchmark pass and returns diagnostic metrics."""
        startup_time = self.measure_startup(init_callable)
        retrieval_latency = self.measure_context_retrieval(retrieval_callable)
        resources = self.get_resource_usage()

        return {
            "startup_time_sec": round(startup_time, 4),
            "context_retrieval_latency_sec": round(retrieval_latency, 4),
            **resources,
        }