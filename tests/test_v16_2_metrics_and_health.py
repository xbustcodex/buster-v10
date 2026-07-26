"""
Test v16.2: Metrics Registry & Health Snapshots
"""
import json
import pytest
from pathlib import Path
from buster.telemetry.metrics_registry import MetricsRegistry
from buster.telemetry.health_snapshot import HealthSnapshot


def test_metrics_registry_and_persistence(tmp_path: Path):
    metrics_file = tmp_path / "runtime_metrics.json"
    metrics = MetricsRegistry(metrics_file=str(metrics_file))

    metrics.increment("execution.started", 5)
    metrics.increment("execution.failed", 1)
    metrics.observe_duration("step_runner", 120.5)

    snap = metrics.snapshot()
    assert snap["counters"]["execution.started"] == 5
    assert snap["counters"]["execution.failed"] == 1
    assert snap["cumulative_durations_ms"]["step_runner"] == 120.5

    metrics.save()
    assert metrics_file.exists()

    data = json.loads(metrics_file.read_text(encoding="utf-8"))
    assert data["counters"]["execution.started"] == 5


def test_health_snapshot_status_evaluation():
    metrics = MetricsRegistry()

    # Initial state -> HEALTHY
    health = HealthSnapshot.generate(metrics)
    assert health["status"] == "HEALTHY"
    assert health["failure_rate"] == 0.0

    # Simulate failures
    metrics.increment("execution.started", 10)
    metrics.increment("execution.failed", 6)

    health_degraded = HealthSnapshot.generate(metrics)
    assert health_degraded["status"] == "DEGRADED"
    assert health_degraded["failure_rate"] == 0.6