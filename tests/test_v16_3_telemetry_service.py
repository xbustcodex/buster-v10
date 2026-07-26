"""
Test v16.3: Execution Tracker & Telemetry Service Integration
"""
import pytest
from pathlib import Path
from buster.telemetry.telemetry_service import TelemetryService


def test_telemetry_service_execution_tracker_success(tmp_path: Path):
    service = TelemetryService(log_dir=str(tmp_path))

    with service.track_execution(component="git_step_runner") as tracker:
        # Simulate work
        pass

    health = service.get_health()
    assert health["total_executions"] == 1
    assert health["total_failures"] == 0
    assert health["status"] == "HEALTHY"


def test_telemetry_service_execution_tracker_failure(tmp_path: Path):
    service = TelemetryService(log_dir=str(tmp_path))

    with pytest.raises(FileNotFoundError):
        with service.track_execution(component="file_cleanup"):
            raise FileNotFoundError("Target workspace directory not found")

    health = service.get_health()
    assert health["total_executions"] == 1
    assert health["total_failures"] == 1


def test_telemetry_circuit_and_retry_recording(tmp_path: Path):
    service = TelemetryService(log_dir=str(tmp_path))

    service.record_retry(
        component="rest_client",
        attempt=2,
        failure_category="TRANSIENT",
    )
    service.record_circuit_event("circuit.opened", target_id="/api/v1/deploy")

    service.flush()

    health = service.get_health()
    assert health["circuit_breaker_trips"] == 1
    assert health["status"] == "DEGRADED"