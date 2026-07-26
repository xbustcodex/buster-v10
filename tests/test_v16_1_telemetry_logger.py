"""
Test v16.1: Trace Context & Event Logger (Structured JSONL)
"""
import json
import pytest
from pathlib import Path
from buster.telemetry.trace_context import TraceContext
from buster.telemetry.event_logger import EventLogger


def test_trace_context_propagation():
    trace_id = TraceContext.start_trace(task_id="task_123", agent_id="worker_alpha")
    ctx = TraceContext.get_context()

    assert ctx["trace_id"] == trace_id
    assert ctx["task_id"] == "task_123"
    assert ctx["agent_id"] == "worker_alpha"
    assert ctx["parent_task_id"] is None


def test_event_logger_writes_jsonl(tmp_path: Path):
    logger = EventLogger(log_dir=str(tmp_path))

    TraceContext.start_trace(task_id="task_test_001")
    evt = logger.log_event(
        event_type="execution.started",
        component="retry_runner",
        status="running",
        attempt=1,
    )

    assert evt["component"] == "retry_runner"
    assert evt["event_type"] == "execution.started"

    # Verify JSONL content on disk
    events_file = tmp_path / "execution_events.jsonl"
    assert events_file.exists()

    lines = events_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1

    parsed = json.loads(lines[0])
    assert parsed["event_id"] == evt["event_id"]
    assert parsed["task_id"] == "task_test_001"


def test_failure_event_mirrored(tmp_path: Path):
    logger = EventLogger(log_dir=str(tmp_path))

    logger.log_event(
        event_type="execution.failed",
        component="step_runner",
        status="failed",
        failure_category="TRANSIENT",
        retryable=True,
    )

    failures_file = tmp_path / "failure_events.jsonl"
    assert failures_file.exists()

    lines = failures_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["failure_category"] == "TRANSIENT"