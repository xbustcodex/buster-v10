# tests/test_v32_runner.py
import pytest
from buster.capabilities import CapabilityRegistry
from buster.capabilities.filesystem_cap import FilesystemCapability
from buster.orchestration.planner import MissionPlanner
from buster.orchestration.runner import MissionRunner


def test_mission_runner_execution(tmp_path):
    registry = CapabilityRegistry()
    registry.register(FilesystemCapability(registry))

    planner = MissionPlanner(registry)
    runner = MissionRunner(registry)

    test_file = tmp_path / "run_test.txt"
    task_defs = [
        {
            "task_id": "write_step",
            "capability_id": "core.filesystem",
            "action": "filesystem.write_file",
            "arguments": {"file_path": str(test_file), "content": "Full Autonomous Mission OK"},
        },
        {
            "task_id": "read_step",
            "capability_id": "core.filesystem",
            "action": "filesystem.read_file",
            "arguments": {"file_path": str(test_file)},
            "dependencies": ["write_step"],
        },
    ]

    plan = planner.plan_from_template(goal="End-to-end filesystem mission", task_definitions=task_defs)
    ctx = runner.run_mission(plan)

    assert ctx.outputs["write_step"]["bytes_written"] > 0
    assert ctx.outputs["read_step"]["content"] == "Full Autonomous Mission OK"