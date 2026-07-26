# tests/test_v35_integration.py
import pytest
from buster.capabilities.registry import CapabilityRegistry
from buster.capabilities.filesystem_cap import FilesystemCapability
from buster.agent.core import BusterAgent
from buster.agent.llm_planner import LLMIntentPlanner
from buster.cli import main


def test_end_to_end_agent_ecosystem(tmp_path):
    # 1. Initialize Registry and Capabilities
    registry = CapabilityRegistry()
    registry.register(FilesystemCapability(registry))

    # 2. Instantiate Agent and Intent Planner
    agent = BusterAgent(registry, agent_id="integration-agent")
    planner = LLMIntentPlanner(agent)

    # 3. Execute natural language goal through planner & runner
    ctx = planner.run_natural_language_goal("Please write a log and then read it back")
    
    # 4. Verify outputs and state
    assert ctx.mission_id.startswith("mission_")
    assert "auto_write" in ctx.outputs
    assert "auto_read" in ctx.outputs
    assert ctx.outputs["auto_read"]["content"] == "Goal: Please write a log and then read it back"

    # 5. Verify CLI execution path
    exit_code = main(["Please write a log and then read it back"])
    assert exit_code == 0