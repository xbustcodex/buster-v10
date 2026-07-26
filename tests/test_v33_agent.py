# tests/test_v33_agent.py
import pytest
from buster.capabilities import CapabilityRegistry
from buster.capabilities.filesystem_cap import FilesystemCapability
from buster.agent.core import BusterAgent


def test_buster_agent_execution(tmp_path):
    registry = CapabilityRegistry()
    registry.register(FilesystemCapability(registry))

    agent = BusterAgent(registry)

    test_file = tmp_path / "agent_test.txt"
    task_defs = [
        {
            "task_id": "step1",
            "capability_id": "core.filesystem",
            "action": "filesystem.write_file",
            "arguments": {"file_path": str(test_file), "content": "Agent Core Operational"},
        },
        {
            "task_id": "step2",
            "capability_id": "core.filesystem",
            "action": "filesystem.read_file",
            "arguments": {"file_path": str(test_file)},
            "dependencies": ["step1"],
        },
    ]

    ctx = agent.execute_plan_from_template(goal="Agent filesystem test", task_definitions=task_defs)
    assert ctx.outputs["step2"]["content"] == "Agent Core Operational"