"""
Test v17.3: Delegation Planner, Parent/Child Lineage & Dead-Letter Queue
"""
import json
import pytest
from pathlib import Path
from buster.telemetry.telemetry_service import TelemetryService
from buster.autonomy.delegation.worker_pool import WorkerPoolManager
from buster.autonomy.delegation.delegation_planner import DelegationPlanner


def test_subtask_creation_and_lineage(tmp_path: Path):
    telemetry = TelemetryService(log_dir=str(tmp_path))
    pool = WorkerPoolManager()
    planner = DelegationPlanner(worker_pool=pool, telemetry=telemetry, dlq_path=str(tmp_path / "dlq.jsonl"))

    parent_id = "parent_task_001"
    subtask = planner.create_subtask(
        parent_task_id=parent_id,
        title="Run unit tests",
        required_capabilities=["unit_testing", "test_execution"],
    )

    assert subtask["parent_task_id"] == parent_id
    assert subtask["role"] == "TESTER"
    assert planner.children[parent_id] == [subtask["task_id"]]


def test_cancellation_propagation(tmp_path: Path):
    telemetry = TelemetryService(log_dir=str(tmp_path))
    pool = WorkerPoolManager()
    planner = DelegationPlanner(worker_pool=pool, telemetry=telemetry, dlq_path=str(tmp_path / "dlq.jsonl"))

    parent_id = "root_task"
    sub1 = planner.create_subtask(parent_id, "Sub 1", ["code_generation"])
    sub2 = planner.create_subtask(sub1["task_id"], "Sub 1.1", ["unit_testing"])

    cancelled = planner.cancel_task_tree(parent_id)

    assert sub1["task_id"] in cancelled
    assert sub2["task_id"] in cancelled
    assert planner.tasks[sub1["task_id"]]["status"] == "cancelled"
    assert planner.tasks[sub2["task_id"]]["status"] == "cancelled"


def test_dead_letter_queue_parking(tmp_path: Path):
    dlq_file = tmp_path / "dead_letter_queue.jsonl"
    telemetry = TelemetryService(log_dir=str(tmp_path))
    pool = WorkerPoolManager()
    planner = DelegationPlanner(worker_pool=pool, telemetry=telemetry, dlq_path=str(dlq_file))

    sub = planner.create_subtask("parent_01", "Failing task", ["bug_fixing"])
    planner.send_to_dlq(sub["task_id"], error_reason="Max retries exceeded")

    assert dlq_file.exists()
    lines = dlq_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1

    dlq_data = json.loads(lines[0])
    assert dlq_data["task_id"] == sub["task_id"]
    assert dlq_data["error_reason"] == "Max retries exceeded"