"""
Phase 18 — Mission Control Snapshot & Presenter Verification Tests
"""
import pytest
from datetime import datetime, timezone
from buster.mission_control.snapshot import (
    MissionControlSnapshot,
    WorkerLeaseSnapshot,
    CircuitSnapshot,
)
from buster.mission_control.health_aggregator import HealthAggregator
from buster.mission_control.presenter import MissionControlPresenter
from buster.ui.dashboard_visualizer import DashboardVisualizer


class MockTelemetry:
    def get_health(self):
        return {"total_executions": 10, "total_failures": 1, "failure_rate": 0.1, "circuit_breaker_trips": 0}


class MockWorkerPool:
    def __init__(self):
        self.active_leases = {
            "lease_01": type("Lease", (), {
                "agent_id": "builder_alpha",
                "role": "Builder",
                "task_id": "task_101",
                "acquired_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc),
                "time_remaining": lambda: 45.0,
            })
        }


class MockCircuitRegistry:
    def __init__(self):
        self.circuits = {
            "playwright": type("CB", (), {"state": "CLOSED", "failure_count": 0, "is_critical": True, "retry_after_seconds": None}),
            "filesystem": type("CB", (), {"state": "OPEN", "failure_count": 3, "is_critical": False, "retry_after_seconds": 12.0}),
        }


def test_health_aggregator_determines_degraded_and_critical():
    agg = HealthAggregator()
    
    # Healthy case
    assert agg.calculate(
        open_critical_circuits=0,
        open_noncritical_circuits=0,
        dlq_count=0,
        telemetry_stale=False,
        worker_pool_available=True,
    ) == "HEALTHY"

    # Degraded due to non-critical open circuit
    assert agg.calculate(
        open_critical_circuits=0,
        open_noncritical_circuits=1,
        dlq_count=0,
        telemetry_stale=False,
        worker_pool_available=True,
    ) == "DEGRADED"

    # Critical due to critical circuit open
    assert agg.calculate(
        open_critical_circuits=1,
        open_noncritical_circuits=0,
        dlq_count=0,
        telemetry_stale=False,
        worker_pool_available=True,
    ) == "CRITICAL"


def test_presenter_creates_valid_snapshot():
    presenter = MissionControlPresenter(
        telemetry=MockTelemetry(),
        worker_pool=MockWorkerPool(),
        circuit_registry=MockCircuitRegistry(),
    )

    snapshot = presenter.create_snapshot()

    assert isinstance(snapshot, MissionControlSnapshot)
    assert snapshot.health == "DEGRADED"  # Due to filesystem open circuit
    assert len(snapshot.active_leases) == 1
    assert snapshot.active_leases[0].worker_id == "builder_alpha"
    assert len(snapshot.circuits) == 2


def test_visualizer_ansi_and_html_outputs():
    presenter = MissionControlPresenter(
        telemetry=MockTelemetry(),
        worker_pool=MockWorkerPool(),
        circuit_registry=MockCircuitRegistry(),
    )
    snapshot = presenter.create_snapshot()
    visualizer = DashboardVisualizer()

    ansi_out = visualizer.render_ansi(snapshot)
    assert "MISSION CONTROL PANEL" in ansi_out
    assert "builder_alpha" in ansi_out

    html_out = visualizer.render_html(snapshot)
    assert "<h1>🚀 Mission Control & System Health</h1>" in html_out
    assert "builder_alpha" in html_out