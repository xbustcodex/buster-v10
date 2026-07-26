# tests/test_v32_planner.py
import pytest
from buster.capabilities import CapabilityRegistry
from buster.capabilities.filesystem_cap import FilesystemCapability
from buster.orchestration.planner import MissionPlanner


def test_mission_planner_construction(tmp_path):
    registry = CapabilityRegistry()
    registry.register(FilesystemCapability(registry))

    planner = MissionPlanner(registry)

    test_file = tmp_path / "plan_test.txt"
    task_defs = [
        {
            "task_id": "t1",
            "capability_id": "core.filesystem",
            "action": "filesystem.write_file",
            "arguments": {"file_path": str(test_file), "content": "Orchestration OK"},
        },
        {
            "task_id": "t2",
            "capability_id": "core.filesystem",
            "action": "filesystem.read_file",
            "arguments": {"file_path": str(test_file)},
            "dependencies": ["t1"],
        },
    ]

    plan = planner.plan_from_template(goal="Write and read file test", task_definitions=task_defs)
    assert plan.mission_id.startswith("mission_")
    assert len(plan.tasks) == 2
    assert plan.tasks[0].risk_level == "medium"
    assert plan.tasks[1].dependencies == ["t1"]