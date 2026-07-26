# tests/test_v33_llm_planner.py
import pytest
from buster.capabilities import CapabilityRegistry
from buster.capabilities.filesystem_cap import FilesystemCapability
from buster.agent.core import BusterAgent
from buster.agent.llm_planner import LLMIntentPlanner


def test_llm_intent_planner_execution():
    registry = CapabilityRegistry()
    registry.register(FilesystemCapability(registry))

    agent = BusterAgent(registry)
    planner = LLMIntentPlanner(agent)

    ctx = planner.run_natural_language_goal("Please write a log and then read it back")
    
    assert ctx.outputs["auto_write"]["bytes_written"] > 0
    assert "Goal: Please write a log and then read it back" in ctx.outputs["auto_read"]["content"]